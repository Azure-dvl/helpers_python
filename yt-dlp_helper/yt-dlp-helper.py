#!/usr/bin/env python3

import argparse
import subprocess
import os

DOWNLOAD_DIR = os.path.expanduser("~/Downloads")


def build_command(args):
    cmd = ["yt-dlp"]

    if args.music:
        cmd.extend(["-x", "--audio-format", "best"])
        output_template = f"{DOWNLOAD_DIR}/%(title)s.%(ext)s"
    elif args.playlist:
        output_template = f"{DOWNLOAD_DIR}/%(playlist)s/%(title)s.%(ext)s"
    else:
        output_template = f"{DOWNLOAD_DIR}/%(title)s.%(ext)s"

    if args.resolution and args.resolution != "best":
        height = args.resolution
        cmd.extend(
            ["-f", f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"]
        )
    elif args.resolution == "best":
        cmd.extend(["-f", "bestvideo+bestaudio/best"])
    else:
        cmd.extend(["-f", "bestvideo[height<=480]+bestaudio/best[height<=480]"])

    if args.subs:
        cmd.extend(["--write-subs", "--sub-lang", "en"])

    cmd.extend(["-o", output_template])
    cmd.append(args.url)

    return cmd


def main():
    parser = argparse.ArgumentParser(description=" yt-dlp helper")
    parser.add_argument("-u", "--url", required=True, help="Video or playlist URL")
    parser.add_argument(
        "-s", "--subs", action="store_true", help="Download subtitles (English)"
    )
    parser.add_argument(
        "-r",
        "--resolution",
        choices=["480", "720", "1080", "best"],
        help="Video resolution",
    )
    parser.add_argument(
        "-p", "--playlist", action="store_true", help="Download as playlist"
    )
    parser.add_argument(
        "-m", "--music", action="store_true", help="Download only audio (music)"
    )

    args = parser.parse_args()

    cmd = build_command(args)
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
