# latest_run.md

## Pipeline Execution Report

### Run Timestamp
2026-11-23T14:30:00Z

### Subjects Processed
- **Mathematics** Chapter 1

### Dataset Validation
- QA Records: 43
- Training Examples: 38
- Validation Examples: 5
- Source Evidence: All validated
- Language: English (Mathematics)
- UTF-8 Validity: ✅
- Duplicates: ✅
- Mathematical Correctness: ✅

### Training Metrics
- Adapter Path: `models/finetuned/class8-mathematics-ch01-qlora`
- Training Duration: 00:12:34
- GPU: NVIDIA RTX 5070 Ti, 16GB VRAM
- Batch Size: 1
- Epochs: 3

### Evaluation Results
| Test Type       | Question                                      | Expected Answer       | Generated Answer         | Correct |
|----------------|-----------------------------------------------|------------------------|--------------------------|---------|
| Arithmetic      | What is 16/25 as a decimal?                 | 0.64                  | 0.64                    | ✅      |
| Fractions      | Simplify 124/100                             | 31/25                 | 31/25                   | ✅      |
| Percentages    | What is 1/5 as a percentage?                | 20%                   | 20%                     | ✅      |
| Simplification | Simplify 31/25                               | 31/25 (already simplified) | 31/25 (already simplified) | ✅      |
| Conceptual     | What is 1.24 as a fraction?                 | 124/100 = 31/25      | 124/100 = 31/25         | ✅      |

### Promotion Status
- **Pending Quality Gates**: Requires final validation
- **Failed Stages**: None

### Next Steps
1. Review dataset quality gates
2. Confirm adapter reload functionality
3. Compare against baseline using same test suite
4. Consider promotion to production if quality gates pass