"""Tests de las partes puras de download/downloader.py (sin red ni yt-dlp)."""

import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "download"))

import downloader  # noqa: E402


def make_args(**overrides):
    defaults = dict(
        url="https://example.com/v",
        output="/tmp/out",
        music=False,
        playlist=False,
        resolution="480",
        subs=False,
        cookies_from_browser=None,
        dry_run=False,
        donghua=False,
        facebook=False,
        source=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class SanitizeFilenameTest(unittest.TestCase):
    def test_removes_invalid_chars(self):
        self.assertEqual(downloader.sanitize_filename('a<b>:c"d/e\\f|g?h*i'), "abcdefghi")

    def test_collapses_whitespace_and_trims(self):
        self.assertEqual(downloader.sanitize_filename("  Ep  01  . "), "Ep 01")

    def test_empty_becomes_download(self):
        self.assertEqual(downloader.sanitize_filename('  <>:"/\\|?*  '), "download")

    def test_truncates_long_titles_by_bytes(self):
        title = "x" * 500
        result = downloader.sanitize_filename(title)
        self.assertLessEqual(len(result.encode("utf-8")), 200)
        self.assertEqual(len(result), 200)

    def test_multibyte_truncation_keeps_valid_utf8(self):
        result = downloader.sanitize_filename("日" * 300)
        self.assertLessEqual(len(result.encode("utf-8")), 200)
        # No debe cortar a mitad de un caracter multibyte
        self.assertTrue(result.endswith("日"))


class DetectSiteTest(unittest.TestCase):
    def test_known_sites(self):
        self.assertEqual(downloader.detect_site("https://seriesdonghua.com/x/1"), "series")
        self.assertEqual(downloader.detect_site("https://donghualife.com/watch/a"), "donghualife")
        self.assertEqual(downloader.detect_site("https://www.mundodonghua.com/ver/a/1"), "mundo")

    def test_unknown_site(self):
        self.assertIsNone(downloader.detect_site("https://youtube.com/watch?v=1"))


class IsFacebookUrlTest(unittest.TestCase):
    def test_matches_hosts_and_subdomains(self):
        for url in (
            "https://www.facebook.com/watch/?v=1",
            "https://es-la.facebook.com/foo",
            "https://fb.watch/abc/",
            "https://fb.me/abc",
            "https://facebook.com:443/x",
        ):
            self.assertTrue(downloader.is_facebook_url(url), url)

    def test_rejects_other_hosts(self):
        for url in ("https://notfacebook.com/x", "https://youtube.com/x", "https://fb.foo.com/x"):
            self.assertFalse(downloader.is_facebook_url(url), url)


class LabelForEmbedTest(unittest.TestCase):
    def test_m3u8_is_directo(self):
        self.assertEqual(
            downloader.label_for_embed("https://cdn.example.com/hls/ep.m3u8?tok=1"),
            ("Directo (m3u8)", "directo"),
        )

    def test_known_hosts(self):
        self.assertEqual(
            downloader.label_for_embed("https://dailymotion.com/embed/video/abc"),
            ("Dailymotion", "dailymotion"),
        )
        self.assertEqual(
            downloader.label_for_embed("https://ok.ru/videoembed/1"), ("OK.ru", "okru")
        )

    def test_unknown_host_falls_back_to_host(self):
        label, key = downloader.label_for_embed("https://player.unknown-site.tv/e/abc")
        self.assertEqual(label, "player_unknown-site_tv")
        self.assertEqual(key, "player_unknown-site_tv")


class SourcesTest(unittest.TestCase):
    def test_order_sources_puts_preference_first(self):
        sources = [
            {"key": "voe", "url": "u1"},
            {"key": "dailymotion", "url": "u2"},
            {"key": "otro", "url": "u3"},
        ]
        ordered = downloader.order_sources(sources, ["dailymotion", "okru"])
        self.assertEqual([s["key"] for s in ordered], ["dailymotion", "voe", "otro"])

    def test_dedupe_sources_drops_repeated_urls_and_keys(self):
        sources = [
            {"key": "directo", "url": "u1"},
            {"key": "directo", "url": "u1"},
            {"key": "directo", "url": "u2"},
        ]
        out = downloader.dedupe_sources(sources)
        self.assertEqual(len(out), 2)
        self.assertEqual([s["key"] for s in out], ["directo", "directo-2"])


class PackerDecodeTest(unittest.TestCase):
    def test_decodes_simple_packer(self):
        self.assertEqual(downloader.packer_decode("0=1", 2, "ab|cd"), "ab=cd")

    def test_longest_codes_replaced_first(self):
        # a=36 -> codigos "0".."z" y "10" (indice 36): "10" debe sustituirse
        # primero; si no, se reemplazarian por separado "1" y "0".
        keys = [f"v{i}" for i in range(36)] + ["url"]
        self.assertEqual(downloader.packer_decode("10", 36, "|".join(keys)), "url")


class LegacyDecodeTest(unittest.TestCase):
    def test_decode_base(self):
        self.assertEqual(downloader.decode_base("101", 2, 10), "5")
        self.assertEqual(downloader.decode_base("ff", 16, 10), "255")
        self.assertEqual(downloader.decode_base("z", 36, 10), "35")


class BuildCommandTest(unittest.TestCase):
    def test_generic_resolution_format(self):
        cmd = downloader.build_generic_command(make_args(resolution="720"))
        self.assertIn("bestvideo[height<=720]+bestaudio/best[height<=720]", cmd)
        self.assertIn("/tmp/out/%(title)s.%(ext)s", cmd)
        self.assertEqual(cmd[-1], "https://example.com/v")

    def test_generic_best_resolution(self):
        cmd = downloader.build_generic_command(make_args(resolution="best"))
        self.assertIn("bestvideo+bestaudio/best", cmd)

    def test_generic_music_extracts_audio_only(self):
        cmd = downloader.build_generic_command(make_args(music=True))
        self.assertIn("-x", cmd)
        self.assertIn("bestaudio/best", cmd)
        # Con -m no se debe inyectar el formato de video
        self.assertNotIn("bestvideo+bestaudio/best", cmd)

    def test_generic_playlist_template(self):
        cmd = downloader.build_generic_command(make_args(playlist=True))
        self.assertIn("/tmp/out/%(playlist)s/%(title)s.%(ext)s", cmd)

    def test_generic_cookies_from_browser_is_not_ignored(self):
        cmd = downloader.build_generic_command(make_args(cookies_from_browser="chrome:Default"))
        idx = cmd.index("--cookies-from-browser")
        self.assertEqual(cmd[idx + 1], "chrome:Default")

    def test_facebook_command_has_browser_fingerprint(self):
        cmd = downloader.build_facebook_command(
            make_args(facebook=True, resolution="720", cookies_from_browser="firefox")
        )
        self.assertIn("--user-agent", cmd)
        self.assertIn("Referer:https://www.facebook.com/", cmd)
        self.assertIn("--merge-output-format", cmd)
        # Resolucion con respaldo /best para Facebook
        self.assertIn(
            "bestvideo[height<=720]+bestaudio/best[height<=720]/best", cmd
        )
        idx = cmd.index("--cookies-from-browser")
        self.assertEqual(cmd[idx + 1], "firefox")

    def test_facebook_rejects_non_facebook_url(self):
        with self.assertRaises(downloader.DownloadError):
            downloader.run_facebook(make_args(facebook=True))


class ChooseSourceTest(unittest.TestCase):
    SOURCES = [
        {"key": "a", "label": "Fuente A", "url": "https://a"},
        {"key": "b", "label": "Fuente B", "url": "https://b"},
    ]

    def test_empty_input_selects_first(self):
        with mock.patch("builtins.input", return_value=""):
            self.assertEqual(downloader.choose_source(self.SOURCES), 0)

    def test_numeric_input_is_one_based(self):
        with mock.patch("builtins.input", return_value="2"):
            self.assertEqual(downloader.choose_source(self.SOURCES), 1)

    def test_eof_falls_back_to_first_source(self):
        # Sin TTY (stdin cerrada) no debe morir con traceback
        with mock.patch("builtins.input", side_effect=EOFError):
            self.assertEqual(downloader.choose_source(self.SOURCES), 0)

    def test_invalid_option_raises(self):
        with mock.patch("builtins.input", return_value="nope"):
            with self.assertRaises(downloader.DownloadError):
                downloader.choose_source(self.SOURCES)
        with mock.patch("builtins.input", return_value="99"):
            with self.assertRaises(downloader.DownloadError):
                downloader.choose_source(self.SOURCES)

    def test_ctrl_c_raises_clean_error(self):
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            with self.assertRaises(downloader.DownloadError):
                downloader.choose_source(self.SOURCES)


class RunYtdlpTest(unittest.TestCase):
    def test_dry_run_does_not_execute(self):
        with mock.patch.object(downloader.subprocess, "run") as run:
            downloader.run_ytdlp(["yt-dlp", "--version"], dry_run=True)
            run.assert_not_called()

    def test_nonzero_exit_raises(self):
        completed = mock.Mock(returncode=3)
        with mock.patch.object(downloader.subprocess, "run", return_value=completed):
            with self.assertRaises(downloader.DownloadError):
                downloader.run_ytdlp(["yt-dlp", "--version"])


class DonghuaFlowTest(unittest.TestCase):
    """run_donghua() con las extracciones y yt-dlp simulados (sin red)."""

    SOURCES = [
        {"key": "dailymotion", "label": "Dailymotion", "url": "https://a"},
        {"key": "okru", "label": "OK.ru", "url": "https://b"},
    ]

    def run_donghua(self, args):
        with mock.patch.object(downloader, "detect_site", return_value="series"), \
            mock.patch.object(
                downloader,
                "extract_seriesdonghua_sources",
                return_value=("Mi Episodio 1", self.SOURCES),
            ), \
            mock.patch.object(downloader, "run_ytdlp") as run:
            downloader.run_donghua(args)
        return run

    def test_dry_run_does_not_create_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "no-debe-crearse"
            args = make_args(
                donghua=True,
                url="https://seriesdonghua.com/ep/1",
                output=str(out),
                source="dailymotion",
                dry_run=True,
            )
            self.run_donghua(args)
            self.assertFalse(out.exists())

    def test_download_creates_dir_and_uses_forced_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "salida"
            args = make_args(
                donghua=True,
                url="https://seriesdonghua.com/ep/1",
                output=str(out),
                source="okru",
                cookies_from_browser="chrome:Default",
            )
            run = self.run_donghua(args)
            self.assertTrue((out / "Mi Episodio 1").is_dir())
            cmd = run.call_args[0][0]
            # Fuente forzada, no la primera
            self.assertEqual(cmd[-1], "https://b")
            self.assertEqual(
                cmd[cmd.index("--cookies-from-browser") + 1], "chrome:Default"
            )

    def test_unknown_source_lists_available_keys(self):
        args = make_args(
            donghua=True,
            url="https://seriesdonghua.com/ep/1",
            source="noexiste",
            dry_run=True,
        )
        with self.assertRaises(downloader.DownloadError) as ctx:
            self.run_donghua(args)
        self.assertIn("dailymotion", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
