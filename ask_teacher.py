import os
import json
import re
import sys
from rank_bm25 import BM25Okapi
from langchain_ollama import ChatOllama, OllamaLLM
from subprocess import run, PIPE

# 1. Load actual textbook data
def load_textbooks():
    subjects = ["biological-science", "english", "hindi", "mathematics", "physical-science", "social-studies", "telugu"]
    texts = []
    metadata = []
    for subject in subjects:
        dir_path = os.path.join("data", "processed", "jsonl")
        if not os.path.exists(dir_path):
            print(f"❌ Directory {dir_path} does not exist.")
            return None, None
        files = [f for f in os.listdir(dir_path) if f.startswith(f"{subject}_")]
        for file in files:
            file_path = os.path.join(dir_path, file)
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        # Extract only existing fields
                        text = entry.get("input", "") + " " + entry.get("output", "")
                        if not text.strip():
                            continue
                        texts.append(text)
                        metadata.append({
                            "subject": entry.get("subject", "Unknown"),
                            "chapter": entry.get("chapter", "Unknown"),
                            "page": entry.get("page", "Unknown"),
                            "source": entry.get("source", "Unknown")
                        })
                    except json.JSONDecodeError:
                        print(f"⚠️ Malformed JSON in {file_path}")
                        continue
    return texts, metadata

# 2. BM25 Indexing
def build_bm25_index(texts):
    tokenized_texts = [doc.lower().split() for doc in texts]
    bm25 = BM25Okapi(tokenized_texts)
    return bm25

# 3. Ollama Model Selection
def get_ollama_model():
    try:
        # Capture actual ollama list output
        result = run([
            "ollama",
            "list"
        ], stdout=PIPE, stderr=PIPE, text=True, check=True)
        models = [line.split()[0].strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith("NAME")]
        if not models:
            raise RuntimeError("No models found in ollama list")
        
        model_name = input(f"Select a model from {models}: ")
        if not model_name:
            raise ValueError("No model selected")
        if model_name not in models:
            raise ValueError(f"Model {model_name} not found")
        
        return ChatOllama(model=model_name, temperature=0)
    except Exception as e:
        print(f"❌ Error connecting to Ollama: {e}")
        sys.exit(1)

# 4. Main Interaction Loop
def ask_teacher():
    texts, metadata = load_textbooks()
    if not texts:
        print("❌ No valid textbook data found. Check the data directory.")
        return
    
    # Verify dataset
    subject_counts = {}
    for meta in metadata:
        subject = meta["subject"]
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
    
    print(f"✅ Loaded {sum(subject_counts.values())} textbook records:")
    for subject, count in subject_counts.items():
        print(f"  - {subject}: {count} records")
    
    bm25 = build_bm25_index(texts)
    model = get_ollama_model()
    
    print("📚 Telangana Textbook Q&A System (Type 'exit' to quit)")
    while True:
        question = input("\n❓ Question: ").strip()
        if question.lower() in ["exit", "quit"]:
            break
        if not question:
            continue
        
        # BM25 Search
        tokenized_question = question.lower().split()
        doc_scores = bm25.get_scores(tokenized_question)
        top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:3]
        
        # Filter by relevance and check for zero scores
        relevant_results = []
        for i in top_indices:
            score = doc_scores[i]
            text = texts[i]
            meta = metadata[i]
            if score > 0:
                relevant_results.append((score, text, meta))
        
        if not relevant_results:
            print("❌ No relevant textbook passages found.")
            continue
        
        # Format prompt with actual text and metadata
        formatted_sources = []
        for i, (score, text, meta) in enumerate(relevant_results):
            formatted_sources.append(
                f"{i+1}. Chapter {meta["chapter"]}, Page {meta["page"]} ({meta["source"]})\nText: {text}"
            )
        
        # Send to Ollama with proper chat interface
        try:
            answer = model.invoke(
                f"\n<System> You are a Telangana textbook assistant. Answer only using the provided passages. If there is not enough evidence, say so.\n<User> {question}\n\nPassages:\n{chr(10).join(formatted_sources)}\n\nAnswer:\n</System>"
            )
            print(f"\n🧠 Answer:\n{answer}")
            print(f"\n📝 Sources:\n{chr(10).join(formatted_sources)}")
        except Exception as e:
            print(f"❌ Error getting answer: {e}")

if __name__ == "__main__":
    ask_teacher()