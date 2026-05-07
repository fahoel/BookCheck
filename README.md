# BookCheck

## Local test pass

### Setup

1. Use Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

### Automated smoke checks

Run:

```bash
python -m unittest discover -s tests -q
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
