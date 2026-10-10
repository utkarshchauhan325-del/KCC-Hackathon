"""Custom PyTorch dataset loader for Civic-VLM multimodal instruction tuning."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image

try:
    import torch
    from torch.utils.data import Dataset
except ImportError:
    class Dataset:
        pass


class CivicVLMDataset(Dataset):
    """Dataset loader parsing municipal CCTV multimodal conversations for VLM instruction tuning."""

    def __init__(self, data_path: str, image_root: Optional[str] = None, transform=None):
        self.data_path = Path(data_path)
        self.image_root = Path(image_root) if image_root else self.data_path.parent
        self.transform = transform
        
        with open(self.data_path, "r", encoding="utf-8") as f:
            self.samples: List[Dict[str, Any]] = json.load(f)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = self.samples[idx]
        img_file = self.image_root / Path(item["image_path"]).name
        
        if img_file.exists():
            image = Image.open(img_file).convert("RGB")
        else:
            # Fallback tensor for dry-run
            image = Image.new("RGB", (448, 448), color=(128, 128, 128))

        if self.transform:
            image = self.transform(image)

        prompt = item["conversations"][0]["content"]
        target_response = item["conversations"][1]["content"]

        return {
            "id": item["id"],
            "location": item.get("location", "Unknown"),
            "hazard_category": item.get("hazard_category", "general"),
            "image": image,
            "prompt": prompt,
            "target": target_response,
            "ground_truth_boxes": item.get("ground_truth_boxes", []),
        }
