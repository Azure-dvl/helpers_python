"""Tests de python_utils/create_pdf.py (sin red: solo items sin foto)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_utils"))

import create_pdf  # noqa: E402


class LoadJsonDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, name, content):
        path = self.dir / name
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(json.dumps(content), encoding="utf-8")
        return str(path)

    def test_valid_list_of_objects(self):
        path = self.write("ok.json", [{"name": "A", "year": "2020"}])
        self.assertEqual(create_pdf.load_json_data(path), [{"name": "A", "year": "2020"}])

    def test_empty_list_is_valid(self):
        path = self.write("empty.json", [])
        self.assertEqual(create_pdf.load_json_data(path), [])

    def test_object_instead_of_list_raises(self):
        path = self.write("dict.json", {"name": "A"})
        with self.assertRaises(ValueError) as ctx:
            create_pdf.load_json_data(path)
        self.assertIn("dict.json", str(ctx.exception))

    def test_list_of_strings_raises(self):
        path = self.write("strings.json", ["a", "b"])
        with self.assertRaises(ValueError) as ctx:
            create_pdf.load_json_data(path)
        self.assertIn("[0]", str(ctx.exception))

    def test_invalid_json_raises_value_error(self):
        path = self.write("broken.json", "{no es json")
        with self.assertRaises(ValueError):
            create_pdf.load_json_data(path)

    def test_missing_file_raises_os_error(self):
        with self.assertRaises(OSError):
            create_pdf.load_json_data(str(self.dir / "no-existe.json"))


class CreatePdfTest(unittest.TestCase):
    def test_builds_pdf_from_json_without_photos(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "peliculas.json"
            src.write_text(
                json.dumps(
                    [
                        {"name": "Pelicula A", "year": "2020"},
                        {"name": "Pelicula B", "year": "2021"},
                    ]
                ),
                encoding="utf-8",
            )
            out = Path(tmp) / "salida.pdf"
            create_pdf.create_pdf(str(out), [str(src)])
            self.assertTrue(out.is_file())
            self.assertEqual(out.read_bytes()[:5], b"%PDF-")

    def test_main_returns_1_on_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "mal.json"
            bad.write_text('{"no": "es una lista"}', encoding="utf-8")
            out = str(Path(tmp) / "out.pdf")
            argv = ["create_pdf.py", str(bad), "-o", out]
            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(create_pdf.main(), 1)

    def test_main_returns_0_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "ok.json"
            src.write_text(json.dumps([{"name": "A"}]), encoding="utf-8")
            out = str(Path(tmp) / "out.pdf")
            argv = ["create_pdf.py", str(src), "-o", out]
            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(create_pdf.main(), 0)
            self.assertTrue(Path(out).is_file())


if __name__ == "__main__":
    unittest.main()
