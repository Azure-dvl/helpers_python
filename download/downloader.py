#!/usr/bin/env python3

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
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

_PLATFORMS = {
    "asura": ("DailyMotion", "https://www.dailymotion.com/embed/video/"),
    "skadi": ("OK.ru", None),
    "fembed": ("Rumble", None),
    "tape": ("Odysee", None),
    "amagi": ("Voe.sx", None),
}


class DownloadError(Exception):
    pass


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "download"


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


def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_video_map(html):
    pattern = (
        r'eval\(function\([^)]*\)\s*\{.*?'
        r'return decodeURIComponent\(escape\(r\)\)\}\s*'
        r'\(\s*"([^"]+)"\s*,(\d+)\s*,\s*"([^"]+)"\s*,(\d+)\s*,(\d+)\s*,(\d+)\s*\)\s*\)'
    )
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        raise ValueError("No se encontro el script ofuscado en la pagina")

    encoded = match.group(1)
    n_chars = match.group(3)
    t = int(match.group(4))
    e = int(match.group(5))

    decoded = decode_script(encoded, n_chars, t, e)

    json_match = re.search(r"VIDEO_MAP_JSON=(\{)", decoded)
    if not json_match:
        raise ValueError("No se pudo extraer VIDEO_MAP_JSON")

    start = json_match.start(1)
    depth = 0
    end = start
    for i, c in enumerate(decoded[start:], start=start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    raw_json = decoded[start:end]
    clean_json = js_unescape(raw_json)
    outer = json.loads(clean_json)
    result = {}
    for key, val in outer.items():
        result[key] = json.loads(val)
    return result


def get_page_title(html, url):
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if title:
            return sanitize_filename(title)
    slug = urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]
    return sanitize_filename(slug)


def build_available_sources(video_map):
    sources = []
    for key in ["asura", "skadi", "fembed", "tape", "amagi"]:
        src = video_map.get(key)
        if not src:
            continue
        name, prefix = _PLATFORMS[key]
        url = (prefix + src) if prefix else src
        sources.append((name, url, key))
    return sources


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


def run_ytdlp(cmd, dry_run=False):
    print(f"\nEjecutando: {shlex.join(cmd)}")
    if dry_run:
        print("(dry-run)")
        return
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise DownloadError(f"yt-dlp termino con codigo {result.returncode}")


def run_donghua(args):
    try:
        html = fetch_html(args.url)
    except Exception as e:
        raise DownloadError(f"Error al obtener la pagina: {e}")

    try:
        video_map = extract_video_map(html)
    except ValueError as e:
        raise DownloadError(str(e))

    title = get_page_title(html, args.url)

    sources = build_available_sources(video_map)
    if not sources:
        raise DownloadError("No se encontraron fuentes disponibles")

    source_keys = [key for _, _, key in sources]
    if args.source:
        if args.source not in source_keys:
            raise DownloadError(
                f"Fuente '{args.source}' no disponible. Opciones: {', '.join(source_keys)}"
            )
        idx = source_keys.index(args.source)
    else:
        print("\nFuentes disponibles:")
        for i, (name, url, _) in enumerate(sources, 1):
            print(f"  [{i}] {name:<12} -> {url}")
        choice = input(
            f"\nSelecciona fuente [1-{len(sources)}] (default: 1): "
        ).strip()
        if not choice:
            choice = "1"
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(sources):
                raise ValueError
        except ValueError:
            raise DownloadError("Opcion invalida")

    name, url, _ = sources[idx]
    print(f"\nDescargando desde {name}...")

    output_dir = Path(args.output) / title
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "-o", str(output_dir / f"{title}.%(ext)s"),
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--user-agent", USER_AGENT,
        url,
    ]
    run_ytdlp(cmd, args.dry_run)

    if not args.dry_run:
        print(f"\nDescarga completada: {output_dir / title}.mp4")


def main():
    parser = argparse.ArgumentParser(
        description="Descargador yt-dlp (seriesdonghua.com con --donghua)"
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
    parser.add_argument(
        "--donghua",
        action="store_true",
        help="Usar el flujo de extraccion de seriesdonghua.com",
    )
    parser.add_argument(
        "--source",
        choices=list(_PLATFORMS),
        help="Fuente para --donghua (si no se pasa, se muestra el menu)",
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
        else:
            run_ytdlp(build_generic_command(args), args.dry_run)
    except DownloadError as e:
        print(f"\nError: {e}")
        return 1

    if not args.donghua:
        print("\nDescarga completada")
    return 0


if __name__ == "__main__":
    sys.exit(main())