#!/usr/bin/env python3

"""Descargador unificado basado en yt-dlp.

Uso generico:   -u <url> [-m|-p] [-r 480|720|1080|best] [-s] [-o DIR]
Facebook:       -u <url> --facebook [mismas opciones]  (facebook.com / fb.watch)
Donghua:        -u <url> --donghua [--source CLAVE] [--dry-run]

El modo --donghua extrae el enlace real de video desde las paginas:
  * seriesdonghua.com  -> API interna /api/player/get-server (requiere
                          session cookie + token CSRF)
  * donghualife.com    -> tokens cifrados embedidos en la pagina, se resuelven
                          vía /api/player/source
  * mundodonghua.com   -> scripts ofuscados (JavaScript Packer): m3u8 directo
                          (asura), Dailymotion (tamamo) e iframes de terceros
"""

import argparse
import http.cookiejar
import json
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOWNLOAD_DIR = Path.home() / "Downloads"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"

# Orden preferente de fuentes por sitio (las que yt-dlp resuelve primero).
_SOURCE_PREFERENCE = {
    "series": ["dailymotion", "okru", "rumble", "voe"],
    "donghualife": ["directo", "dailymotion", "rumble"],
    "mundo": ["asura", "tamamo", "fmoon", "amagi", "vhide", "swish"],
}


class DownloadError(Exception):
    pass


# ---------------------------------------------------------------------------
# Decodificadores legacy (pagina antigua de seriesdonghua: VIDEO_MAP).
# Se conservan identicos al decodificador original del usuario.
# ---------------------------------------------------------------------------

def decode_base(d, e, f):
    h = _CHARS[:e]
    i = _CHARS[:f]
    total = 0
    for pos, ch in enumerate(reversed(d)):
        if ch in h:
            total += h.index(ch) * (e ** pos)
    if total == 0:
        return "0"
    k = ""
    while total > 0:
        k = i[total % f] + k
        total //= f
    return k


def decode_script(encoded, n_chars, t, e):
    result = []
    sep = n_chars[e]
    pos = 0
    while pos < len(encoded):
        s = ""
        while pos < len(encoded) and encoded[pos] != sep:
            s += encoded[pos]
            pos += 1
        pos += 1
        for j, ch in enumerate(n_chars):
            s = s.replace(ch, str(j))
        decoded_num = decode_base(s, e, 10)
        result.append(chr(int(decoded_num) - t))
    combined = "".join(result)
    return urllib.parse.unquote(combined)


def js_unescape(s):
    result = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == '"':
                result.append('"')
                i += 2
            elif n == "\\":
                result.append("\\")
                i += 2
            elif n == "/":
                result.append("/")
                i += 2
            elif n == "n":
                result.append("\n")
                i += 2
            elif n == "t":
                result.append("\t")
                i += 2
            else:
                result.append(s[i])
                i += 1
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Helpers HTTP
# ---------------------------------------------------------------------------

def _make_opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return opener


def _http_get(url, opener=None, referer=None):
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    op = opener or _make_opener()
    try:
        with op.open(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise DownloadError(f"HTTP {e.code} en {url}")
    except urllib.error.URLError as e:
        raise DownloadError(f"No se pudo obtener {url}: {e.reason}")


def _http_post_json(opener, url, payload, referer, extra_headers=None):
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": referer,
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST", headers=headers
    )
    try:
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code == 419:
            raise DownloadError("CSRF expirado; vuelve a ejecutar el comando")
        raise DownloadError(f"HTTP {e.code} en {url}")
    except ValueError:
        raise DownloadError(f"Respuesta inesperada de {url}")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "download"


def get_page_title(html, url):
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if title:
            return sanitize_filename(title)
    slug = urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]
    return sanitize_filename(slug)


