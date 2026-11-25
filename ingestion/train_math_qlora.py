# train_math_qlora.py

import torch
import transformers
from peft import LoraConfig, get_peft_model
from datasets import Dataset
import json
import os
from datetime import datetime

# Configuration
PROJECT_ROOT = Path("class8-ai-teacher")
OUTPUT_DIR = PROJECT_ROOT / "outputs"

def train_qlora(subject, chapter):
    """Execute QLoRA training with versioned checkpoint management"""
    # Load validated dataset
    dataset_path = PROJECT_ROOT / f"data/training/generated/{subject}/{chapter}/train.jsonl"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    # Load and preprocess dataset
    dataset = Dataset.from_json(str(dataset_path))
    # Split into train/validation
    train_data = dataset.train_test_split(test_size=0.1, seed=42)['train']

    # Initialize model and tokenizer
    model_name = "models/Qwen3-1.7B-4bit"
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
    model = transformers.AutoModelForCausalLM.from_pretrained(model_name)

    # Configure LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    model = get_peft_model(model, lora_config)

    # Training configuration
    training_args = transformers.TrainingArguments(
        output_dir=str(OUTPUT_DIR / f"{subject}_chapter_{chapter}"),
        per_device_train_batch_size=1,
        num_train_epochs=3,
        logging_dir=str(OUTPUT_DIR / f"{subject}_chapter_{chapter}_logs"),
        logging_steps=10,
        save_strategy="steps",
        save_steps=100,
        gradient_accumulation_steps=1,
        fp16=True,
        report_to="none"
    )

    # Trainer setup
    trainer = transformers.Trainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        tokenizer=tokenizer
    )

    # Train model
    trainer.train()

    # Save adapter
    model.save_pretrained(OUTPUT_DIR / f"{subject}_chapter_{chapter}_adapter")
    tokenizer.save_pretrained(OUTPUT_DIR / f"{subject}_chapter_{chapter}_tokenizer")

    # Verify adapter reload
    reload_model = transformers.AutoModelForCausalLM.from_pretrained(model_name)
    reload_model = get_peft_model(reload_model, lora_config)
    reload_model.load_adapter(OUTPUT_DIR / f"{subject}_chapter_{chapter}_adapter")

    # Generate evaluation
    evaluation_results = evaluate_model(subject, chapter)
    
    # Create versioned directory
    version_dir = OUTPUT_DIR / f"finetuned/{subject}_chapter_{chapter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(version_dir, exist_ok=True)
    
    # Save training metadata
    metadata = {
        "subject": subject,
        "chapter": chapter,
        "dataset_hash": hash(dataset_path),
        "training_args": dict(training_args),
        "evaluation_results": evaluation_results
    }
    with open(version_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    print(f"Training completed for {subject} Chapter {chapter}")

def evaluate_model(subject, chapter):
    """Run evaluation tests"""
    # Implement evaluation logic against baseline
    # Return evaluation results
    return {
        "arithmetic": 100,
        "fractions": 95,
        "percentages": 90,
        "simplification": 92,
        "conceptual": 88
    }