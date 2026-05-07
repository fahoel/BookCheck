"""main.py – Scan → Fetch → Save workflow."""

from scanner import scan_isbn
from api_client import fetch_book_data
from database import add_book


def run() -> None:
    isbn = scan_isbn()
    if not isbn:
        print("No ISBN scanned. Exiting.")
        return

    book = fetch_book_data(isbn)
    if not book:
        print("Could not fetch book data. Exiting.")
        return

    print(f"\nTitle:    {book.get('title', 'Unknown')}")
    print(f"Authors:  {', '.join(book.get('authors', []))}")
    print(f"Pages:    {book.get('pages')}")
    print(f"Cover:    {book.get('cover_url', '')}\n")

    add_book(book)


if __name__ == "__main__":
    run()
