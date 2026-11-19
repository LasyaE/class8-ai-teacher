
from pathlib import Path
from PIL import Image
import pytesseract

ROOT = Path(__file__).resolve().parents[1]

IMAGE_PATH = (
    ROOT
    / "data"
    / "extracted"
    / "visual_pages"
    / "english"
    / "English"
    / "page-0011.png"
   )


OUTPUT_DIR = ROOT / "data" / "extracted" / "layout_tests"

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

image = Image.open(IMAGE_PATH).convert("RGB")
width, height = image.size

# Crop the right-side vertical title strip.
crop = image.crop((
    int(width * 0.78),
    int(height * 0.04),
    width,
    int(height * 0.96),
))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Save original crop and both possible text orientations.
crop.save(OUTPUT_DIR / "english-0059-vertical-crop.png")

rotated_clockwise = crop.rotate(-90, expand=True)
rotated_counterclockwise = crop.rotate(90, expand=True)

rotated_clockwise.save(
    OUTPUT_DIR / "english-0059-heading-clockwise.png"
)

rotated_counterclockwise.save(
    OUTPUT_DIR / "english-0059-heading-counterclockwise.png"
)

for name, image_to_read in [
    ("CLOCKWISE", rotated_clockwise),
    ("COUNTERCLOCKWISE", rotated_counterclockwise),
]:
    print(f"\n===== {name} =====")

    text = pytesseract.image_to_string(
        image_to_read,
        lang="eng",
        config="--psm 6",
    )

    print(text)

print("\nImages saved in:", OUTPUT_DIR)
