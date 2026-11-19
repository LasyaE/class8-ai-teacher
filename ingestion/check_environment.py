import sys
import fitz
import pandas
from PIL import Image
print("Python:", sys.version)
print("PyMuPDF:", fitz.VersionBind)
print("pandas:", pandas.__version__)
print("Pillow:", Image.__version__)
try:
    import pytesseract
    print("pytesseract:", pytesseract.get_tesseract_version())
except Exception as exc:
    print("Tesseract not ready (optional until OCR is required):", exc)
