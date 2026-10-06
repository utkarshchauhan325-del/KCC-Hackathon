#!/usr/bin/env python3
"""CLI utility to analyze a video clip using CivicEye Gemini VLM pipeline."""

import sys
import argparse
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.gemini_client import GeminiVideoClient
from app.core.scoring import compute_sewer_score

def main():
    parser = argparse.ArgumentParser(description="CivicEye CLI: Analyze video for civic issues using Gemini VLM.")
    parser.add_argument("video_path", type=str, help="Path to video file (.mp4, .mov, .webm)")
    parser.add_argument("--pass-b", action="store_true", help="Run Pass B (Violator detection) in addition to Pass A")
    parser.add_argument("--pass-c", action="store_true", help="Run Pass C (Sewer overflow assessment) on detected drains")
    parser.add_argument("--keep-remote-file", action="store_true", help="Do not delete uploaded file from Gemini Files API")
    args = parser.parse_args()

    video_file = Path(args.video_path)
    if not video_file.is_file():
        print(f"Error: Video file not found: {video_file}", file=sys.stderr)
        sys.exit(1)

    key = settings.GEMINI_API_KEY.strip()
    if not key or key == "your_gemini_api_key_here":
        print("Error: Valid GEMINI_API_KEY is required to contact Gemini API.", file=sys.stderr)
        print("Please configure GEMINI_API_KEY in your .env file or export GEMINI_API_KEY in your shell.", file=sys.stderr)
        sys.exit(1)

    print(f"--- CivicEye Video Analysis CLI ---")
    print(f"Target Video: {video_file.name} ({video_file.stat().st_size / (1024*1024):.2f} MB)")
    print(f"Gemini Model: {settings.GEMINI_MODEL}")

    client = GeminiVideoClient()
    uploaded_file = None
    try:
        uploaded_file = client.upload_video(video_file)
        print(f"Upload complete. Gemini File ID: {uploaded_file.name}")

        # Pass A: Infrastructure issues
        print("\n=== Pass A: Infrastructure Analysis ===")
        infra_result = client.analyze_infrastructure(uploaded_file)
        print(json.dumps(infra_result.model_dump(), indent=2))

        # Pass B (Optional): Violator detection
        if args.pass_b:
            print("\n=== Pass B: Violator Detection ===")
            violator_result = client.analyze_violators(uploaded_file)
            print(json.dumps(violator_result.model_dump(), indent=2))

        # Pass C (Optional or automatic on drainage issues)
        if args.pass_c:
            print("\n=== Pass C: Sewer Assessment & Deterministic Risk Scoring ===")
            drain_issues = [i for i in infra_result.issues if i.category == "drainage"]
            if not drain_issues:
                print("No drainage issues detected in Pass A for Pass C evaluation.")
            for issue in drain_issues:
                print(f"\nAssessing drain issue '{issue.subtype}' at {issue.best_frame_ts}...")
                sewer_result = client.assess_sewer_point(uploaded_file, issue.best_frame_ts)
                print("Raw VLM Observations:")
                print(json.dumps(sewer_result.model_dump(), indent=2))

                score, band, breakdown = compute_sewer_score(sewer_result)
                print(f"\n>>> DETERMINISTIC SEWER OVERFLOW SCORE: {score}/100 [{band.upper()} RISK] <<<")
                print("Score Breakdown:")
                print(json.dumps(breakdown, indent=2))

    except Exception as e:
        print(f"\nExecution failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if uploaded_file and not args.keep_remote_file:
            print(f"\nCleaning up uploaded file {uploaded_file.name} from Gemini Files API...")
            client.delete_file(uploaded_file.name)

if __name__ == "__main__":
    main()
