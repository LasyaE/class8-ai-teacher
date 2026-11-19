from pathlib import Path
import json
import csv
import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "textbooks"
REPORT_DIR = ROOT / "data" / "extracted" / "reports"

EXPECTED = {
    "Math.pdf": "mathematics",
    "physics.pdf": "physical-science",
    "bio.pdf": "biological-science",
    "social.pdf": "social-studies",
    "English.pdf": "english",
    "telugu.pdf": "telugu",
    "Hindi.pdf": "hindi",
}

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    inventory, page_rows, summary = [], [], []
    for filename, subject in EXPECTED.items():
        path = PDF_DIR / filename
        if not path.exists():
            inventory.append({
                "subject": subject, "filename": filename, "found": False,
                "pdf_pages": "", "metadata_title": "", "metadata_author": "",
                "file_bytes": "", "status": "MISSING"
            })
            summary.append(f"MISSING: {filename}")
            continue

        doc = fitz.open(path)
        meta = doc.metadata or {}
        inventory.append({
            "subject": subject, "filename": filename, "found": True,
            "pdf_pages": len(doc), "metadata_title": meta.get("title", ""),
            "metadata_author": meta.get("author", ""),
            "file_bytes": path.stat().st_size, "status": "FOUND"
        })

        for idx, page in enumerate(doc):
            text = page.get_text("text") or ""
            images = page.get_images(full=True)
            words = len(text.split())
            rect = page.rect
            if words >= 30:
                classification = "digital_text_or_mixed"
            elif len(images) > 0 or words < 30:
                classification = "review_for_scan_or_image"
            else:
                classification = "review_needed"

            page_rows.append({
                "subject": subject,
                "filename": filename,
                "pdf_page_index_zero_based": idx,
                "pdf_page_number_one_based": idx + 1,
                "width_points": round(rect.width, 2),
                "height_points": round(rect.height, 2),
                "extracted_word_count": words,
                "image_object_count": len(images),
                "page_classification": classification
            })
        doc.close()
        summary.append(f"OK: {filename}")

    def write_csv(path, rows):
        if not rows:
            return
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    write_csv(REPORT_DIR / "textbook_inventory.csv", inventory)
    write_csv(REPORT_DIR / "page_inspection.csv", page_rows)
    (REPORT_DIR / "inspection_summary.json").write_text(
        json.dumps({"books": summary, "expected_books": len(EXPECTED),
                    "found_books": sum(1 for x in inventory if x["found"]),
                    "pages_inspected": len(page_rows)}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("\n".join(summary))
    print(f"\nBooks found: {sum(1 for x in inventory if x['found'])}/{len(EXPECTED)}")
    print(f"Pages inspected: {len(page_rows)}")
    print(f"Reports: {REPORT_DIR}")

if __name__ == "__main__":
    main()
