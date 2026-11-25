# run_pipeline.py

import argparse
import os
import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from packaging import version
import subprocess
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CHAPTER_MAPPING = PROJECT_ROOT / "config" / "chapter_mapping.json"

def run_preflight_checks(args):
    """Run all preflight checks for dry-run mode"""
    results = []

    # 1. Subject and Chapter Mapping
    results.append(check_subject_chapter_mapping(args.subject, args.chapter))

    # 2. Extracted Source Pages
    results.append(check_source_pages(args.subject, args.chapter))

    # 3. QA Generation Script
    results.append(check_qa_script(args.subject, args.chapter))

    # 4. QLORA Training Script
    results.append(check_training_script())

    # 5. Base Model
    results.append(check_base_model())

    # 6. Baseline Adapter
    results.append(check_baseline_adapter(args.subject, args.chapter))

    # 7. Python Environment
    results.append(check_python_environment())

    # 8. Ollama Connection
    results.append(check_ollama_connection())

    # 9. Ollama Model
    results.append(check_ollama_model())

    # 10. Dataset Structure
    results.append(check_dataset_structure(args.subject, args.chapter))

    # 11. Output Directory Readiness
    results.append(check_output_directories())

    return results
    """Run all preflight checks for dry-run mode"""
    results = []
    
    # 1. Subject and Chapter Mapping
    results.append(check_subject_chapter_mapping(args.subject, args.chapter))
    
    # 2. Extracted Source Pages
    results.append(check_source_pages(args.subject, args.chapter))
    
    # 3. QA Generation Script
    results.append(check_qa_script(args.subject, args.chapter))
    
    # 4. QLoRA Training Script
    results.append(check_training_script())
    
    # 5. Base Model
    results.append(check_base_model())
    
    # 6. Baseline Adapter
    results.append(check_baseline_adapter(args.subject, args.chapter))
    
    # 7. Python Environment
    results.append(check_python_environment())
    
    # 8. Ollama Connection
    results.append(check_ollama_connection())
    
    # 9. Ollama Model
    results.append(check_ollama_model())
    
    # 10. Dataset Structure
    results.append(check_dataset_structure(args.subject, args.chapter))
    
    # 11. Output Directory Readiness
    results.append(check_output_directories())
    
    return results

def check_subject_chapter_mapping(subject, chapter):
    """Validate against the verified chapter mapping currently available."""
    subject_key = subject.lower().replace("_", "-")
    chapter_num = int(chapter)

    # Verified Mathematics chapter mapping.
    if subject_key in ("mathematics", "math") and chapter_num == 1:
        return {
            "name": "Subject and Chapter Mapping",
            "status": "PASS",
            "message": "Mathematics Chapter 1: Rational Numbers, PDF pages 13-45",
            "critical": False
        }

    return {
        "name": "Subject and Chapter Mapping",
        "status": "FAIL",
        "message": f"No verified chapter mapping currently configured for {subject}, chapter {chapter_num}",
        "critical": True
    }
    """Validate against the verified chapter mapping currently available."""
    subject_key = subject.lower().replace("_", "-")
    chapter_num = int(chapter)

    # Verified Mathematics chapter mapping.
    if subject_key in ("mathematics", "math") and chapter_num == 1:
        return {
            "name": "Subject and Chapter Mapping",
            "status": "PASS",
            "message": "Mathematics Chapter 1: Rational Numbers, PDF pages 13-45",
            "critical": False
        }

    return {
        "name": "Subject and Chapter Mapping",
        "status": "FAIL",
        "message": f"No verified chapter mapping currently configured for {subject}, chapter {chapter_num}",
        "critical": True
    }

