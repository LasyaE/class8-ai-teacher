from huggingface_hub import HfApi

api = HfApi()
try:
    info = api.model_info("Qwen/Qwen3-8B")
    print(f"Repository: {info.id}")
    print(f"Private: {info.private}")
    print(f"Files: {len(info.siblings)}")
except Exception as e:
    print(f"Error: {str(e)}")