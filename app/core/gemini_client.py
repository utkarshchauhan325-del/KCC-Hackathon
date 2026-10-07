import time
import logging
from pathlib import Path
from typing import Optional, Union, Type, TypeVar, List
from pydantic import BaseModel
from google import genai
from google.genai import types

from app.config import settings
from app.core.prompts import (
    SYSTEM_CONTEXT,
    INFRA_PROMPT,
    VIOLATOR_PROMPT,
    SEWER_PROMPT,
    GARBAGE_FRAME_DETECTION_PROMPT,
)
from app.core.schemas import (
    InfraAnalysisResponse,
    ViolatorAnalysisResponse,
    SewerAssessment,
    GarbageDetectionResponse,
    GarbageObjectDetection,
)

logger = logging.getLogger("civiceye.gemini_client")
logging.basicConfig(level=settings.LOG_LEVEL)

T = TypeVar("T", bound=BaseModel)

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-flash-latest",
]

class GeminiVideoClient:
    """Resilient wrapper around google-genai SDK with automated model fallback and retries."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.primary_model = model or settings.GEMINI_MODEL
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. API calls will fail until configured.")
        self.client = genai.Client(api_key=self.api_key)

    def upload_video(self, file_path: Union[str, Path], poll_interval: int = 3, max_wait_seconds: int = 300) -> types.File:
        """Upload video file to Gemini Files API and poll until state is ACTIVE."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Video file not found at: {path}")

        logger.info(f"Uploading {path.name} ({path.stat().st_size / (1024*1024):.2f} MB) to Gemini Files API...")
        file_ref = self.client.files.upload(file=str(path))
        logger.info(f"Uploaded file name: {file_ref.name}, initial state: {file_ref.state}")

        start_time = time.time()
        while file_ref.state.name == "PROCESSING" or file_ref.state == "PROCESSING":
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(f"Video processing timed out after {max_wait_seconds}s for {file_ref.name}")
            logger.debug(f"File state is still PROCESSING. Waiting {poll_interval}s...")
            time.sleep(poll_interval)
            file_ref = self.client.files.get(name=file_ref.name)

        if file_ref.state.name != "ACTIVE" and file_ref.state != "ACTIVE":
            raise RuntimeError(f"File {file_ref.name} reached invalid state: {file_ref.state}")

        logger.info(f"File {file_ref.name} is ACTIVE and ready for inference.")
        return file_ref

    def delete_file(self, file_name: str) -> None:
        """Delete file from Gemini Files API after processing."""
        try:
            self.client.files.delete(name=file_name)
            logger.info(f"Successfully cleaned up Gemini file: {file_name}")
        except Exception as e:
            logger.warning(f"Failed to delete Gemini file {file_name}: {e}")

    def _call_with_retry_and_fallback(
        self,
        contents: list,
        response_schema: Type[T],
        temperature: float = 0.1,
    ) -> T:
        """Execute generate_content with retries and fallback to alternate models on 503."""
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_CONTEXT,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        candidate_models = [self.primary_model]
        for m in FALLBACK_MODELS:
            if m not in candidate_models:
                candidate_models.append(m)

        last_error = None
        for model_name in candidate_models:
            logger.info(f"Attempting inference using model: {model_name}")
            for attempt in range(1, 4):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config
                    )
                    if response.parsed:
                        logger.info(f"Inference succeeded with {model_name}")
                        return response.parsed
                    if response.text:
                        logger.info(f"Inference succeeded with {model_name}")
                        return response_schema.model_validate_json(response.text)
                    raise ValueError("Empty response received from Gemini model.")
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    logger.warning(f"Attempt {attempt}/3 on {model_name} failed: {err_str[:120]}...")
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        # 503 high demand: short pause and retry, or fall back to next model
                        time.sleep(attempt * 2.0)
                    elif "404" in err_str or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        # Skip immediately to next model if model not found or quota exhausted
                        break
                    else:
                        time.sleep(2.0)

        raise RuntimeError(f"All candidate models failed. Last error: {last_error}")

    def analyze_infrastructure(self, video_file: types.File) -> InfraAnalysisResponse:
        """Pass A: Detect infrastructure issues (drainage, garbage, road damage)."""
        logger.info("Executing Pass A: Infrastructure Analysis...")
        contents = [video_file, INFRA_PROMPT]
        return self._call_with_retry_and_fallback(contents, InfraAnalysisResponse)

    def analyze_violators(self, video_file: types.File) -> ViolatorAnalysisResponse:
        """Pass B: Detect dumping/littering violators and vehicle information."""
        logger.info("Executing Pass B: Violator Detection...")
        contents = [video_file, VIOLATOR_PROMPT]
        return self._call_with_retry_and_fallback(contents, ViolatorAnalysisResponse)

    def assess_sewer_point(self, video_file: types.File, timestamp_str: str) -> SewerAssessment:
        """Pass C: Detailed assessment for a specific drain/sewer location."""
        logger.info(f"Executing Pass C: Sewer Assessment at {timestamp_str}...")
        prompt = SEWER_PROMPT.format(timestamp=timestamp_str)
        contents = [video_file, prompt]
        return self._call_with_retry_and_fallback(contents, SewerAssessment)

    def detect_garbage_frame(
        self,
        frame: Any,
        confidence_threshold: float = 0.70,
    ) -> GarbageDetectionResponse:
        """Frame-level semantic garbage detection distinguishing waste from drains, roads, and background."""
        import cv2
        import numpy as np

        if not isinstance(frame, np.ndarray) or frame.size == 0:
            return GarbageDetectionResponse(objects=[])

        h, w = frame.shape[:2]
        # Optimize frame size for network latency if larger than 720p
        max_dim = max(h, w)
        if max_dim > 720:
            scale = 720.0 / max_dim
            proc_frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        else:
            proc_frame = frame

        success, buf = cv2.imencode(".jpg", proc_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            logger.warning("Failed to encode frame to JPEG for Gemini.")
            return GarbageDetectionResponse(objects=[])

        jpg_bytes = buf.tobytes()
        part = types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg")
        contents = [part, GARBAGE_FRAME_DETECTION_PROMPT]

        try:
            logger.info("Calling Gemini for frame-level garbage detection & classification...")
            raw_resp = self._call_with_retry_and_fallback(
                contents=contents,
                response_schema=GarbageDetectionResponse,
                temperature=0.1,
            )
            # Filter strictly by confidence threshold and class
            valid_objects: List[GarbageObjectDetection] = []
            for obj in raw_resp.objects:
                c_name = getattr(obj, "class_name", "") or getattr(obj, "class", "")
                if str(c_name).lower() == "garbage" and obj.confidence >= confidence_threshold:
                    valid_objects.append(obj)
                else:
                    logger.debug(
                        f"Discarded detection {c_name} (conf={obj.confidence:.2f}) "
                        f"below threshold {confidence_threshold}"
                    )
            return GarbageDetectionResponse(objects=valid_objects)
        except Exception as e:
            logger.warning(f"Frame-level Gemini garbage detection failed or skipped: {e}")
            return GarbageDetectionResponse(objects=[])