def check_source_pages(subject, chapter):
    """Find extracted PDF pages recursively, without assuming chapter folders."""
    subject_root = PROJECT_ROOT / "data" / "extracted" / "raw" / subject.lower()

    if subject.lower() in ("mathematics", "math") and int(chapter) == 1:
        first_page, last_page = 13, 45
    else:
        return {
            "name": "Extracted Source Pages",
            "status": "FAIL",
            "message": "No verified PDF page range configured for this subject and chapter",
            "critical": True
        }

    if not subject_root.is_dir():
        return {
            "name": "Extracted Source Pages",
            "status": "FAIL",
            "message": f"Subject extraction directory not found: {subject_root}",
            "critical": True
        }

    missing = []
    for number in range(first_page, last_page + 1):
        expected = f"page-{number:04d}.txt"
        if not any(subject_root.rglob(expected)):
            missing.append(expected)

    if missing:
        return {
            "name": "Extracted Source Pages",
            "status": "FAIL",
            "message": f"Missing {len(missing)} source pages: {chr(44).join(missing[:8])}",
            "critical": True
        }

    return {
        "name": "Extracted Source Pages",
        "status": "PASS",
        "message": f"All {last_page - first_page + 1} Mathematics Chapter 1 source pages found recursively",
        "critical": False
    }
    """Find extracted PDF pages recursively, without assuming chapter folders."""
    subject_root = PROJECT_ROOT / "data" / "extracted" / "raw" / subject.lower()

    if subject.lower() in ("mathematics", "math") and int(chapter) == 1:
        first_page, last_page = 13, 45
    else:
        return {
            "name": "Extracted Source Pages",
            "status": "FAIL",
            "message": "No verified PDF page range configured for this subject and chapter",
            "critical": True
        }

    if not subject_root.is_dir():
        return {
            "name": "Extracted Source Pages",
            "status": "FAIL",
            "message": f"Subject extraction directory not found: {subject_root}",
            "critical": True
        }

    missing = []
    for number in range(first_page, last_page + 1):
        expected = f"page-{number:04d}.txt"
        if not any(subject_root.rglob(expected)):
            missing.append(expected)

    if missing:
        return {
            "name": "Extracted Source Pages",
            "status": "FAIL",
            "message": f"Missing {len(missing)} source pages: {', '.join(missing[:8])}",
            "critical": True
        }

    return {
        "name": "Extracted Source Pages",
        "status": "PASS",
        "message": f"All {last_page - first_page + 1} Mathematics Chapter 1 source pages found recursively",
        "critical": False
    }

def check_qa_script(subject, chapter):
    """Check the actual QA generator location."""
    script_path = PROJECT_ROOT / "ingestion" / "generate_math_qa.py"

    if subject.lower() not in ("mathematics", "math"): 
        return {
            "name": "QA Generation Script",
            "status": "FAIL",
            "message": f"No QA generator configured for {subject}",
            "critical": True
        }

    exists = script_path.is_file()
    return {
        "name": "QA Generation Script",
        "status": "PASS" if exists else "FAIL",
        "message": f"QA generator: {script_path}",
        "critical": not exists
    }
    """Check the actual QA generator location."""
    script_path = PROJECT_ROOT / "ingestion" / "generate_math_qa.py"

    if subject.lower() not in ("mathematics", "math"):
        return {
            "name": "QA Generation Script",
            "status": "FAIL",
            "message": f"No QA generator configured for {subject}",
            "critical": True
        }

    exists = script_path.is_file()
    return {
        "name": "QA Generation Script",
        "status": "PASS" if exists else "FAIL",
        "message": f"QA generator: {script_path}",
        "critical": not exists
    }

def check_training_script():
    """Check the existing Mathematics QLORA trainer."""
    script_path = PROJECT_ROOT / "ingestion" / "train_math_qlora.py"
    exists = script_path.is_file()
    return {
        "name": "QLORA Training Script",
        "status": "PASS" if exists else "FAIL",
        "message": f"Training script: {script_path}",
        "critical": not exists
    }
    """Check the existing Mathematics QLoRA trainer."""
    script_path = PROJECT_ROOT / "ingestion" / "train_math_qlora.py"
    exists = script_path.is_file()
    return {
        "name": "QLORA Training Script",
        "status": "PASS" if exists else "FAIL",
        "message": f"Training script: {script_path}",
        "critical": not exists
    }

def check_base_model():
    """Verify the base model directory."""
    model_dir = PROJECT_ROOT / "models" / "Qwen3-1.7B-4bit"
    exists = model_dir.is_dir()
    return {
        "name": "Base Model",
        "status": "PASS" if exists else "FAIL",
        "message": f"Base model: {model_dir}",
        "critical": not exists
    }
    """Verify the base model directory."""
    model_dir = PROJECT_ROOT / "models" / "Qwen3-1.7B-4bit"
    exists = model_dir.is_dir()
    return {
        "name": "Base Model",
        "status": "PASS" if exists else "FAIL",
        "message": f"Base model: {model_dir}",
        "critical": not exists
    }

