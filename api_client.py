"""api_client.py – Fetch book metadata from the Open Library API."""

import requests


def fetch_book_data(isbn: str) -> dict | None:
    """Fetch book metadata for *isbn* from Open Library.

    Returns a dict with keys: isbn, title, authors, cover_url, pages.
    Returns None if the book is not found or the request fails.
    """
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Network error: {exc}")
        return None

    data = response.json()
    key = f"ISBN:{isbn}"
    if key not in data:
        print(f"No data found for ISBN {isbn}.")
        return None

    book = data[key]
    return {
        "isbn": isbn,
        "title": book.get("title", "Unknown"),
        "authors": [a.get("name", "Unknown Author") for a in book.get("authors", [])],
        "cover_url": book.get("cover", {}).get("large", ""),
        "pages": book.get("number_of_pages"),
    }


if __name__ == "__main__":
    import sys

    isbn_arg = sys.argv[1] if len(sys.argv) > 1 else "9780140328721"
    info = fetch_book_data(isbn_arg)
    if info:
        for k, v in info.items():
            print(f"{k}: {v}")
