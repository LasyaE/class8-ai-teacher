import json
from pathlib import Path

files = [
    Path("data/training/mathematics/train.jsonl"),
    Path("data/training/mathematics/validation.jsonl"),
]

for path in files:
    print("\n" + "=" * 65)
    print("FILE:", path)

    with path.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file, 1):
            record = json.loads(line)

            print(f"\nRECORD {index}")

            for message in record["messages"]:
                print(f"\n[{message['role'].upper()}]")
                print(message["content"])

            print("\nMETADATA:")
            print(json.dumps(
                record.get("metadata", {}),
                indent=2,
                ensure_ascii=False
            ))
