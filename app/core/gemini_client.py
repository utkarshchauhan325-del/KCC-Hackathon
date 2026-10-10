import time
import logging
from pathlib import Path
from typing import Optional, Union, Type, TypeVar, List
from pydantic import BaseModel
from google import genai
from google.genai import types

from app.config import settings
from app.core.prompts import SYSTEM_CONTEXT, INFRA_PROMPT, VIOLATOR_PROMPT, SEWER_PROMPT, GARBAGE_EXEMPLAR_PROMPT, PLATE_ANALYSIS_PROMPT
from app.core.schemas import InfraAnalysisResponse, ViolatorAnalysisResponse, SewerAssessment, GarbageExemplarResponse, PlateAnalysisResponse

logger = logging.getLogger("civiceye.gemini_client")
logging.basicConfig(level=settings.LOG_LEVEL)

T = TypeVar("T", bound=BaseModel)

# Tried in order after GEMINI_MODEL. Free-tier quota is per model (20 requests/day), so a
# 429 on one model moves straight to the next.
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
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

    def locate_garbage(self, jpeg_frames: List[bytes]) -> GarbageExemplarResponse:
        """Box garbage regions on still frames; the boxes become visual prompts for the local detector."""
        logger.info(f"Locating garbage exemplars on {len(jpeg_frames)} frames...")
        contents: list = []
        for i, jpeg in enumerate(jpeg_frames, start=1):
            contents.append(f"Image {i}:")
            contents.append(types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"))
        contents.append(GARBAGE_EXEMPLAR_PROMPT.format(n=len(jpeg_frames)))
        return self._call_with_retry_and_fallback(contents, GarbageExemplarResponse)

    def analyze_plate_image(self, plate_jpeg: bytes) -> PlateAnalysisResponse:
        """Pass B helper: fine-grained VLM inspection of cropped license plate image."""
        logger.info("Executing fine-grained license plate visual analysis...")
        contents = [
            types.Part.from_bytes(data=plate_jpeg, mime_type="image/jpeg"),
            PLATE_ANALYSIS_PROMPT
        ]
        return self._call_with_retry_and_fallback(contents, PlateAnalysisResponse)

