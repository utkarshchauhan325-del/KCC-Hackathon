# CivicGuard-VLM: Municipal Vision-Language Model Training Pipeline

This directory contains the dataset curation, annotation schemas, and Parameter-Efficient Fine-Tuning (PEFT/LoRA) pipeline for domain-adapting Vision-Language Models to Indian municipal street infrastructure.

## Architecture Overview
- **Base Backbone:** `Qwen2-VL-7B-Instruct`
- **Methodology:** Low-Rank Adaptation (LoRA) on Query, Key, Value, and Projection matrices
- **Domain Focus:**
  1. Stormwater drain intake and grate blockage detection
  2. Illegal commercial waste & construction debris dumping identification
  3. Underpass flood level depth estimation
  4. Work clearance before/after visual verification

## Directory Structure
```
models_training/
├── configs/
│   └── lora_training_config.yaml   # Hyperparameters (lr=2e-4, r=16, alpha=32, bf16)
├── data/
│   └── civic_vlm_dataset.json      # Ground-truth multi-turn CCTV dialogue dataset
├── dataset_loader.py               # PyTorch Dataset implementation
├── train_vlm.py                    # Training and checkpointing pipeline
└── README.md                       # Technical specification
```

## Running the Training Pipeline
```bash
python models_training/train_vlm.py --config configs/lora_training_config.yaml
```
