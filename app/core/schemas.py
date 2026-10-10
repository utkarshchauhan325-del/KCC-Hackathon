from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class BBox(BaseModel):
    """Bounding box normalized to 0-1000 range: [ymin, xmin, ymax, xmax]."""
    ymin: int = Field(..., ge=0, le=1000)
    xmin: int = Field(..., ge=0, le=1000)
    ymax: int = Field(..., ge=0, le=1000)
    xmax: int = Field(..., ge=0, le=1000)

class InfraIssue(BaseModel):
    """Single detected infrastructure issue (Pass A)."""
    category: Literal["garbage", "drainage", "road", "other"]
    subtype: str = Field(..., description="e.g. dump_pile, open_manhole, pothole, blocked_drain")
    severity: int = Field(..., ge=1, le=5, description="Severity rating 1 (minor) to 5 (critical hazard)")
    start_ts: str = Field(..., description="Start timestamp MM:SS")
    end_ts: str = Field(..., description="End timestamp MM:SS")
    best_frame_ts: str = Field(..., description="Timestamp MM:SS with the clearest view for still frame extraction")
    box: BBox = Field(..., description="Bounding box on the best frame")
    description: str = Field(..., description="One-sentence description of the issue")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")

class InfraAnalysisResponse(BaseModel):
    """Structured response container for Pass A."""
    issues: List[InfraIssue] = Field(default_factory=list)

class ViolatorEvent(BaseModel):
    """Detected garbage dumping / littering violation (Pass B)."""
    act_ts: str = Field(..., description="Timestamp MM:SS when dumping occurs")
    best_frame_ts: str = Field(..., description="Timestamp MM:SS with best frame evidence")
    person_box: Optional[BBox] = None
    garbage_box: Optional[BBox] = None
    vehicle_box: Optional[BBox] = None
    vehicle_type: Optional[str] = Field(default=None, description="e.g. two-wheeler, auto-rickshaw, car, truck, handcart")
    plate_text: Optional[str] = Field(default=None, description="Exact number plate text or null if unreadable")
    plate_box: Optional[BBox] = None
    plate_legibility: Literal["clear", "partial", "unreadable", "none"] = Field(default="none")
    description: str = Field(..., description="Factual description of the act (clothing color, object thrown)")
    confidence: float = Field(..., ge=0.0, le=1.0)

class ViolatorAnalysisResponse(BaseModel):
    """Structured response container for Pass B."""
    events: List[ViolatorEvent] = Field(default_factory=list)

class PlateAnalysisResponse(BaseModel):
    """Fine-grained VLM analysis of cropped license plate image."""
    plate_text: Optional[str] = Field(default=None, description="Exact plate registration text e.g. MH 12 AB 1234 or null if unreadable")
    legibility: Literal["clear", "partial", "unreadable", "none"] = Field(default="none")
    vehicle_type: Optional[str] = Field(default=None, description="Inferred vehicle category e.g. car, motorcycle, truck")
    state: Optional[str] = Field(default=None, description="State abbreviation or name")
    description: Optional[str] = Field(default=None, description="Short visual description of what is written on the plate")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class SewerAssessment(BaseModel):
    """Detailed assessment for drain/manhole locations (Pass C)."""
    water_level: Literal["none", "damp", "pooling", "flowing_over", "gushing"]
    water_reaching_road: bool
    trash_inside: Literal["none", "light", "moderate", "heavy", "fully_blocked"]
    trash_near: Literal["none", "light", "moderate", "heavy"]
    grating_covered: bool
    cover_missing_or_broken: bool
    wet_conditions: bool
    hazards: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

WasteType = Literal["dry_plastic", "dry_paper", "wet_organic", "construction", "e_waste", "mixed"]

class GarbageRegion(BaseModel):
    """One garbage region on a still frame, used as a visual prompt for the local detector."""
    box: BBox
    waste_type: WasteType

class GarbageExemplarFrame(BaseModel):
    image_index: int = Field(..., ge=1, description="1-based index of the image in the request")
    regions: List[GarbageRegion] = Field(default_factory=list)

class GarbageExemplarResponse(BaseModel):
    """Garbage regions Gemini located on sampled frames."""
    frames: List[GarbageExemplarFrame] = Field(default_factory=list)
