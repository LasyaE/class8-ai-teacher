# evaluation_tests.py

import json
import os
from datetime import datetime
from peft import LoraConfig
import transformers

# Baseline evaluation questions
baseline_tests = {
    "arithmetic": {
        "question": "What is 16/25 as a decimal?",
        "expected": "0.64"
    },
    "fractions": {
        "question": "Simplify 124/100.",
        "expected": "31/25"
    },
    "percentages": {
        "question": "What is 1/5 as a percentage?",
        "expected": "20%"
    },
    "simplification": {
        "question": "Simplify 31/25.",
        "expected": "31/25 (already simplified)"
    },
    "conceptual": {
        "question": "What is 1.24 as a fraction?",
        "expected": "124/100 = 31/25"
    }
}

# Evaluation results storage
results_dir = "class8-ai-teacher/outputs/evaluations"

def run_evaluations(subject, chapter):
    """Run evaluation tests and compare against baseline"""
    # Load model and tokenizer
    model_path = "models/Qwen3-1.7B-4bit"
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_path)
    model = transformers.AutoModelForCausalLM.from_pretrained(model_path)

    # Load adapter if exists
    adapter_path = f"models/finetuned/class8-{subject}-ch{chapter}-qlora"
    if os.path.exists(adapter_path):
        model = get_peft_model(model, LoraConfig.from_pretrained(adapter_path))
        model.load_adapter(adapter_path)

    # Execute tests
    evaluation_results = {}
    for test_name, test in baseline_tests.items():
        prompt = f"{test['question']}\nAnswer:"
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=100)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract answer
        answer_start = response.find("Answer:")
        if answer_start != -1:
            answer = response[answer_start + len("Answer:"):].strip()
        else:
            answer = """ 

        evaluation_results[test_name] = {
            "question": test['question'],
            "expected": test['expected'],
            "generated": answer,
            "correct": answer == test['expected']
        }

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"{results_dir}/{subject}_ch{chapter}_{timestamp}.json"
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(evaluation_results, f, indent=2)

    return evaluation_results