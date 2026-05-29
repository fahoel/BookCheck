import io
import os
import runpy
import subprocess
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


class ScannerCv2Tests(unittest.TestCase):
    """Tests for the cv2 (desktop) backend."""

    def _cv2_patches(self, cap, detector):
        """Return a context manager that injects a mock cv2 into scanner."""
        import contextlib

        mock_cv2 = MagicMock()
        mock_cv2.VideoCapture.return_value = cap
        mock_cv2.barcode.BarcodeDetector.return_value = detector
        mock_cv2.waitKey.return_value = -1

        @contextlib.contextmanager
        def _ctx():
            original_cv2 = getattr(scanner, "cv2", None)
            original_flag = scanner._CV2_AVAILABLE
            scanner.cv2 = mock_cv2
            scanner._CV2_AVAILABLE = True
            try:
                yield mock_cv2
            finally:
                if original_cv2 is None:
                    try:
                        del scanner.cv2
                    except AttributeError:
                        pass
                else:
                    scanner.cv2 = original_cv2
                scanner._CV2_AVAILABLE = original_flag

        return _ctx()

    def test_scan_isbn_handles_camera_unavailable(self):
        cap = MagicMock()
        cap.isOpened.return_value = False
        detector = MagicMock()

        with self._cv2_patches(cap, detector), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            isbn = scanner.scan_isbn()

        self.assertIsNone(isbn)
        self.assertIn("Error: Could not open camera.", output.getvalue())

    def test_scan_isbn_detects_and_returns_isbn(self):
        cap = MagicMock()
        cap.isOpened.return_value = True
        cap.read.return_value = (True, object())

        detector = MagicMock()
        detector.detectAndDecodeMulti.return_value = (True, ["9780140328721"], None, None)

        with self._cv2_patches(cap, detector), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            isbn = scanner.scan_isbn()

        self.assertEqual("9780140328721", isbn)
        cap.release.assert_called_once()
        self.assertIn("ISBN detected: 9780140328721", output.getvalue())


class ScannerTermuxTests(unittest.TestCase):
    """Tests for the Termux (mobile) backend."""

    def test_termux_detects_and_returns_isbn(self):
        mock_result = MagicMock()
        mock_result.text = "9780140328721"

        with patch("scanner._CV2_AVAILABLE", False), patch(
            "subprocess.run"
        ) as run_mock, patch("scanner.zxingcpp") as zxing_mock, patch(
            "scanner.Image"
        ) as img_mock, patch(
            "tempfile.NamedTemporaryFile"
        ) as ntf_mock, patch(
            "pathlib.Path.unlink"
        ), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            ntf = MagicMock()
            ntf.name = "/tmp/scan_test.jpg"
            ntf_mock.return_value = ntf

            zxing_mock.read_barcodes.return_value = [mock_result]

            # Reload so the lazy imports inside _scan_isbn_termux pick up the mocks
            isbn = scanner._scan_isbn_termux()

        run_mock.assert_called_once()
        self.assertEqual("9780140328721", isbn)
        self.assertIn("ISBN detected: 9780140328721", output.getvalue())

    def test_termux_returns_none_when_no_barcode_found(self):
        with patch("scanner._CV2_AVAILABLE", False), patch(
            "subprocess.run"
        ), patch("scanner.zxingcpp") as zxing_mock, patch(
            "scanner.Image"
        ), patch(
            "tempfile.NamedTemporaryFile"
        ) as ntf_mock, patch(
            "pathlib.Path.unlink"
        ), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            ntf = MagicMock()
            ntf.name = "/tmp/scan_test.jpg"
            ntf_mock.return_value = ntf

            zxing_mock.read_barcodes.return_value = []

            isbn = scanner._scan_isbn_termux()

        self.assertIsNone(isbn)
        self.assertIn("No barcode found in photo.", output.getvalue())

    def test_termux_handles_camera_failure(self):
        with patch("scanner._CV2_AVAILABLE", False), patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "termux-camera-photo"),
        ), patch("scanner.zxingcpp"), patch(
            "scanner.Image"
        ), patch(
            "tempfile.NamedTemporaryFile"
        ) as ntf_mock, patch(
            "pathlib.Path.unlink"
        ), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            ntf = MagicMock()
            ntf.name = "/tmp/scan_test.jpg"
            ntf_mock.return_value = ntf

            isbn = scanner._scan_isbn_termux()

        self.assertIsNone(isbn)
        self.assertIn("Error: Camera capture failed:", output.getvalue())

    def test_termux_handles_missing_termux_api(self):
        with patch("scanner._CV2_AVAILABLE", False), patch(
            "subprocess.run", side_effect=FileNotFoundError
        ), patch("scanner.zxingcpp"), patch(
            "scanner.Image"
        ), patch(
            "tempfile.NamedTemporaryFile"
        ) as ntf_mock, patch(
            "pathlib.Path.unlink"
        ), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            ntf = MagicMock()
            ntf.name = "/tmp/scan_test.jpg"
            ntf_mock.return_value = ntf

            isbn = scanner._scan_isbn_termux()

        self.assertIsNone(isbn)
        self.assertIn("termux-camera-photo not found", output.getvalue())

    def test_scan_isbn_dispatches_to_termux_when_cv2_unavailable(self):
        with patch("scanner._CV2_AVAILABLE", False), patch(
            "scanner._scan_isbn_termux", return_value="9780140328721"
        ) as termux_fn:
            isbn = scanner.scan_isbn()

        termux_fn.assert_called_once()
        self.assertEqual("9780140328721", isbn)


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
            library_file = Path(tmpdir) / "library.json"
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
