#!/usr/bin/env python3
"""One-time setup: download YOLOE weights and build the CivicEye detector model.

The first build downloads ~280 MB (segmentation weights + text encoder) into data/models/.
Running this before a demo avoids that delay on the first video upload.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.detector import build_detector_model


def main():
    path = build_detector_model(settings.DETECTOR_MODEL)
    print(f"Detector model ready: {path}")


if __name__ == "__main__":
    main()