def check_baseline_adapter(subject, chapter):
    """Verify the existing baseline adapter without modifying it."""
    adapter_dir = (PROJECT_ROOT / "models" / "finetuned" /
                   f"class8-{subject}-ch{int(chapter):02d}-qlora")
    weights = adapter_dir / "adapter_model.safetensors"
    config = adapter_dir / "adapter_config.json"

    if not adapter_dir.is_dir() or not weights.is_file() or not config.is_file():
        return {
            "name": "Baseline Adapter",
            "status": "FAIL",
            "message": f"Expected adapter weights and config under: {adapter_dir}",
            "critical": True
        }

    return {
        "name": "Baseline Adapter",
        "status": "PASS",
        "message": f"Baseline adapter and required files found: {adapter_dir}",
        "critical": False
    }
    """Verify the existing baseline adapter without modifying it."""
    adapter_dir = (
        PROJECT_ROOT / "models" / "finetuned" /
        f"class8-{subject}-ch{int(chapter):02d}-qlora"
    )
    weights = adapter_dir / "adapter_model.safetensors"
    config = adapter_dir / "adapter_config.json"

    if not adapter_dir.is_dir() or not weights.is_file() or not config.is_file():
        return {
            "name": "Baseline Adapter",
            "status": "FAIL",
            "message": f"Expected adapter weights and config under: {adapter_dir}",
            "critical": True
        }

    return {
        "name": "Baseline Adapter",
        "status": "PASS",
        "message": f"Baseline adapter and required files found: {adapter_dir}",
        "critical": False
    }

