from pathlib import Path
from huggingface_hub import snapshot_download

project = Path(r"C:\\Projects\class8-ai-teacher")
model_dir = project / "models" / "Qwen3-8B"
model_dir.mkdir(parents=True, exist_ok=True)

print("Starting Qwen3-8B download...")
print("Destination:", model_dir)

result = snapshot_download(
    repo_id="Qwen/Qwen3-8B",
    local_dir=str(model_dir),
    revision="main",
)

print("Download finished:", result)

required = [
    model_dir / "config.json",
    model_dir / "tokenizer.json",
]

for path in required:
    print(path.name, "FOUND" if path.is_file() else "MISSING")

weights = list(model_dir.glob("*.safetensors"))
print("Safetensors files:", len(weights))

if not (model_dir / "config.json").is_file() or not weights:
    raise RuntimeError("Model checkpoint verification failed.")

print("Basic checkpoint verification passed.")