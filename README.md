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
- A working camera (built-in or USB webcam on desktop; device camera via Termux:API on Android)
- **Desktop**: `opencv-python` 4.5.1+ (optional – enables the live-camera window)
- **Mobile (Termux)**: `zxing-cpp` (imported as `zxingcpp`) and `Pillow` (installed automatically from `requirements.txt`); the [Termux:API](https://wiki.termux.com/wiki/Termux:API) app and `pkg install termux-api` for camera access

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/fahoel/BookCheck.git
cd BookCheck

# 2. Install dependencies with uv (recommended)
uv sync

# 3. Run with uv
uv run python main.py

# 4. Optional desktop dependency for live-camera window
uv add --optional desktop opencv-python
```

### pip (alternative)

```bash
# 1. (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# Desktop only – adds the live-camera window (not available on ARM/mobile):
pip install opencv-python
```

### Termux (Android) setup

```bash
# Inside Termux:
pkg install python termux-api
pip install -r requirements.txt
# Also install the "Termux:API" companion app from F-Droid / Google Play.
```

---

## Running the app

```bash
uv run python main.py
# or, if using pip/venv:
# python main.py
```

1. A camera window opens – point it at the ISBN barcode on the back of a book.
2. Once the barcode is detected the window closes automatically.
3. Book metadata (title, authors, pages, cover URL) is printed to the terminal.
4. The record is appended to `library.json` in the current directory.
5. Press **q** in the camera window at any time to quit without saving.

### Standalone helpers

```bash
# Test the API client directly (default ISBN used if none provided)
uv run python api_client.py [ISBN]

# List all books already saved
uv run python database.py

# Scan a barcode without saving
uv run python scanner.py
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

---

## Testing

### Automated smoke checks

```bash
uv run python -m unittest discover -s tests -q
```

These tests cover the core workflow (scan → fetch → save), duplicate handling, API/network failure handling, camera-unavailable behavior, and module-level CLI execution paths.

### Manual test checklist

- [ ] `python main.py` with a valid ISBN barcode:
  - [ ] metadata is shown (title, authors, pages, cover)
  - [ ] book is written to `library.json`
- [ ] scan same ISBN again:
  - [ ] duplicate is reported and no duplicate entry is added
- [ ] failure paths:
  - [ ] camera unavailable prints graceful error and exits
  - [ ] ISBN not found in Open Library prints graceful message
  - [ ] network issue prints request/network error path
- [ ] module-level commands:
  - [ ] `python scanner.py`
  - [ ] `python api_client.py <isbn>`
  - [ ] `python database.py`

### Test result template

Record for each run:

- OS:
- Python version:
- Camera type:
- Scenario result matrix (pass/fail):
- Known issues / follow-up issues:
