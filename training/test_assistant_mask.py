
import json
from pathlib import Path

from transformers import AutoTokenizer

MODEL_DIR = "models/Qwen3-1.7B-4bit"
DATASET = "data/training/mathematics/train.jsonl"

# Load the actual local Qwen3 tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
)

# Read one training record
with open(DATASET, "r", encoding="utf-8") as file:
    record = json.loads(next(line for line in file if line.strip()))

messages = record["messages"]

# Require a simple system -> user -> assistant conversation
roles = [message["role"] for message in messages]

if roles != ["system", "user", "assistant"]:
    raise ValueError(f"Unexpected message roles: {roles}")

# Render the complete conversation using the real template
formatted = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=False,
)

# Render the conversation without the assistant message.
# This gives us a tokenized prefix ending at the assistant boundary.
prefix_messages = messages[:-1]

prefix_formatted = tokenizer.apply_chat_template(
    prefix_messages,
    tokenize=False,
    add_generation_prompt=True,
)

# Verify that the complete conversation begins with the exact prefix.
if not formatted.startswith(prefix_formatted):
    raise RuntimeError(
        "The assistant prefix is not stable. "
        "Cannot safely determine the assistant token boundary."
    )

# Tokenize both strings without adding extra special tokens.
full_ids = tokenizer.encode(
    formatted,
    add_special_tokens=False,
)

prefix_ids = tokenizer.encode(
    prefix_formatted,
    add_special_tokens=False,
)

# Require token-level prefix stability too.
if full_ids[:len(prefix_ids)] != prefix_ids:
    raise RuntimeError(
        "Token IDs are not prefix-stable. "
        "Do not use this masking method."
    )

# Supervise only tokens after the assistant generation prefix.
labels = [-100] * len(prefix_ids) + full_ids[len(prefix_ids):]

# Decode the actual supervised portion
supervised_ids = full_ids[len(prefix_ids):]
supervised_text = tokenizer.decode(
    supervised_ids,
    skip_special_tokens=False,
)

expected_answer = messages[-1]["content"]

print("Tokenizer:", tokenizer.__class__.__name__)
print("\nFormatted conversation:\n", formatted)
print("\nExpected assistant answer:\n", expected_answer)
print("\nDecoded supervised portion:\n", supervised_text)
print("\nInput token IDs:\n", full_ids)
print("\nLabels:\n", labels)
print("\nMasked tokens:", labels.count(-100))
print("Supervised tokens:", len(full_ids) - labels.count(-100))

# Assertions
assert len(full_ids) == len(labels)
assert len(supervised_ids) > 0
assert supervised_text.endswith(expected_answer), (
    "Decoded supervised text does not end with the expected answer."
)
assert all(label == -100 for label in labels[:len(prefix_ids)])
assert labels[len(prefix_ids):] == full_ids[len(prefix_ids):]

print("\nPASS: Prefix-based assistant masking checks passed.")
