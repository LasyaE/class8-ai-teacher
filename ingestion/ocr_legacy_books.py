from pathlib import Path
import subprocess
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "extracted" / "raw"
OCR_SCRIPT = ROOT / "ingestion" / "ocr_pages.py"
OCR_DIR = ROOT / "data" / "extracted" / "ocr"

BOOKS = {"hindi": "hin", "telugu": "tel"}

def main():
    for subject, language in BOOKS.items():
        metadata_files = list((RAW_DIR / subject).rglob("metadata.json"))
        if len(metadata_files) != 1:
            raise RuntimeError(
                f"{subject}: expected one metadata file, found {len(metadata_files)}"
            )

        data = json.loads(metadata_files[0].read_text(encoding="utf-8"))
        pages = data if isinstance(data, list) else data.get("pages", [])
        page_numbers = sorted({
            int(p.get("pdf_page_number_one_based", p.get("page_number", 0)))
            for p in pages
            if int(p.get("pdf_page_number_one_based", p.get("page_number", 0))) > 0
        })

        folder = OCR_DIR / subject
        folder.mkdir(parents=True, exist_ok=True)

        missing = [
            page for page in page_numbers
            if not (
                (folder / f"page-{page:04d}-{language}.txt").exists()
                and (folder / f"page-{page:04d}-{language}.txt").stat().st_size > 0
            )
        ]

        print(f"\n{subject.upper()}: {len(page_numbers)} total pages")
        print(f"Existing non-empty OCR files: {len(page_numbers) - len(missing)}")
        print(f"Pages remaining: {len(missing)}")

        if not missing:
            continue

        command = [
            sys.executable, str(OCR_SCRIPT),
            "--subject", subject,
            "--pages", *map(str, missing),
            "--lang", language,
            "--dpi", "300",
        ]

        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            raise SystemExit(result.returncode)

        print(f"{subject} OCR batch completed.")

    print("\nLEGACY LANGUAGE OCR JOBS FINISHED")

if __name__ == "__main__":
    main()
