from pathlib import Path
from modelscope import snapshot_download

project = Path(r"C:\\Projects\class8-ai-teacher")
destination = project / "models" / "Qwen3-8B-modelscope"
destination.mkdir(parents=True, exist_ok=True)

print("Downloading official Qwen3-8B from ModelScope...")

result = snapshot_download(
    model_id="Qwen/Qwen3-8B",
    local_dir=str(destination),
)

print("Download result:", result)

config = destination / "config.json"
weights = list(destination.glob("*.safetensors"))

print("Config exists:", config.is_file())
print("Weight shard count:", len(weights))

if not config.is_file() or not weights:
    raise RuntimeError("Checkpoint verification failed.")

print("Basic checkpoint verification passed.")