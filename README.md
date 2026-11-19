# Class 8 Telangana Textbook Ingestion Starter

This starter kit begins Stage 1: inventory, inspect, and extract the seven original textbook PDFs.

## Important
- The PDFs uploaded to ChatGPT are not automatically copied to your laptop or Google Drive.
- Download the seven original attachments from the conversation onto the computer where you will run this project.
- Put them in `data/textbooks/` using these exact filenames:
  - `Math.pdf`
  - `physics.pdf`
  - `bio.pdf`
  - `social.pdf`
  - `English.pdf`
  - `telugu.pdf`
  - `Hindi.pdf`
- Do not edit or overwrite the originals.
- Keep PDFs, extracted textbook content, and student data out of a public GitHub repository unless redistribution rights have been confirmed.

## 1. Windows setup (PowerShell)

Open this folder in VS Code, then open Terminal > New Terminal:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If activation is blocked, run this once in PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 2. Place the PDFs

Copy the seven files into `data/textbooks/`. Confirm the filenames exactly match the list above.

## 3. Inspect all PDFs first

```powershell
python ingestion/inspect_pdfs.py
```

Outputs:
- `data/extracted/reports/textbook_inventory.csv`
- `data/extracted/reports/page_inspection.csv`
- `data/extracted/reports/inspection_summary.json`

This stage records page count, metadata, text availability, page dimensions, image counts and likely scan/image-only pages. It does not change source PDFs.

## 4. Extract digital text (pilot first)

Run the four-book pilot:

```powershell
python ingestion/extract_text.py --subjects mathematics physical-science telugu social-studies
```

Review:
- `data/extracted/raw/<subject>/<pdf-stem>/page-0001.txt`
- `data/extracted/reports/extraction_summary.csv`

Then run all seven:

```powershell
python ingestion/extract_text.py --all
```

The extractor saves one UTF-8 text file per PDF page and a JSON metadata file. It preserves both zero-based PDF page index and printed page label where available only as extracted text; printed page labels are not assumed to equal PDF page numbers.

## 5. OCR is a separate step

Do not OCR every page blindly. First inspect `page_inspection.csv`. OCR is for pages where digital text is absent or clearly inadequate.

For a Windows Tesseract setup:
1. Install Tesseract OCR for Windows from its official distribution.
2. During installation, include English (`eng`), Telugu (`tel`) and Hindi (`hin`) trained data if available.
3. Confirm `tesseract --version` works in a new terminal.
4. Confirm language packs using `tesseract --list-langs`.

The optional OCR script expects Tesseract to be installed and accessible on PATH:

```powershell
python ingestion/ocr_pages.py --subject telugu --pages 12 13 14 --lang tel
```

Page numbers passed to this script are 1-based PDF page numbers. OCR output goes to `data/extracted/ocr/`; it never overwrites digital text extraction.

For Telugu and Hindi, manually compare OCR output with page images. Some PDFs may use embedded/legacy font encodings that produce garbled extracted text; OCR or font-aware processing may be necessary. OCR output is not automatically trusted.

## 6. Stage 1 quality gates

Before declaring Stage 1 complete:
- all seven PDFs are inventoried and page counts reconciled;
- every page is accounted for as digital-text, scan/image, mixed, or review-needed;
- representative pages from every book are visually checked;
- Telugu and Hindi script quality is reviewed carefully;
- Mathematics equations and diagrams, Science diagrams/tables, and Social Studies maps are accounted for;
- chapter/section structure is checked against each book's contents pages;
- unresolved OCR/extraction issues are recorded.

## 7. Expected project layout

```text
class8-ai-teacher/
├── data/
│   ├── textbooks/                 # private originals; do not publish
│   └── extracted/
│       ├── raw/                   # page-wise UTF-8 text
│       ├── ocr/                   # OCR outputs, separately stored
│       └── reports/
├── ingestion/
├── requirements.txt
├── .gitignore
└── README.md
```

## 8. Next step after the pilot

Do not start chunking, embeddings, or model training yet. First review the pilot extraction and page-inspection reports. Fix extraction/OCR issues, then run all seven books and build the chapter catalogue.
