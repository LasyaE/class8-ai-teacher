from pathlib import Path
import argparse
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "extracted" / "raw"
VISUAL_DIR = ROOT / "data" / "extracted" / "visual_pages"

SUBJECT_FILES = {
    "mathematics": "Math.pdf",
    "physical-science": "physics.pdf",
    "biological-science": "bio.pdf",
    "social-studies": "social.pdf",
    "english": "English.pdf",
    "telugu": "telugu.pdf",
    "hindi": "Hindi.pdf",
}

MIN_TEXT_CHARS = 100
MIN_TEXT_WORDS = 15
IMAGE_COVERAGE_THRESHOLD = 0.75
RENDER_SCALE = 2.0


def relative_path(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")


def clean_text(text):
    return (text or "").replace("\x00", "").strip()


def page_image_coverage(page):
    """Estimate the proportion of the page covered by embedded images."""
    page_area = max(page.rect.width * page.rect.height, 1)
    image_rects = []

    for info in page.get_image_info(xrefs=True):
        bbox = info.get("bbox")
        if not bbox:
            continue
        rect = pymupdf.Rect(bbox) & page.rect
        if not rect.is_empty:
            image_rects.append(rect)

    # Use the union area to avoid double-counting overlapping images.
    if not image_rects:
        return 0.0

    union = []
    for rect in image_rects:
        merged = rect
        remaining = []
        for existing in union:
            if merged.intersects(existing):
                merged |= existing
            else:
                remaining.append(existing)
        remaining.append(merged)
        union = remaining

    covered_area = sum(rect.get_area() for rect in union)
    return min(covered_area / page_area, 1.0)


def extract_page_images(page, subject, book_name, page_number):
    """Save embedded images and return their source metadata."""
    image_dir = VISUAL_DIR / subject / book_name / f"page-{page_number:04d}"
    image_records = []

    for image_number, info in enumerate(
        page.get_image_info(xrefs=True), start=1
    ):
        xref = info.get("xref")
        record = {
            "image_number": image_number,
            "xref": xref,
            "bbox": [round(float(v), 2) for v in info.get("bbox", [])],
            "width": info.get("width"),
            "height": info.get("height"),
            "saved_file": None,
            "error": None,
        }

        if xref:
            try:
                extracted = page.parent.extract_image(xref)
                extension = extracted.get("ext", "bin")
                image_dir.mkdir(parents=True, exist_ok=True)
                image_path = image_dir / (
                    f"image-{image_number:02d}.{extension}"
                )
                image_path.write_bytes(extracted["image"])
                record["saved_file"] = relative_path(image_path)
            except Exception as exc:
                record["error"] = str(exc)

        image_records.append(record)

    return image_records


def save_visual_page(page, subject, book_name, page_number):
    """Render the complete page when it needs visual review."""
    page_dir = VISUAL_DIR / subject / book_name
    page_dir.mkdir(parents=True, exist_ok=True)
    image_path = page_dir / f"page-{page_number:04d}.png"

    page.get_pixmap(
        matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
        alpha=False,
    ).save(image_path)

    return relative_path(image_path)


def extract_one(subject, filename):
    pdf_path = PDF_DIR / filename
    if not pdf_path.exists():
        print(f"[MISSING] {pdf_path}")
        return None

    book_out = OUT_DIR / subject / pdf_path.stem
    book_out.mkdir(parents=True, exist_ok=True)

    records = []

    with pymupdf.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            page_number = index + 1

            # Digital text remains the primary source. OCR is not mixed into it.
            text = clean_text(page.get_text("text", sort=True))
            word_count = len(text.split())
            image_coverage = page_image_coverage(page)
            images = extract_page_images(
                page, subject, pdf_path.stem, page_number
            )

            low_text = (
                len(text) < MIN_TEXT_CHARS
                or word_count < MIN_TEXT_WORDS
            )
            image_based = image_coverage >= IMAGE_COVERAGE_THRESHOLD
            needs_visual_review = low_text or image_based

            text_path = book_out / f"page-{page_number:04d}.txt"
            text_path.write_text(text, encoding="utf-8")

            visual_reference = None
            if needs_visual_review:
                visual_reference = save_visual_page(
                    page, subject, pdf_path.stem, page_number
                )

            record = {
                "subject": subject,
                "source_pdf": filename,
                "pdf_page_index_zero_based": index,
                "pdf_page_number_one_based": page_number,
                "text_characters": len(text),
                "text_words": word_count,
                "text_file": relative_path(text_path),
                "embedded_image_count": len(images),
                "image_coverage_estimate": round(image_coverage, 4),
                "page_type_hint": (
                    "image_dominant"
                    if image_based
                    else "low_text"
                    if low_text
                    else "digital_text_or_mixed"
                ),
                "needs_visual_review": needs_visual_review,
                "visual_reference": visual_reference,
                "embedded_images": images,
                "ocr_status": "not_run",
                "review_status": "pending" if needs_visual_review else "not_required_by_initial_heuristic",
            }
            records.append(record)

    metadata = {
        "subject": subject,
        "source_pdf": filename,
        "pdf_page_count": len(records),
        "extraction_method": "PyMuPDF digital text extraction",
        "ocr_policy": (
            "OCR is not automatically merged into digital text. "
            "Image-based and low-text pages are preserved for separate review."
        ),
        "pages": records,
    }

    metadata_path = book_out / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_words = sum(item["text_words"] for item in records)
    flagged = sum(item["needs_visual_review"] for item in records)
    image_dominant = sum(
        item["page_type_hint"] == "image_dominant" for item in records
    )

    print(
        f"[OK] {filename}: {len(records)} pages, "
        f"{total_words} words, {flagged} pages for visual review, "
        f"{image_dominant} image-dominant pages"
    )
    print(f"     Metadata: {relative_path(metadata_path)}")

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Extract digital text and preserve visual textbook pages."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extract all seven PDFs",
    )
    parser.add_argument(
        "--subjects",
        nargs="*",
        choices=SUBJECT_FILES.keys(),
        help="Extract selected subjects",
    )
    args = parser.parse_args()

    if args.all:
        selected = list(SUBJECT_FILES.keys())
    elif args.subjects:
        selected = args.subjects
    else:
        parser.error(
            "Use --all or --subjects followed by one or more subject names."
        )

    for subject in selected:
        extract_one(subject, SUBJECT_FILES[subject])


if __name__ == "__main__":
    main()
