# data_validation.py

import json
import os
import re
from datetime import datetime

# Quality gate rules
QUALITY_GATES = {
    "utf8_valid": True,
    "no_duplicates": True,
    "source_evidence": True,
    "math_correct": True,
    "language_match": True
}

def validate_dataset(dataset_path):
    """Validate dataset against quality gates"""
    # Check if dataset exists
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    # Read and validate dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # UTF-8 validation
    if not QUALITY_GATES["utf8_valid"]:
        raise ValueError("Invalid UTF-8 encoding in dataset")

    # Duplicate detection
    seen = set()
    for item in dataset:
        item_hash = hash(json.dumps(item, sort_keys=True))
        if item_hash in seen:
            raise ValueError("Duplicate example detected")
        seen.add(item_hash)

    # Source evidence validation
    for item in dataset:
        if not QUALITY_GATES["source_evidence"]:
            continue
        if "source" not in item or not os.path.exists(item["source"]):
            raise ValueError(f"Missing source evidence: {item}")

    # Mathematical correctness validation
    if QUALITY_GATES["math_correct"]:
        for item in dataset:
            if "math" in item:
                try:
                    # Basic arithmetic validation
                    if isinstance(item["math"], dict) and "question" in item["math"]:
                        answer = item["math"].get("answer")
                        if answer:
                            # Simple arithmetic check
                            if "+" in answer:
                                a, b = map(int, answer.split("+")[0].split())
                                expected = a + b
                                actual = int(answer.split("=")[1].strip())
                                if actual != expected:
                                    raise ValueError(f'Math error in question: {item["math"]["question"]}')
                            # Fraction simplification check
                            if "frac" in answer:
                                numerator, denominator = map(int, answer.split("/")[0].split())
                                gcd = math.gcd(numerator, denominator)
                                simplified = f"{numerator//gcd}/{denominator//gcd}"
                                if simplified != answer:
                                    raise ValueError(f'Fraction simplification error: {item["math"]["question"]}')
                except Exception as e:
                    raise ValueError(f"Math validation error: {str(e)}")

    # Language validation
    if QUALITY_GATES["language_match"]:
        for item in dataset:
            if "language" in item:
                if item["language"] not in ["English", "Telugu", "Hindi"]:
                    raise ValueError(f'Invalid language: {item["language"]}')

    # Generate validation report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dataset_hash": hash(dataset_path),
        "valid": True,
        "issues": []
    }

    # Save validation report
    report_path = f"{os.path.dirname(dataset_path)}/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report