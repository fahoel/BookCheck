"""database.py – Persist book records in library.json (no duplicates)."""

import json
from pathlib import Path

LIBRARY_FILE = Path("library.json")


def _load() -> list:
    if LIBRARY_FILE.exists():
        with LIBRARY_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return []


def _save(library: list) -> None:
    with LIBRARY_FILE.open("w", encoding="utf-8") as fh:
        json.dump(library, fh, indent=2, ensure_ascii=False)


def add_book(book: dict) -> bool:
    """Append *book* to library.json.

    Returns True if added, False if the ISBN already exists.
    """
    library = _load()
    isbn = book.get("isbn")
    if not isbn:
        print("Book has no ISBN; cannot save.")
        return False
    if any(b.get("isbn") == isbn for b in library):
        print(f"Book with ISBN {isbn} already in library.")
        return False
    library.append(book)
    _save(library)
    print(f"Saved: {book.get('title')} ({isbn})")
    return True


def list_books() -> list:
    """Return all books currently stored in library.json."""
    return _load()


if __name__ == "__main__":
    for entry in list_books():
        print(entry.get("title"), "-", entry.get("isbn"))
