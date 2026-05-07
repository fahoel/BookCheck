import io
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import api_client
import database
import main
import scanner


class MainWorkflowTests(unittest.TestCase):
    def test_run_happy_path_prints_metadata_and_saves_book(self):
        book = {
            "isbn": "9780140328721",
            "title": "Matilda",
            "authors": ["Roald Dahl"],
            "pages": 240,
            "cover_url": "https://example.com/cover.jpg",
        }

        with patch("main.scan_isbn", return_value=book["isbn"]), patch(
            "main.fetch_book_data", return_value=book
        ), patch("main.add_book", return_value=True) as add_book, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            main.run()

        add_book.assert_called_once_with(book)
        text = output.getvalue()
        self.assertIn("Title:    Matilda", text)
        self.assertIn("Authors:  Roald Dahl", text)
        self.assertIn("Pages:    240", text)
        self.assertIn("Cover:    https://example.com/cover.jpg", text)

    def test_run_exits_when_no_isbn(self):
        with patch("main.scan_isbn", return_value=None), patch(
            "main.fetch_book_data"
        ) as fetch, patch("main.add_book") as add_book, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            main.run()

        fetch.assert_not_called()
        add_book.assert_not_called()
        self.assertIn("No ISBN scanned. Exiting.", output.getvalue())

    def test_run_exits_when_book_not_found(self):
        with patch("main.scan_isbn", return_value="9780140328721"), patch(
            "main.fetch_book_data", return_value=None
        ), patch("main.add_book") as add_book, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            main.run()

        add_book.assert_not_called()
        self.assertIn("Could not fetch book data. Exiting.", output.getvalue())


class DatabaseTests(unittest.TestCase):
    def test_add_book_blocks_duplicates(self):
        book = {
            "isbn": "9780140328721",
            "title": "Matilda",
            "authors": ["Roald Dahl"],
            "pages": 240,
            "cover_url": "https://example.com/cover.jpg",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            library_file = Path(tmpdir) / "library.json"
            with patch.object(database, "LIBRARY_FILE", library_file):
                first = database.add_book(book)
                second = database.add_book(book)
                books = database.list_books()

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(1, len(books))
        self.assertEqual(book["isbn"], books[0]["isbn"])


class ApiClientTests(unittest.TestCase):
    def test_fetch_book_data_success(self):
        isbn = "9780140328721"
        payload = {
            f"ISBN:{isbn}": {
                "title": "Matilda",
                "authors": [{"name": "Roald Dahl"}],
                "cover": {"large": "https://example.com/cover.jpg"},
                "number_of_pages": 240,
            }
        }

        response = MagicMock()
        response.json.return_value = payload

        with patch("api_client.requests.get", return_value=response) as get:
            book = api_client.fetch_book_data(isbn)

        get.assert_called_once()
        self.assertEqual(isbn, book["isbn"])
        self.assertEqual("Matilda", book["title"])
        self.assertEqual(["Roald Dahl"], book["authors"])

    def test_fetch_book_data_handles_missing_data(self):
        response = MagicMock()
        response.json.return_value = {}

        with patch("api_client.requests.get", return_value=response), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            book = api_client.fetch_book_data("9780140328721")

        self.assertIsNone(book)
        self.assertIn("No data found for ISBN", output.getvalue())

    def test_fetch_book_data_handles_network_error(self):
        with patch(
            "api_client.requests.get", side_effect=api_client.requests.RequestException("offline")
        ), patch("sys.stdout", new_callable=io.StringIO) as output:
            book = api_client.fetch_book_data("9780140328721")

        self.assertIsNone(book)
        self.assertIn("Network error:", output.getvalue())


class ScannerTests(unittest.TestCase):
    def test_scan_isbn_handles_camera_unavailable(self):
        cap = MagicMock()
        cap.isOpened.return_value = False

        with patch("scanner.cv2.VideoCapture", return_value=cap), patch(
            "scanner.cv2.barcode.BarcodeDetector"
        ), patch("sys.stdout", new_callable=io.StringIO) as output:
            isbn = scanner.scan_isbn()

        self.assertIsNone(isbn)
        self.assertIn("Error: Could not open camera.", output.getvalue())

    def test_scan_isbn_detects_and_returns_isbn(self):
        cap = MagicMock()
        cap.isOpened.return_value = True
        cap.read.return_value = (True, object())

        detector = MagicMock()
        detector.detectAndDecodeMulti.return_value = (True, ["9780140328721"], None, None)

        with patch("scanner.cv2.VideoCapture", return_value=cap), patch(
            "scanner.cv2.barcode.BarcodeDetector", return_value=detector
        ), patch("scanner.cv2.imshow"), patch("scanner.cv2.waitKey", return_value=-1), patch(
            "scanner.cv2.destroyAllWindows"
        ), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            isbn = scanner.scan_isbn()

        self.assertEqual("9780140328721", isbn)
        cap.release.assert_called_once()
        self.assertIn("ISBN detected: 9780140328721", output.getvalue())


class ModuleCliTests(unittest.TestCase):
    def test_main_module_runs_workflow(self):
        book = {
            "isbn": "9780140328721",
            "title": "Matilda",
            "authors": ["Roald Dahl"],
            "pages": 240,
            "cover_url": "https://example.com/cover.jpg",
        }
        with patch("scanner.scan_isbn", return_value=book["isbn"]), patch(
            "api_client.fetch_book_data", return_value=book
        ), patch("database.add_book", return_value=True) as add_book, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            runpy.run_module("main", run_name="__main__")

        add_book.assert_called_once_with(book)
        self.assertIn("Title:    Matilda", output.getvalue())

    def test_database_module_lists_books_without_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            library_file = Path(tmpdir, "library.json")
            library_file.write_text(
                '[{"title": "Matilda", "isbn": "9780140328721"}]', encoding="utf-8"
            )
            cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.stdout", new_callable=io.StringIO) as output:
                    runpy.run_module("database", run_name="__main__")
            finally:
                os.chdir(cwd)

        text = output.getvalue()
        self.assertIn("Matilda - 9780140328721", text)

    def test_api_client_module_prints_fields(self):
        isbn = "9780140328721"
        payload = {
            f"ISBN:{isbn}": {
                "title": "Matilda",
                "authors": [{"name": "Roald Dahl"}],
                "cover": {"large": "https://example.com/cover.jpg"},
                "number_of_pages": 240,
            }
        }
        response = MagicMock()
        response.json.return_value = payload

        with patch("requests.get", return_value=response), patch(
            "sys.argv", ["api_client.py", isbn]
        ), patch("sys.stdout", new_callable=io.StringIO) as output:
            runpy.run_module("api_client", run_name="__main__")

        text = output.getvalue()
        self.assertIn("title: Matilda", text)
        self.assertIn("authors: ['Roald Dahl']", text)


if __name__ == "__main__":
    unittest.main()
