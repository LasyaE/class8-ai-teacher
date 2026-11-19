
from pathlib import Path
import json
import re

import pymupdf


# =========================================================
# CONFIGURATION
# =========================================================

ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = ROOT / "data" / "textbooks" / "English.pdf"
PAGE_NUMBER = 133

OUTPUT_DIR = ROOT / "data" / "extracted" / "layout_tests"
IMAGE_DIR = OUTPUT_DIR / "images"

WATERMARK_RE = re.compile(r"SCERT\s+TELANGANA", re.IGNORECASE)
CAPTION_RE = re.compile(r"^\s*Fig[\s.-]*\d+", re.IGNORECASE)


# =========================================================
# GENERAL HELPERS
# =========================================================

def clean(text):
    return " ".join(text.split()).strip()


def rect_values(rect):
    return [round(float(value), 2) for value in rect]


def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def output_basename():
    return f"{PDF_PATH.stem.lower()}-page-{PAGE_NUMBER:04d}"


def rectangle_area(rect):
    return max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])


def intersection_area(a, b):
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])

    if x1 <= x0 or y1 <= y0:
        return 0.0

    return (x1 - x0) * (y1 - y0)


def overlap_ratio(a, b):
    denominator = min(rectangle_area(a), rectangle_area(b))

    if denominator <= 0:
        return 0.0

    return intersection_area(a, b) / denominator


def rectangle_center(rect):
    return (
        (rect[0] + rect[2]) / 2,
        (rect[1] + rect[3]) / 2
    )


def point_inside_rect(x, y, rect, padding=0):
    return (
        rect[0] - padding <= x <= rect[2] + padding
        and rect[1] - padding <= y <= rect[3] + padding
    )


# =========================================================
# TEXT EXTRACTION
# =========================================================

def extract_blocks(page):
    data = page.get_text("dict", sort=False)
    results = []

    for index, block in enumerate(data["blocks"]):
        if block.get("type") != 0:
            continue

        text_parts = []
        fonts = []
        sizes = []

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")

                if text:
                    text_parts.append(text)
                    fonts.append(span.get("font", "unknown"))
                    sizes.append(round(float(span.get("size", 0)), 2))

        text = clean(" ".join(text_parts))

        if not text:
            continue

        bbox = rect_values(block["bbox"])
        x0, y0, x1, y1 = bbox

        if WATERMARK_RE.search(text):
            category = "watermark"
        elif CAPTION_RE.match(text):
            category = "caption"
        elif y0 > page.rect.height * 0.90:
            category = "footer"
        elif y1 < page.rect.height * 0.12:
            category = "header"
        else:
            category = "body"

        results.append({
            "id": index,
            "text": text,
            "bbox": bbox,
            "category": category,
            "fonts": sorted(set(fonts)),
            "font_sizes": sorted(set(sizes))
        })

    return results


# =========================================================
# WORD EXTRACTION
# =========================================================

def extract_words(page):
    results = []

    for word in page.get_text("words", sort=False):
        x0, y0, x1, y1, text = word[:5]
        text = clean(text)

        if not text:
            continue

        if text.upper() in ("SCERT", "TELANGANA"):
            continue

        results.append({
            "text": text,
            "bbox": rect_values((x0, y0, x1, y1))
        })

    return results


# =========================================================
# EXCLUDED TEXT REGIONS
# =========================================================

def get_excluded_regions(blocks):
    excluded = []

    # Only exclude header and footer regions.
    # Watermark bounding boxes are deliberately NOT excluded:
    # they can overlap real diagram shapes and page content.

    for block in blocks:
        if block["category"] in ("footer", "header"):
            excluded.append({
                "category": block["category"],
                "bbox": block["bbox"],
                "text": block["text"]
            })

    return excluded


def word_is_excluded(word, excluded_regions):
    x0, y0, x1, y1 = word["bbox"]
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2

    return any(
        point_inside_rect(center_x, center_y, region["bbox"])
        for region in excluded_regions
    )


# =========================================================
# DIAGRAM SHAPE DETECTION
# =========================================================

