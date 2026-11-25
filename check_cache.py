from huggingface_hub import snapshot_download

# Check if model files already exist in Hugging Face cache
import os
model_dir = r"C:\\Projects\class8-ai-teacher\\models\\Qwen3-8B"
existing_files = [f for f in os.listdir(model_dir) if os.path.isfile(os.path.join(model_dir, f))]
print(f"Existing files in cache: {existing_files}")

# Attempt download with resume support
temp_dir = os.path.join(model_dir, "temp")
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

result = snapshot_download(
    repo_id="Qwen/Qwen3-8B",
    local_dir=temp_dir,
    revision="main",
    resume_download=True
)

print(f"Downloaded to: {result}")

# Check if files were successfully transferred
final_files = [f for f in os.listdir(model_dir) if os.path.isfile(os.path.join(model_dir, f))]
new_files = [f for f in final_files if f not in existing_files]
print(f"New files transferred: {new_files}")