def check_python_environment():
    """Verify the dedicated AI virtual environment and required packages."""
    env_path = PROJECT_ROOT / ".venv-ai" / "Scripts" / "python.exe"

    if not env_path.is_file():
        return {
            "name": "Python Environment",
            "status": "FAIL",
            "message": f"AI interpreter not found: {env_path}",
            "critical": True
        }

    required = [
        ("transformers", "4.45.0"),
        ("peft", "0.9.0"),
        ("torch", "2.0.0"),
        ("packaging", "23.1"),
        ("requests", "2.29.0")
    ]

    try:
        for package, minimum in required:
            result = subprocess.run(
                [str(env_path), "-m", "pip", "show", package],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return {
                    "name": "Python Environment",
                    "status": "FAIL",
                    "message": f"Required package not installed: {package}",
                    "critical": True
                }

            match = re.search(r"(?m)^Version:\s*(\S+)", result.stdout)
            if not match or version.parse(match.group(1)) < version.parse(minimum):
                installed = match.group(1) if match else "unknown"
                return {
                    "name": "Python Environment",
                    "status": "FAIL",
                    "message": f"{package} version {installed}; minimum required {minimum}",
                    "critical": True
                }

        return {
            "name": "Python Environment",
            "status": "PASS",
            "message": "AI interpreter and required packages verified",
            "critical": False
        }
    except Exception as exc:
        return {
            "name": "Python Environment",
            "status": "FAIL",
            "message": f"Environment check failed: {exc}",
            "critical": True
        }
    """Verify the dedicated AI virtual environment and required packages."""
    env_path = PROJECT_ROOT / ".venv-ai" / "Scripts" / "python.exe"

    if not env_path.is_file():
        return {
            "name": "Python Environment",
            "status": "FAIL",
            "message": f"AI interpreter not found: {env_path}",
            "critical": True
        }

    required = [
        ("transformers", "4.45.0"),
        ("peft", "0.9.0"),
        ("torch", "2.0.0"),
        ("packaging", "23.1"),
        ("requests", "2.29.0")
    ]

    try:
        for package, minimum in required:
            result = subprocess.run(
                [str(env_path), "-m", "pip", "show", package],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return {
                    "name": "Python Environment",
                    "status": "FAIL",
                    "message": f"Required package not installed: {package}",
                    "critical": True
                }

            match = re.search(r"(?m)^Version:\s*(\S+)", result.stdout)
            if not match or version.parse(match.group(1)) < version.parse(minimum):
                installed = match.group(1) if match else "unknown"
                return {
                    "name": "Python Environment",
                    "status": "FAIL",
                    "message": f"{package} version {installed}; minimum required {minimum}",
                    "critical": True
                }

        return {
            "name": "Python Environment",
            "status": "PASS",
            "message": "AI interpreter and required packages verified",
            "critical": False
        }
    except Exception as exc:
        return {
            "name": "Python Environment",
            "status": "FAIL",
            "message": f"Environment check failed: {exc}",
            "critical": True
        }

def check_ollama_connection():
    """Verify Ollama is running and accessible"""
    try:
        # Check Ollama connection
        req = Request("http://localhost:11434/api/tags", headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=5) as response:
            response_data = json.loads(response.read().decode())
            
            if not response_data:
                return {
                    "name": "Ollama Connection",
                    "status": "FAIL",
                    "message": "No response from Ollama",
                    "critical": True
                }
            
            return {
                "name": "Ollama Connection",
                "status": "PASS",
                "message": "Ollama connection successful",
                "critical": False
            }
    except Exception as e:
        return {
            "name": "Ollama Connection",
            "status": "FAIL",
            "message": f"Ollama connection failed: {str(e)}",
            "critical": True
        }
    """Verify Ollama is running and accessible"""
    try:
        # Check Ollama connection
        req = Request("http://localhost:11434/api/tags", headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=5) as response:
            response_data = json.loads(response.read().decode())
            
            if not response_data:
                return {
                    "name": "Ollama Connection",
                    "status": "FAIL",
                    "message": "No response from Ollama",
                    "critical": True
                }
            
            return {
                "name": "Ollama Connection",
                "status": "PASS",
                "message": "Ollama connection successful",
                "critical": False
        }
    except Exception as e:
        return {
            "name": "Ollama Connection",
            "status": "FAIL",
            "message": f"Ollama connection failed: {str(e)}",
            "critical": True
        }

def check_ollama_model():
    """Check qwen3:8b in Ollama's /api/tags response."""
    try:
        req = Request(
            "http://localhost:11434/api/tags",
            headers={"Content-Type": "application/json"}
        )
        with urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        models = payload.get("models", []) if isinstance(payload, dict) else []
        names = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("name", "")
            elif isinstance(item, str):
                name = item
            else:
                continue
            if name:
                names.append(name)

        found = any(
            name == "qwen3:8b" or name.startswith("qwen3:8b-")
            for name in names
        )

        return {
            "name": "Ollama Model",
            "status": "PASS" if found else "FAIL",
            "message": "Ollama model qwen3:8b available" if found
                       else f"qwen3:8b not found; installed models: {names}",
            "critical": not found
        }
    except Exception as exc:
        return {
            "name": "Ollama Model",
            "status": "FAIL",
            "message": f"Ollama model check failed: {exc}",
            "critical": True
        }
    """Check qwen3:8b in Ollama's /api/tags response."""
    try:
        req = Request(
            "http://localhost:11434/api/tags",
            headers={"Content-Type": "application/json"}
        )
        with urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        models = payload.get("models", []) if isinstance(payload, dict) else []
        names = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("name", "")
            elif isinstance(item, str):
                name = item
            else:
                continue
            if name:
                names.append(name)

        found = any(
            name == "qwen3:8b" or name.startswith("qwen3:8b-")
            for name in names
        )

        return {
            "name": "Ollama Model",
            "status": "PASS" if found else "FAIL",
            "message": "Ollama model qwen3:8b available" if found
                       else f"qwen3:8b not found; installed models: {names}",
            "critical": not found
        }
    except Exception as exc:
        return {
            "name": "Ollama Model",
            "status": "FAIL",
            "message": f"Ollama model check failed: {exc}",
            "critical": True
        }

def check_dataset_structure(subject, chapter):
    """Inspect actual dataset artifacts without treating unapproved drafts as training data."""
    dataset_dir = (PROJECT_ROOT / "data" / "training" / "generated" /
                   subject.lower() / f"chapter_{int(chapter):02d}")

    train_path = dataset_dir / "train.jsonl"
    validation_path = dataset_dir / "validation.jsonl"
    draft_path = dataset_dir / "qa_drafts.jsonl"

    if train_path.is_file() and validation_path.is_file():
        if train_path.stat().st_size > 0 and validation_path.stat().st_size > 0:
            return {
                "name": "Dataset Structure",
                "status": "PASS",
                "message": f"Training and validation datasets found in {dataset_dir}",
                "critical": False
            }

    if draft_path.is_file() and draft_path.stat().st_size > 0:
        return {
            "name": "Dataset Structure",
            "status": "WARN",
            "message": "QA drafts found, but approved train.jsonl and validation.jsonl are not both ready. Training must not start yet.",
            "critical": False
        }

    # The original QA workflow may store drafts directly under data/training/<subject>.
    alternate = PROJECT_ROOT / "data" / "training" / subject.lower() / "qa_drafts.jsonl"
    if alternate.is_file() and alternate.stat().st_size > 0:
        return {
            "name": "Dataset Structure",
            "status": "WARN",
            "message": f"QA draft exists at {alternate}; approved train/validation files still need preparation.",
            "critical": False
        }

    return {
        "name": "Dataset Structure",
        "status": "WARN",
        "message": f"No approved training dataset or QA draft found at {dataset_dir}. Dataset generation may still be required.",
        "critical": False
    }
    """Inspect actual dataset artifacts without treating unapproved drafts as training data."""
    dataset_dir = (
        PROJECT_ROOT / "data" / "training" / "generated" /
        subject.lower() / f"chapter_{int(chapter):02d}"
    )

    train_path = dataset_dir / "train.jsonl"
    validation_path = dataset_dir / "validation.jsonl"
    draft_path = dataset_dir / "qa_drafts.jsonl"

    if train_path.is_file() and validation_path.is_file():
        if train_path.stat().st_size > 0 and validation_path.stat().st_size > 0:
            return {
                "name": "Dataset Structure",
                "status": "PASS",
                "message": f"Training and validation datasets found in {dataset_dir}",
                "critical": False
            }

    if draft_path.is_file() and draft_path.stat().st_size > 0:
        return {
            "name": "Dataset Structure",
            "status": "WARN",
            "message": "QA drafts found, but approved train.jsonl and validation.jsonl are not both ready. Training must not start yet.",
            "critical": False
        }

    # The original QA workflow may store drafts directly under data/training/<subject>.
    alternate = PROJECT_ROOT / "data" / "training" / subject.lower() / "qa_drafts.jsonl"
    if alternate.is_file() and alternate.stat().st_size > 0:
        return {
            "name": "Dataset Structure",
            "status": "WARN",
            "message": f"QA draft exists at {alternate}; approved train/validation files still need preparation.",
            "critical": False
        }

    return {
        "name": "Dataset Structure",
        "status": "WARN",
        "message": f"No approved training dataset or QA draft found at {dataset_dir}. Dataset generation may still be required.",
        "critical": False
    }

def check_output_directories():
    """Verify output directories can be created"""
    try:
        # Check evaluations directory
        eval_dir = OUTPUT_DIR / "evaluations"
        os.makedirs(eval_dir, exist_ok=True)
        
        # Check versions directory
        versions_dir = OUTPUT_DIR / "finetuned/versions"
        os.makedirs(versions_dir, exist_ok=True)
        
        return {
            "name": "Output Directory Readiness",
            "status": "PASS",
            "message": "Output directories confirmed writable",
            "critical": False
        }
    except Exception as e:
        return {
            "name": "Output Directory Readiness",
            "status": "FAIL",
            "message": f"Failed to create output directories: {str(e)}",
            "critical": True
        }
    """Verify output directories can be created"""
    try:
        # Check evaluations directory
        eval_dir = OUTPUT_DIR / "evaluations"
        os.makedirs(eval_dir, exist_ok=True)
        
        # Check versions directory
        versions_dir = OUTPUT_DIR / "finetuned/versions"
        os.makedirs(versions_dir, exist_ok=True)
        
        return {
            "name": "Output Directory Readiness",
            "status": "PASS",
            "message": "Output directories confirmed writable",
            "critical": False
        }
    except Exception as e:
        return {
            "name": "Output Directory Readiness",
            "status": "FAIL",
            "message": f"Failed to create output directories: {str(e)}",
            "critical": True
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True, choices=["mathematics", "physical-science", "biological-science", "social-studies", "english", "telugu", "hindi"])
    parser.add_argument("--chapter", type=int, default=1)
    parser.add_argument("--all-chapters", action="store_true")
    parser.add_argument("--all-subjects", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    if args.dry_run:
        results = run_preflight_checks(args)
        
        for result in results:
            status = result["status"]
            name = result["name"]
            message = result["message"]
            critical = result["critical"]
            
            if critical:
                print(f"[FAIL] {name}: {message}")
            else:
                print(f"[{status}] {name}: {message}")
        
        # Check for critical failures
        for result in results:
            if result["critical"] and result["status"] == "FAIL":
                exit(1)
        
        print("\nDry-run completed successfully. No critical failures detected.")
        return
    
    # Original pipeline execution logic here
    
if __name__ == "__main__":
    main()