def detect_diagram_shapes(page, excluded_regions):
    candidates = []

    for drawing in page.get_drawings():
        rect = rect_values(drawing["rect"])

        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        # Ignore tiny decorative marks and thin connector lines.
        if width < 35 or height < 10:
            continue

        # Filled shapes are candidate diagram nodes.
        if drawing.get("fill") is None:
            continue

        # Only exclude shapes that substantially overlap
        # actual header/footer areas.
        if any(
            overlap_ratio(rect, region["bbox"]) >= 0.50
            for region in excluded_regions
        ):
            continue

        candidates.append({
            "bbox": rect,
            "drawing_type": drawing.get("type"),
            "fill": drawing.get("fill")
        })

    # Merge duplicate/overlapping rectangles.
    groups = []

    for shape in candidates:
        matching_group = None

        for group in groups:
            if any(
                overlap_ratio(shape["bbox"], item["bbox"]) >= 0.75
                for item in group
            ):
                matching_group = group
                break

        if matching_group is None:
            groups.append([shape])
        else:
            matching_group.append(shape)

    merged_shapes = []

    for group in groups:
        bbox = [
            min(item["bbox"][0] for item in group),
            min(item["bbox"][1] for item in group),
            max(item["bbox"][2] for item in group),
            max(item["bbox"][3] for item in group)
        ]

        merged_shapes.append({
            "bbox": rect_values(bbox),
            "source_drawing_count": len(group)
        })

    return merged_shapes


# =========================================================
# DIAGRAM LABEL ASSOCIATION
# =========================================================

def associate_diagram_labels(shapes, words, excluded_regions):
    nodes = []

    for index, shape in enumerate(shapes, 1):
        shape_bbox = shape["bbox"]
        label_words = []

        for word in words:
            if word_is_excluded(word, excluded_regions):
                continue

            wx0, wy0, wx1, wy1 = word["bbox"]
            center_x = (wx0 + wx1) / 2
            center_y = (wy0 + wy1) / 2

            if point_inside_rect(
                center_x,
                center_y,
                shape_bbox,
                padding=3
            ):
                label_words.append(word)

        label_words.sort(
            key=lambda word: (
                word["bbox"][1],
                word["bbox"][0]
            )
        )

        label = clean(
            " ".join(word["text"] for word in label_words)
        )

        nodes.append({
            "node_id": index,
            "bbox": shape_bbox,
            "label": label,
            "source_drawing_count": shape["source_drawing_count"]
        })

    return nodes


# =========================================================
# DIAGRAM VISUAL LEVELS
# =========================================================

def build_diagram_hierarchy(nodes):
    labelled = [
        node for node in nodes
        if node["label"]
    ]

    if not labelled:
        return {
            "method": "coordinate_based",
            "levels": [],
            "nodes": [],
            "relationships": [],
            "note": "No labelled diagram nodes detected."
        }

    ordered = sorted(
        labelled,
        key=lambda node: (
            rectangle_center(node["bbox"])[1],
            node["bbox"][0]
        )
    )

    levels = []

    for node in ordered:
        center_y = rectangle_center(node["bbox"])[1]
        matching_level = None

        for level in levels:
            if abs(center_y - level["center_y"]) <= 25:
                matching_level = level
                break

        if matching_level is None:
            levels.append({
                "center_y": center_y,
                "nodes": [node]
            })
        else:
            matching_level["nodes"].append(node)

    for level in levels:
        level["nodes"].sort(
            key=lambda node: node["bbox"][0]
        )

    return {
        "method": "coordinate_based",
        "levels": [
            {
                "level": index,
                "labels": [
                    node["label"]
                    for node in level["nodes"]
                ]
            }
            for index, level in enumerate(levels, 1)
        ],
        "nodes": ordered,
        "relationships": [],
        "note": (
            "Levels are inferred from vertical coordinates. "
            "Parent-child relationships have not been validated "
            "using connector lines."
        )
    }


# =========================================================
# IMAGE EXTRACTION
# =========================================================

def extract_images(page, document):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for index, info in enumerate(page.get_image_info(xrefs=True), 1):
        xref = info.get("xref")
        saved_file = None
        extraction_error = None

        if xref:
            try:
                extracted = document.extract_image(xref)

                filename = (
                    f"{output_basename()}-image-{index:02d}."
                    f"{extracted['ext']}"
                )

                path = IMAGE_DIR / filename
                path.write_bytes(extracted["image"])

                saved_file = str(path.relative_to(ROOT))

            except Exception as error:
                extraction_error = str(error)

        results.append({
            "image_id": index,
            "xref": xref,
            "bbox": rect_values(info["bbox"]),
            "width": info.get("width"),
            "height": info.get("height"),
            "saved_file": saved_file,
            "extraction_error": extraction_error
        })

    return results


# =========================================================
# DRAWING EXTRACTION
# =========================================================

