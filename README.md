# BookCheck

A small Python utility that scans a book's ISBN barcode with your device camera, looks up the metadata from the [Open Library API](https://openlibrary.org/dev/docs/api), and saves the result to a local `library.json` file. Duplicate ISBNs are silently ignored.

---

## How it works

```
Camera → scanner.py  →  isbn string
                              │
                     api_client.py  →  Open Library API
                              │
                        main.py (prints metadata)
                              │
                       database.py  →  library.json
```

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point – ties the three steps together |
| `scanner.py` | Opens the default camera, detects EAN-13/UPC barcodes with OpenCV |
| `api_client.py` | Fetches title, authors, cover URL, and page count from Open Library |
| `database.py` | Reads/writes `library.json`; prevents duplicate ISBNs |
| `sync.sh` | Termux helper – commits and pushes `library.json` to the remote |

---

## Requirements

- Python 3.10+
- A working camera (built-in or USB webcam)
- OpenCV 4.5.1+ (for the built-in barcode detector)

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/fahoel/BookCheck.git
cd BookCheck

# 2. (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the app

```bash
python main.py
```

1. A camera window opens – point it at the ISBN barcode on the back of a book.
2. Once the barcode is detected the window closes automatically.
3. Book metadata (title, authors, pages, cover URL) is printed to the terminal.
4. The record is appended to `library.json` in the current directory.
5. Press **q** in the camera window at any time to quit without saving.

### Standalone helpers

```bash
# Test the API client directly (default ISBN used if none provided)
python api_client.py [ISBN]

# List all books already saved
python database.py

# Scan a barcode without saving
python scanner.py
```

---

## Syncing to GitHub (Termux / mobile)

`sync.sh` is a convenience script for pushing changes from a Termux environment:

```bash
bash sync.sh "Add new book"   # commit message is optional
```

It runs `git add . && git commit -m "..." && git push`.

---

## library.json format

Each entry looks like this:

```json
{
  "isbn": "9780140328721",
  "title": "Fantastic Mr. Fox",
  "authors": ["Roald Dahl"],
  "cover_url": "https://covers.openlibrary.org/b/id/...-L.jpg",
  "pages": 96
}
```