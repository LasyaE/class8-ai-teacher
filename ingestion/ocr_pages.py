from pathlib import Path
import argparse
import fitz
import pytesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "extracted" / "ocr"
SUBJECT_FILES = {
    "mathematics": "Math.pdf",
    "physical-science": "physics.pdf",
    "biological-science": "bio.pdf",
    "social-studies": "social.pdf",
    "english": "English.pdf",
    "telugu": "telugu.pdf",
    "hindi": "Hindi.pdf",
}

def main():
    parser = argparse.ArgumentParser(description="OCR selected 1-based PDF pages using local Tesseract.")
    parser.add_argument("--subject", required=True, choices=SUBJECT_FILES.keys())
    parser.add_argument("--pages", nargs="+", type=int, required=True, help="1-based PDF page numbers")
    parser.add_argument("--lang", default="eng", help="Tesseract language code, e.g. eng, tel, hin, eng+tel")
    parser.add_argument("--dpi", type=int, default=250)
    args = parser.parse_args()

    pdf_path = PDF_DIR / SUBJECT_FILES[args.subject]
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    target = OUT_DIR / args.subject
    target.mkdir(parents=True, exist_ok=True)

    for page_no in args.pages:
        if page_no < 1 or page_no > len(doc):
            print(f"[SKIP] Page {page_no} outside 1..{len(doc)}")
            continue
        page = doc[page_no - 1]
        pix = page.get_pixmap(dpi=args.dpi, alpha=False)
        image_path = target / f"page-{page_no:04d}.png"
        pix.save(image_path)
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=args.lang)
        text_path = target / f"page-{page_no:04d}-{args.lang}.txt"
        text_path.write_text(text, encoding="utf-8", errors="replace")
        print(f"[OK] OCR page {page_no} -> {text_path}")

    doc.close()

if __name__ == "__main__":
    main()
