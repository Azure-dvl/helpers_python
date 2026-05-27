#!/usr/bin/env python3

import argparse
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DOWNLOAD_DIR = Path.home() / "Downloads"

_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"

_PLATFORMS = {
    "asura": ("DailyMotion", "https://www.dailymotion.com/embed/video/"),
    "skadi": ("OK.ru", None),
    "fembed": ("Rumble", None),
    "tape": ("Odysee", None),
    "amagi": ("Voe.sx", None),
}


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
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
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
        raise ValueError("No se encontró el script ofuscado en la página")

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


def download_video(url, output_dir, filename):
    output_path = str(Path(output_dir) / f"{filename}.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "-o", output_path,
        "--merge-output-format", "mp4",
        "--no-playlist",
        url,
    ]
    print(f"\nEjecutando: yt-dlp {' '.join(cmd[1:])}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\nError durante la descarga.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Descargar streams de seriesdonghua.com"
    )
    parser.add_argument("-u", "--url", required=True, help="URL del episodio")
    parser.add_argument(
        "-o",
        "--output",
        default=str(DOWNLOAD_DIR),
        help="Directorio de salida (default: ~/Downloads/donghua)",
    )
    args = parser.parse_args()

    print("Analizando pagina...")
    try:
        html = fetch_html(args.url)
    except Exception as e:
        print(f"Error al obtener la pagina: {e}")
        sys.exit(1)

    try:
        video_map = extract_video_map(html)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    title = args.url.rstrip("/").rstrip("/").split("/")[-1]

    sources = []
    for key in ["asura", "skadi", "fembed", "tape", "amagi"]:
        src = video_map.get(key)
        if not src:
            continue
        name, prefix = _PLATFORMS[key]
        url = (prefix + src) if prefix else src
        sources.append((name, url, key))

    print("\nFuentes disponibles:")
    for i, (name, url, _) in enumerate(sources, 1):
        print(f"  [{i}] {name:<12} -> {url}")

    choice = input(f"\nSelecciona fuente [1-{len(sources)}] (default: 1): ").strip()
    if not choice:
        choice = "1"
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(sources):
            raise ValueError
    except ValueError:
        print("Opcion invalida")
        sys.exit(1)

    name, url, key = sources[idx]
    print(f"\nDescargando desde {name}...")

    output_dir = Path(args.output) / title
    output_dir.mkdir(parents=True, exist_ok=True)

    download_video(url, output_dir, title)

    print(f"\nDescarga completada: {output_dir / title}.mp4")


if __name__ == "__main__":
    main()
