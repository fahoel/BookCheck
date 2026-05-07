"""scanner.py – Use the device camera to detect an ISBN barcode."""

import cv2


def scan_isbn() -> str | None:
    """Open the default camera, scan for a barcode, and return the ISBN string.

    Uses cv2.barcode.BarcodeDetector (OpenCV 4.5.1+) which handles 1-D
    EAN-13/UPC barcodes used on ISBN labels.

    Returns the decoded barcode text, or None if the user quits without scanning.
    """
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


if __name__ == "__main__":
    result = scan_isbn()
    if result:
        print(f"Scanned ISBN: {result}")
    else:
        print("No ISBN scanned.")