def detect_site(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if "seriesdonghua.com" in host:
        return "series"
    if "donghualife.com" in host:
        return "donghualife"
    if "mundodonghua.com" in host:
        return "mundo"
    return None


_FACEBOOK_HOSTS = ("facebook.com", "fb.watch", "fb.com", "fb.me")


def is_facebook_url(url):
    """True si la URL pertenece a Facebook (incluye subdominios de locale)."""
    host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    return any(host == d or host.endswith("." + d) for d in _FACEBOOK_HOSTS)


def label_for_embed(url):
    """Devuelve (label, key) a partir del host del embed."""
    if url.rstrip("/").split("?")[0].endswith(".m3u8"):
        return "Directo (m3u8)", "directo"
    host = urllib.parse.urlparse(url).netloc.lower()
    table = [
        ("dailymotion", "Dailymotion", "dailymotion"),
        ("ok.ru", "OK.ru", "okru"),
        ("rumble", "Rumble", "rumble"),
        ("voe.sx", "Voe.sx", "voe"),
        ("vidhidepro", "VidHidePro", "vidhidepro"),
        ("callistanise", "VidHidePro", "vidhidepro"),
        ("bysekoze", "Bysekoze", "bysekoze"),
        ("embedwish", "EmbedWish", "embedwish"),
        ("donghualife", "Directo (m3u8)", "directo"),
        ("mdnemonicplayer", "MDPlayer", "mdplayer"),
    ]
    for needle, label, key in table:
        if needle in host:
            return label, key
    return host.replace(".", "_"), host.replace(".", "_")


def order_sources(sources, preference):
    pref = {key: i for i, key in enumerate(preference)}
    return sorted(
        sources,
        key=lambda s: pref.get(s["key"], len(pref)),
    )


def dedupe_sources(sources):
    seen = set()
    out = []
    used_keys = set()
    for s in sources:
        if s["url"] in seen:
            continue
        seen.add(s["url"])
        key = s["key"]
        if key in used_keys:
            n = 2
            while f"{key}-{n}" in used_keys:
                n += 1
            key = f"{key}-{n}"
        used_keys.add(key)
        out.append({**s, "key": key})
    return out


# ---------------------------------------------------------------------------
# seriesdonghua.com
# ---------------------------------------------------------------------------

def extract_seriesdonghua_sources(url):
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    opener = _make_opener()
    html = _http_get(url, opener=opener)

    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    if not csrf_match:
        raise DownloadError("No se encontro el token CSRF (la pagina cambio?)")
    csrf = csrf_match.group(1)

    video_ids = sorted(set(re.findall(r'data-video-id="(\d+)"', html)))
    server_indices = sorted(set(int(x) for x in re.findall(r'data-server-index="(\d+)"', html)))
    if not video_ids or not server_indices:
        raise DownloadError(
            "No se encontraron servidores de video en la pagina (la pagina cambio?)"
        )
    video_id = video_ids[0]

    sources = []
    for idx in server_indices:
        data = _http_post_json(
            opener,
            f"{base}/api/player/get-server",
            {"video_id": int(video_id), "server_index": idx},
            referer=url,
            extra_headers={
                "X-CSRF-TOKEN": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        embed = data.get("embed_url")
        if embed:
            label, key = label_for_embed(embed)
            sources.append({"key": key, "label": label, "url": embed})

    return get_page_title(html, url), dedupe_sources(order_sources(sources, _SOURCE_PREFERENCE["series"]))


# ---------------------------------------------------------------------------
# donghualife.com
# ---------------------------------------------------------------------------

def _donghualife_resolve(token, referer):
    parsed = urllib.parse.urlparse(referer)
    base = f"{parsed.scheme}://{parsed.netloc}"
    data = _http_post_json(
        _make_opener(), f"{base}/api/player/source", {"token": token}, referer=referer
    )
    return data.get("url")


def extract_donghualife_sources(url):
    html = _http_get(url)

    tokens = re.findall(r'\\"token\\":\\"([A-Za-z0-9=]+)\\"', html)
    if not tokens:
        tokens = re.findall(r'"token":"([A-Za-z0-9=]+)"', html)
    if not tokens:
        raise DownloadError(
            "No se encontraron tokens de fuente en la pagina (la pagina cambio?)"
        )

    # Resolver todos los tokens y etiquetar por la URL resultante. El emparejamiento
    # token<->nombre por indice no es fiable (varia segun episodio/temporada).
    sources = []
    seen_tokens = set()
    for token in tokens:
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        try:
            resolved = _donghualife_resolve(token, url)
        except DownloadError:
            continue
        if not resolved:
            continue
        label, key = label_for_embed(resolved)
        sources.append({"key": key, "label": label, "url": resolved})

    return get_page_title(html, url), dedupe_sources(order_sources(sources, _SOURCE_PREFERENCE["donghualife"]))


# ---------------------------------------------------------------------------
# mundodonghua.com
# ---------------------------------------------------------------------------

_PACKER_RE = re.compile(
    r"\}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\\?\|'\),0,\{\}\)\)",
    re.DOTALL,
)


def packer_decode(p, a, k):
    """Decodifica un script ofuscado con el JavaScript Packer (Dean Edwards)."""
    k = k.split("|")
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"

    def _e(code):
        if code == 0:
            return "0"
        out = ""
        while code:
            rem = code % a
            out = (digits[rem] if rem < 36 else chr(rem + 29)) + out
            code //= a
        return out

    d = {}
    for i in range(len(k)):
        d[_e(i)] = k[i] if k[i] else _e(i)

    for code in sorted(d, key=len, reverse=True):
        p = re.sub(r"\b" + re.escape(code) + r"\b", lambda mo, cc=code: d[cc], p)
    return p


def _mundo_tamamo_key(slug, base, referer):
    """api_donghua.php -> JSON -> clave para dmplayer.php"""
    data = json.loads(
        _http_get(
            f"{base}/api_donghua.php?slug={urllib.parse.quote(slug)}", referer=referer
        )
    )
    if isinstance(data, list) and data:
        return data[0].get("url")
    if isinstance(data, dict):
        return data.get("url") or data.get("key")
    return None


def _mundo_dmplayer_video(key, referer):
    """dmplayer.php -> video id de Dailymotion"""
    html = _http_get(
        "https://www.mdnemonicplayer.xyz/nemonicplayer/dmplayer.php?key="
        + urllib.parse.quote(key),
        referer=referer,
    )
    match = re.search(r'video:\s*"([A-Za-z0-9_-]+)"', html)
    return match.group(1) if match else None


def extract_mundo_sources(url):
    html = _http_get(url)
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    decoded = []
    for m in _PACKER_RE.finditer(html):
        p, a, k = m.group(1), int(m.group(2)), m.group(4)
        decoded.append(packer_decode(p, a, k))
    full = "\n".join(decoded)

    sources = []

    # Servidor "asura": m3u8 directo via redirector.php
    m = re.search(r"redirector\.php\?slug=([A-Za-z0-9+/=]+)", full)
    if m:
        sources.append(
            {
                "key": "asura",
                "label": "Asura (m3u8 directo)",
                "url": "https://www.mdnemonicplayer.xyz/nemonicplayer/redirector.php?slug="
                + m.group(1),
            }
        )

    # Servidor "tamamo": Dailymotion via api_donghua.php + dmplayer.php
    m = re.search(r'/api_donghua\.php"\s*,\s*data:\s*\{\s*"slug":"([^"]+)"', full)
    if m:
        try:
            key = _mundo_tamamo_key(m.group(1), base, url)
            if key:
                video_id = _mundo_dmplayer_video(key, url)
                if video_id:
                    sources.append(
                        {
                            "key": "tamamo",
                            "label": "Dailymotion (tamamo)",
                            "url": f"https://geo.dailymotion.com/player/x19frc.html?video={video_id}",
                        }
                    )
        except (DownloadError, ValueError) as e:
            print(f"  [aviso] fuente tamamo no disponible: {e}")

    # Servidores con iframe de terceros (puede que yt-dlp no los soporte)
    for key, host in [
        ("fmoon", "bysekoze.com/e"),
        ("amagi", "voe.sx/e"),
        ("vhide", "vidhidepro.com/v"),
        ("swish", "embedwish.com/e"),
    ]:
        m = re.search(rf"https://{re.escape(host)}/[a-z0-9]+", full)
        if m:
            sources.append({"key": key, "label": host.split(".")[0].capitalize(), "url": m.group(0)})

    return get_page_title(html, url), dedupe_sources(order_sources(sources, _SOURCE_PREFERENCE["mundo"]))


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def run_ytdlp(cmd, dry_run=False):
    print(f"\nEjecutando: {shlex.join(cmd)}")
    if dry_run:
        print("(dry-run)")
        return
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise DownloadError(f"yt-dlp termino con codigo {result.returncode}")


def build_generic_command(args):
    cmd = ["yt-dlp"]

    if args.music:
        output_template = f"{args.output}/%(title)s.%(ext)s"
        cmd.extend(["-x", "-f", "bestaudio/best"])
    elif args.playlist:
        output_template = f"{args.output}/%(playlist)s/%(title)s.%(ext)s"
    else:
        output_template = f"{args.output}/%(title)s.%(ext)s"

    if not args.music:
        if args.resolution != "best":
            height = args.resolution
            cmd.extend(
                ["-f", f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"]
            )
        else:
            cmd.extend(["-f", "bestvideo+bestaudio/best"])

    if args.subs:
        cmd.extend(["--write-subs", "--sub-lang", "en"])

    cmd.extend(["-o", output_template])
    cmd.append(args.url)

    return cmd


def build_facebook_command(args):
    """Como el generico, pero con ajustes especificos de Facebook.

    - User-Agent de navegador + Referer de facebook.com (Facebook bloquea
      peticiones que no parecen de un navegador).
    - Formato con respaldo /best cuando no existe un formato <= resolucion
      pedida (Facebook suele servir un unico archivo progresivo).
    - merge-output-format mp4 para que el resultado sea siempre .mp4.
    """
    cmd = [
        "yt-dlp",
        "--user-agent", USER_AGENT,
        "--add-header", "Referer:https://www.facebook.com/",
    ]

    if args.music:
        output_template = f"{args.output}/%(title)s.%(ext)s"
        cmd.extend(["-x", "-f", "bestaudio/best"])
    elif args.playlist:
        output_template = f"{args.output}/%(playlist)s/%(title)s.%(ext)s"
    else:
        output_template = f"{args.output}/%(title)s.%(ext)s"

    if not args.music:
        if args.resolution != "best":
            height = args.resolution
            cmd.extend(
                [
                    "-f",
                    f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
                ]
            )
        else:
            cmd.extend(["-f", "bestvideo+bestaudio/best"])
        cmd.extend(["--merge-output-format", "mp4"])

    if args.subs:
        cmd.extend(["--write-subs", "--sub-lang", "en"])

    cmd.extend(["-o", output_template])
    cmd.append(args.url)

    return cmd


def run_facebook(args):
    if not is_facebook_url(args.url):
        raise DownloadError(
            "--facebook solo acepta URLs de facebook.com, fb.watch o fb.me\n"
            f"Recibido: {args.url}"
        )
    run_ytdlp(build_facebook_command(args), args.dry_run)


def _download_source(args, title, output_dir, src):
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "-o", str(output_dir / f"{title}.%(ext)s"),
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--user-agent", USER_AGENT,
        "--add-header", f"Referer:{args.url}",
        src["url"],
    ]
    print(f"\nDescargando desde {src['label']}...")
    run_ytdlp(cmd, args.dry_run)


def run_donghua(args):
    site = detect_site(args.url)
    if not site:
        raise DownloadError(
            "--donghua soporta seriesdonghua.com, donghualife.com y mundodonghua.com"
        )

    try:
        if site == "series":
            print("Extrayendo servidores de seriesdonghua.com...")
            title, sources = extract_seriesdonghua_sources(args.url)
        elif site == "donghualife":
            print("Extrayendo fuentes de donghualife.com...")
            title, sources = extract_donghualife_sources(args.url)
        else:
            print("Extrayendo servidores de mundodonghua.com...")
            title, sources = extract_mundo_sources(args.url)
    except DownloadError as e:
        raise

    if not sources:
        raise DownloadError("No se encontraron fuentes descargables")

    available = ", ".join(f"{s['key']} ({s['label']})" for s in sources)

    if args.source:
        keys = [s["key"] for s in sources]
        if args.source not in keys:
            raise DownloadError(
                f"Fuente '{args.source}' no disponible para este episodio.\n"
                f"Opciones: {available}"
            )
        order = [keys.index(args.source)]
        fallback = False
    elif args.dry_run:
        order = list(range(len(sources)))
        fallback = False
    else:
        print("\nFuentes disponibles:")
        for i, s in enumerate(sources, 1):
            print(f"  [{i}] {s['label']:<22} -> {s['url']}")
        choice = input(
            f"\nSelecciona fuente [1-{len(sources)}] (default: 1): "
        ).strip()
        if not choice:
            choice = "1"
        try:
            chosen = int(choice) - 1
            if chosen < 0 or chosen >= len(sources):
                raise ValueError
        except ValueError:
            raise DownloadError("Opcion invalida")
        order = [chosen] + [i for i in range(len(sources)) if i != chosen]
        fallback = True

    output_dir = Path(args.output) / title
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = []
    for i, src in enumerate([sources[j] for j in order]):
        try:
            _download_source(args, title, output_dir, src)
            if not args.dry_run:
                print(f"\nDescarga completada: {output_dir / title}.mp4")
            return
        except DownloadError as e:
            errors.append(f"{src['label']}: {e}")
            if fallback and i < len(order) - 1:
                print(f"\n  [aviso] la fuente '{src['label']}' fallo: {e}")
                print("  Probando la siguiente fuente...")

    if fallback or len(errors) > 1 or not args.dry_run:
        raise DownloadError("Todas las fuentes fallaron:\n  " + "\n  ".join(errors))
    raise DownloadError(errors[0])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Descargador yt-dlp (generico, --facebook para facebook.com/fb.watch "
        "o --donghua para seriesdonghua.com, donghualife.com y mundodonghua.com)"
    )
    parser.add_argument("-u", "--url", required=True, help="URL a descargar")
    parser.add_argument(
        "-o",
        "--output",
        default=str(DOWNLOAD_DIR),
        help=f"Directorio de salida (default: {DOWNLOAD_DIR})",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-m", "--music", action="store_true", help="Descargar solo audio (musica)"
    )
    group.add_argument(
        "-p", "--playlist", action="store_true", help="Descargar como playlist"
    )

    parser.add_argument(
        "-r",
        "--resolution",
        choices=["480", "720", "1080", "best"],
        default="480",
        help="Resolucion maxima (default: 480)",
    )
    parser.add_argument(
        "-s",
        "--subs",
        action="store_true",
        help="Descargar subtitulos (ingles)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--donghua",
        action="store_true",
        help="Flujo de extraccion para seriesdonghua.com, donghualife.com y "
        "mundodonghua.com",
    )
    mode.add_argument(
        "--facebook",
        action="store_true",
        help="Flujo optimizado para URLs de facebook.com / fb.watch / fb.me "
        "(UA de navegador, referer, formato con respaldo y salida mp4)",
    )
    parser.add_argument(
        "--source",
        help="Clave de fuente para --donghua (si no se pasa, se muestra el menu "
        "y se reintenta con el resto)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar el comando yt-dlp sin ejecutarlo",
    )

    args = parser.parse_args()

    if shutil.which("yt-dlp") is None:
        parser.error("yt-dlp no esta instalado (pip install yt-dlp)")

    try:
        if args.donghua:
            run_donghua(args)
        elif args.facebook:
            run_facebook(args)
        else:
            run_ytdlp(build_generic_command(args), args.dry_run)
    except DownloadError as e:
        print(f"\nError: {e}")
        return 1

    if not args.donghua and not args.dry_run:
        print("\nDescarga completada")
    return 0


if __name__ == "__main__":
    sys.exit(main())