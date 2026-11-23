from pathlib import Path
import csv

input_path = Path("data/curriculum/chapter_list_processed.txt")
output_path = Path("data/curriculum/chapter_list_split.txt")
error_path = Path("data/curriculum/chapter_list_malformed.txt")

valid_rows = []
malformed_rows = []

with input_path.open("r", encoding="utf-8-sig", newline="") as source:
    for line_number, line in enumerate(source, start=1):
        original = line.rstrip("\r\n")
        parts = [part.strip() for part in original.split("\t")]
        if len(parts) < 2 or any(not part for part in parts):
            malformed_rows.append((line_number, original))
        else:
            valid_rows.append(parts)

with output_path.open("w", encoding="utf-8", newline="") as output:
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerows(valid_rows)

with error_path.open("w", encoding="utf-8") as errors:
    for line_number, original in malformed_rows:
        errors.write(f"{line_number}\t{original}\n")

print(f"Total lines: {len(valid_rows) + len(malformed_rows)}")
print(f"Valid lines: {len(valid_rows)}")
print(f"Malformed lines: {len(malformed_rows)}")
print(f"Structured output: {output_path}")
print(f"Malformed report: {error_path}")
