
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "data" / "extracted" / "visual_pages"
       / "english" / "English" / "page-0011.png"
)

OUTPUT_DIR = ROOT / "data" / "extracted" / "layout_tests"

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

image = Image.open(SOURCE).convert("RGB")

# Isolate the large numeral, excluding the vertical word "Unit".
number = image.crop((175, 90, 490, 550))

# Enlarge the numeral for recognition.
number = number.resize(
    (number.width * 3, number.height * 3),
    Image.Resampling.LANCZOS
)

gray = ImageOps.grayscale(number)
gray = ImageEnhance.Contrast(gray).enhance(1.8)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

number.save(OUTPUT_DIR / "english-0011-number-only.png")
gray.save(OUTPUT_DIR / "english-0011-number-gray.png")
print("===== UNIT NUMBER OCR =====")

for psm in (8, 10, 13):
    config = (
        f"--oem 1 --psm {psm} "
        "-c tessedit_char_whitelist=0123456789"
    )

    text = pytesseract.image_to_string(
        gray,
        lang="eng",
        config=config
    )

    print(f"\nPSM {psm}: {text.strip()!r}")

print("\nSaved images:", OUTPUT_DIR)
