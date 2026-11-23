
import json
from pathlib import Path

source = Path("data/training/mathematics/validation.jsonl")
backup = source.with_suffix(".jsonl.backup")

if not backup.exists():
    backup.write_bytes(source.read_bytes())

raw = backup.read_text(encoding="utf-8")

fixed = []
inside_string = False
escaped = False

for char in raw:
    if inside_string:
        if escaped:
            fixed.append(char)
            escaped = False
        elif char == "\\":
            fixed.append(char)
            escaped = True
        elif char == '"':
            fixed.append(char)
            inside_string = False
        elif char == "\n":
            fixed.append("\\n")
        elif char == "\r":
            fixed.append("\\r")
        else:
            fixed.append(char)
    else:
        fixed.append(char)
        if char == '"':
            inside_string = True

repaired_text = "".join(fixed)

# Validate before writing
try:
    record = json.loads(repaired_text)
except json.JSONDecodeError as error:
    print("Repair failed:", error)
    print("Original remains safe in:", backup)
    raise SystemExit(1)

source.write_text(
    json.dumps(record, ensure_ascii=False) + "\n",
    encoding="utf-8"
)

# Verify
with source.open("r", encoding="utf-8") as file:
    records = [json.loads(line) for line in file if line.strip()]

print("Validation repair successful.")
print("Valid records:", len(records))
print("Backup preserved:", backup.exists())
