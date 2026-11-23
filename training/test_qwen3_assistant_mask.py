# training/test_qwen3_assistant_mask.py

import json
from transformers import AutoTokenizer
import os
import torch

# 📁 Load tokenizer from local model
MODEL_DIR = "models/Qwen3-1.7B-4bit"
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    local_files_only=True,
    padding_side="right"
)

# 📜 Inspect tokenizer metadata
print(f"Tokenizer class: {type(tokenizer).__name__}")
print(f"Tokenizer version: {tokenizer.name_or_path}")
print(f"Chat template: {getattr(tokenizer, "chat_template", "None")}")
print(f"Special tokens: {tokenizer.special_tokens_map}
")

# 📁 Check chat_template.jinja
template_path = os.path.join(MODEL_DIR, "chat_template.jinja")
if os.path.exists(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        print("Chat template content:")
        print(f.read())
else:
    print("Chat template file not found")

# 📚 Load one record from train.jsonl
with open("data/training/mathematics/train.jsonl", "r", encoding="utf-8") as f:
    record = json.loads(f.readline())

# 🧠 Tokenize with chat template
tokenized = tokenizer(
    record["messages"],
    tokenize=True,
    return_dict=True,
    truncation=True,
    padding="max_length",
    max_length=1024
)

# 🧪 Check for generation blocks
if "generation" in tokenizer.chat_template:
    print("Tokenizer supports assistant tokens mask")
    masked = tokenizer.apply_chat_template(
        record["messages"],
        tokenize=True,
        return_assistant_tokens_mask=True
    )
    print("Masked tokens:", masked)
else:
    print("Tokenizer does not support assistant tokens mask")
    # 🧮 Manual message-boundary masking
    # ... (implementation details)

# 🧮 Construct labels
labels = [-100] * len(tokenized["input_ids"])
labels[masked] = tokenized["input_ids"].tolist()[0][masked] if "masked" in locals() else tokenized["input_ids"].tolist()[0]

# 🧾 Decode and count
decoded_input = tokenizer.decode(tokenized["input_ids"].tolist()[0], skip_special_tokens=False)
decoded_labels = tokenizer.decode(labels, skip_special_tokens=False)

masked_count = sum(1 for x in labels if x == -100)
supervised_count = len(labels) - masked_count

print(f"Masked tokens: {masked_count}")
print(f"Supervised tokens: {supervised_count}")
print(f"Decoded input: {decoded_input}")
print(f"Decoded labels: {decoded_labels}")

# 🧪 Assertions
assert supervised_count > 0, "No assistant tokens supervised"
assert masked_count > 0, "No tokens masked"
assert "<s>" in decoded_input, "Missing system token"
assert "<s>" not in decoded_labels, "System token in labels"
assert "<user>" not in decoded_labels, "User token in labels"
assert "<assistant>" in decoded_labels, "Assistant token missing"
assert "<|endoftext|>" in decoded_input, "Missing end-of-text token"
assert "<|endoftext|>" not in decoded_labels, "End-of-text in labels"

print("All assertions passed")