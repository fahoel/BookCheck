"""scanner.py – Use the device camera to detect an ISBN barcode.

Two backends are supported:
* **cv2** (desktop) – requires ``opencv-python``.  Gives a live camera window
  and uses OpenCV's built-in barcode detector.
* **Termux** (Android / mobile) – used automatically when ``opencv-python`` is
  not installed.  Captures a still photo with ``termux-camera-photo`` and
  decodes it with ``zxingcpp`` + ``Pillow``.
"""

import subprocess
import tempfile
from pathlib import Path

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    import zxingcpp
    from PIL import Image
    _ZXING_AVAILABLE = True
except ImportError:  # pragma: no cover – missing on desktop without optional deps
    zxingcpp = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    _ZXING_AVAILABLE = False


# ---------------------------------------------------------------------------
# cv2 backend (desktop)
# ---------------------------------------------------------------------------

def _scan_isbn_cv2() -> str | None:
    """Live-camera scan using OpenCV (requires opencv-python)."""
    detector = cv2.barcode.BarcodeDetector()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None

    print("Point camera at ISBN barcode. Press 'q' to quit.")

    isbn = None
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        ok, decoded, _, _ = detector.detectAndDecodeMulti(frame)
        if ok and decoded:
            isbn = decoded[0]
            print(f"ISBN detected: {isbn}")
            break

        cv2.imshow("ISBN Scanner – press q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return isbn


# ---------------------------------------------------------------------------
# Termux backend (Android / mobile)
# ---------------------------------------------------------------------------

def _scan_isbn_termux() -> str | None:
    """Still-photo scan using termux-camera-photo + zxingcpp (mobile)."""
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        photo_path = Path(tmp.name)
        tmp.close()
    except OSError as exc:
        print(f"Error: Could not create temporary file: {exc}")
        return None

    try:
        print("Taking photo with front camera… (Ctrl-C to cancel)")
        subprocess.run(
            ["termux-camera-photo", "-c", "0", str(photo_path)],
            check=True,
            capture_output=True,
        )

        with Image.open(photo_path) as img:
            results = zxingcpp.read_barcodes(img)
        if results:
            isbn = results[0].text
            print(f"ISBN detected: {isbn}")
            return isbn

        print("No barcode found in photo.")
        return None
    except subprocess.CalledProcessError as exc:
        print(f"Error: Camera capture failed: {exc}")
        return None
    except FileNotFoundError:
        print("Error: termux-camera-photo not found. Install the Termux:API app and package.")
        return None
    finally:
        photo_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_isbn() -> str | None:
    """Scan an ISBN barcode using whichever backend is available.

    Uses the cv2 live-camera window on desktop; falls back to
    termux-camera-photo on mobile where opencv-python is unavailable.
    """
    if _CV2_AVAILABLE:
        return _scan_isbn_cv2()
    return _scan_isbn_termux()


if __name__ == "__main__":
    result = scan_isbn()
    if result:
        print(f"Scanned ISBN: {result}")
    else:
        print("No ISBN scanned.")
