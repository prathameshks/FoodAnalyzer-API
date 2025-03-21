import cv2
import pytesseract

def extract_text_from_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    text = pytesseract.image_to_string(gray)
    return text

def detect_barcode_from_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(gray)
    if bbox is not None:
        return data
    return None
