from pathlib import Path
import argparse
import json
import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "textbooks"
OUT_DIR = ROOT / "data" / "extracted" / "raw"

SUBJECT_FILES = {
    "mathematics": "Math.pdf",
    "physical-science": "physics.pdf",
    "biological-science": "bio.pdf",
    "social-studies": "social.pdf",
    "english": "English.pdf",
    "telugu": "telugu.pdf",
    "hindi": "Hindi.pdf",
}

def extract_one(subject, filename):
    pdf_path = PDF_DIR / filename
    if not pdf_path.exists():
        print(f"[MISSING] {pdf_path}")
        return None

    doc = fitz.open(pdf_path)
    book_out = OUT_DIR / subject / pdf_path.stem
    book_out.mkdir(parents=True, exist_ok=True)
    records = []

    for idx, page in enumerate(doc):
        text = page.get_text("text", sort=True) or ""
        page_no = idx + 1
        txt_path = book_out / f"page-{page_no:04d}.txt"
        txt_path.write_text(text, encoding="utf-8", errors="replace")
        records.append({
            "subject": subject,
            "source_pdf": filename,
            "pdf_page_index_zero_based": idx,
            "pdf_page_number_one_based": page_no,
            "text_characters": len(text),
            "text_words": len(text.split()),
            "text_file": str(txt_path.relative_to(ROOT)).replace("\\", "/"),
            "needs_visual_review": len(text.strip()) < 100
        })

    metadata = {
        "subject": subject,
        "source_pdf": filename,
        "pdf_page_count": len(doc),
        "pdf_metadata": doc.metadata or {},
        "pages": records
    }
    (book_out / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    doc.close()
    total_words = sum(x["text_words"] for x in records)
    low_text = sum(1 for x in records if x["needs_visual_review"])
    print(f"[OK] {filename}: {len(records)} pages, {total_words} words, {low_text} pages flagged for visual review")
    return records

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Extract all seven PDFs")
    parser.add_argument("--subjects", nargs="*", choices=SUBJECT_FILES.keys(),
                        help="Extract selected subject names")
    args = parser.parse_args()

    if args.all:
        selected = list(SUBJECT_FILES.keys())
    elif args.subjects:
        selected = args.subjects
    else:
        parser.error("Use --all or --subjects followed by one or more subject names.")

    for subject in selected:
        extract_one(subject, SUBJECT_FILES[subject])

if __name__ == "__main__":
    main()