def extract_drawings(page):
    results = []

    for index, drawing in enumerate(page.get_drawings(), 1):
        results.append({
            "drawing_id": index,
            "type": drawing.get("type"),
            "bbox": rect_values(drawing["rect"]),
            "fill": drawing.get("fill"),
            "stroke": drawing.get("color"),
            "item_count": len(drawing.get("items", []))
        })

    return results


# =========================================================
# READING ORDER
# =========================================================

def classify_reading_order(blocks):
    excluded = ("watermark", "footer", "header")

    content = [
        block for block in blocks
        if block["category"] not in excluded
    ]

    return sorted(
        content,
        key=lambda block: (
            block["bbox"][1],
            block["bbox"][0]
        )
    )


# =========================================================
# MAIN PROCESSOR
# =========================================================

def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"PDF not found: {PDF_PATH}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    document = pymupdf.open(PDF_PATH)

    try:
        if not 1 <= PAGE_NUMBER <= len(document):
            raise ValueError(
                f"Invalid PDF page number: {PAGE_NUMBER}"
            )

        page = document[PAGE_NUMBER - 1]

        print("\n====================================")
        print("DIAGRAM-AWARE TEXTBOOK EXTRACTION")
        print("====================================")

        print(f"PDF: {PDF_PATH.name}")
        print(f"Page: {PAGE_NUMBER}")
        print(f"Page size: {page.rect}")

        # 1. Text extraction.
        blocks = extract_blocks(page)
        words = extract_words(page)

        # 2. Exclude only header/footer regions.
        excluded_regions = get_excluded_regions(blocks)

        # 3. Detect diagram shapes.
        shapes = detect_diagram_shapes(
            page,
            excluded_regions
        )

        # 4. Associate diagram labels.
        diagram_nodes = associate_diagram_labels(
            shapes,
            words,
            excluded_regions
        )

        # 5. Group visual levels.
        hierarchy = build_diagram_hierarchy(
            diagram_nodes
        )

        # 6. Extract images and drawings.
        images = extract_images(page, document)
        drawings = extract_drawings(page)

        # 7. Identify watermark/footer metadata.
        watermarks = [
            block for block in blocks
            if block["category"] == "watermark"
        ]

        footers = [
            block for block in blocks
            if block["category"] == "footer"
        ]

        # 8. Reading order.
        reading_order = classify_reading_order(blocks)

        # 9. Render original page.
        render_path = (
            OUTPUT_DIR / f"{output_basename()}.png"
        )

        page.get_pixmap(
            matrix=pymupdf.Matrix(1.5, 1.5),
            alpha=False
        ).save(render_path)

        # 10. Build structured output.
        result = {
            "source": {
                "filename": PDF_PATH.name,
                "pdf_page": PAGE_NUMBER,
                "page_width": round(page.rect.width, 2),
                "page_height": round(page.rect.height, 2)
            },

            "statistics": {
                "text_blocks": len(blocks),
                "words": len(words),
                "images": len(images),
                "drawings": len(drawings),
                "diagram_shapes": len(shapes),
                "diagram_nodes": len(diagram_nodes),
                "labelled_diagram_nodes": sum(
                    bool(node["label"])
                    for node in diagram_nodes
                ),
                "watermarks": len(watermarks),
                "footers": len(footers)
            },

            "text_blocks": blocks,
            "reading_order": reading_order,
            "excluded_regions": excluded_regions,
            "diagram_shapes": shapes,
            "diagram_nodes": diagram_nodes,
            "diagram_hierarchy": hierarchy,
            "images": images,
            "drawings": drawings,
            "watermarks": watermarks,
            "footers": footers,

            "visual_reference": str(
                render_path.relative_to(ROOT)
            )
        }

        # 11. Save JSON.
        output_json = (
            OUTPUT_DIR / f"{output_basename()}.json"
        )

        save_json(result, output_json)

        # 12. Display results.
        print("\n========== SUMMARY ==========")

        for key, value in result["statistics"].items():
            print(f"{key}: {value}")

        print("\n========== DIAGRAM NODES ==========")

        for node in diagram_nodes:
            label = node["label"] or "[unlabelled shape]"
            print(f'{node["node_id"]}: {label}')

        print("\n========== DIAGRAM LEVELS ==========")

        for level in hierarchy["levels"]:
            print(
                f'Level {level["level"]}: '
                f'{", ".join(level["labels"])}'
            )

        print("\n========== OUTPUT FILES ==========")
        print("JSON:", output_json)
        print("Page image:", render_path)
        print("Images:", IMAGE_DIR)

        print("\nExtraction completed successfully.")

    finally:
        document.close()


if __name__ == "__main__":
    main()
