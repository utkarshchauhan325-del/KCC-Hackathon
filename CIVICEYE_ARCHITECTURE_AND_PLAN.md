# CivicEye: AI Civic Issue Detection from Video

> **Historical document.** This is the original build brief written before the project was built. The system as built differs in places (local YOLOE detector, garbage measured as area, Streamlit only, no FastAPI yet). For the current design see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); for status and next steps see [docs/PLAN.md](docs/PLAN.md).

> Hand this file to Antigravity as the project brief. Build phase by phase (Section 12). Do not skip ahead.

## 1. Goal

Upload a street or drone video. A Vision-Language Model (Gemini API) analyses it with a fixed, in-code context prompt and detects:

1. **Sewer / drainage issues**: open or broken manholes, overflowing sewer, blocked drains, standing wastewater.
2. **Garbage issues**: dumps, overflowing bins, scattered litter, burning waste.
3. **Other road issues**: potholes, broken road edge, waterlogging, missing manhole covers, stray debris blocking road.
4. **Littering/dumping violations**: a person dumping garbage, with a cropped photo and vehicle number plate (if a vehicle is involved).
5. **Sewer Overflow Risk Score (0-100)** per drain/manhole, computed from the water state at the drain plus nearby and inside trash.

Detected issues are turned into **incident reports** with evidence and sent to the municipal corporation. Violator reports go through a human review step before dispatch (see Section 9).

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Best SDK and CV support |
| VLM | Gemini via `google-genai` SDK | Native video understanding, structured JSON output, bounding boxes |
| Backend API | FastAPI + Uvicorn | Async, easy file upload, auto docs |
| Video / image | OpenCV (`opencv-python`), `ffmpeg` | Frame extraction, cropping, annotated evidence |
| Database | SQLite (dev), PostgreSQL (prod) via SQLAlchemy | Incidents, evidence, alert logs |
| Task queue | FastAPI `BackgroundTasks` (MVP), Celery + Redis (later) | Video analysis is slow |
| Dashboard | Streamlit (MVP) or React + Leaflet later | Upload, review queue, map |
| Alerts | SMTP email, Telegram bot, generic webhook | Pluggable `Notifier` interface |
| Plate OCR | Gemini on cropped plate image, EasyOCR as fallback | Cheap cross-check |
| Config | `.env` + `pydantic-settings` | Keys never in code |
| Tests | pytest | Schema and scoring tests |

Model name goes in config (`GEMINI_MODEL`, default `gemini-2.5-flash`). Verify the current model name in the Gemini docs before building; use a Pro-class model for the hard "violator + plate" pass if Flash accuracy is poor.

## 3. High-Level Architecture

```
 ┌────────────┐   video + GPS/time    ┌──────────────────────┐
 │ Dashboard  │ ───────────────────▶ │   FastAPI backend    │
 │ (Streamlit)│ ◀─────────────────── │  /upload /jobs /...  │
 └────────────┘   status, reports     └──────────┬───────────┘
                                                 │ create job
                                       ┌─────────▼──────────┐
                                       │  Job Orchestrator  │
                                       └─────────┬──────────┘
         ┌──────────────────────┬────────────────┼───────────────────┐
         ▼                      ▼                ▼                   ▼
 ┌───────────────┐   ┌───────────────────┐ ┌───────────────┐ ┌────────────────┐
 │ Video Ingest  │   │  Gemini Analyzer  │ │ Evidence      │ │ Scoring Engine │
 │ validate,     │──▶│  Pass A: issues   │▶│ Extractor     │ │ sewer overflow │
 │ chunk, upload │   │  Pass B: people & │ │ frames, crops,│ │ score 0-100    │
 │ to Files API  │   │  vehicles         │ │ plate crops   │ └───────┬────────┘
 └───────────────┘   │  Pass C: sewer    │ └───────┬───────┘         │
                     └───────────────────┘         │                 │
                                          ┌────────▼─────────────────▼───┐
                                          │  Incident Builder + Dedupe   │
                                          └────────┬─────────────────────┘
                                                   ▼
                                  ┌────────────────────────────────┐
                                  │ DB (jobs, incidents, evidence, │
                                  │ violators, alerts)             │
                                  └────────┬───────────────────────┘
                              ┌────────────┴─────────────┐
                              ▼                          ▼
                    ┌──────────────────┐      ┌─────────────────────┐
                    │ Review Queue (UI)│─────▶│ Notifier (email/    │
                    │ human approve    │      │ Telegram/webhook)   │
                    └──────────────────┘      └─────────────────────┘
```

### Why three Gemini passes instead of one

One giant prompt gives vague, inconsistent output. Splitting keeps each prompt focused and each JSON schema small:

- **Pass A, Infrastructure issues**: garbage, drainage, road damage.
- **Pass B, Violators**: people dumping or littering, plus vehicle and plate.
- **Pass C, Sewer overflow**: only runs on drain/manhole events found in Pass A.

## 4. Project Structure

```
civiceye/
├── AGENTS.md                  # Antigravity rules (Section 13)
├── README.md
├── pyproject.toml
├── .env.example
├── app/
│   ├── main.py                # FastAPI entry
│   ├── config.py              # pydantic-settings
│   ├── api/
│   │   ├── routes_upload.py
│   │   ├── routes_jobs.py
│   │   ├── routes_incidents.py
│   │   └── routes_review.py
│   ├── core/
│   │   ├── video_ingest.py    # validate, probe, chunk, upload to Files API
│   │   ├── gemini_client.py   # wrapper, retries, JSON parse, rate limits
│   │   ├── prompts.py         # ALL context prompts live here (Section 6)
│   │   ├── schemas.py         # Pydantic models = Gemini response schemas
│   │   ├── analyzers/
│   │   │   ├── infra_analyzer.py      # Pass A
│   │   │   ├── violator_analyzer.py   # Pass B
│   │   │   └── sewer_analyzer.py      # Pass C
│   │   ├── evidence.py        # frame grab, bbox crop, annotation
│   │   ├── scoring.py         # sewer overflow score
│   │   ├── dedupe.py          # merge repeated sightings
│   │   ├── geo.py             # GPS from user / video metadata / SRT
│   │   └── pipeline.py        # orchestrates everything
│   ├── notify/
│   │   ├── base.py            # Notifier interface
│   │   ├── email_notifier.py
│   │   ├── telegram_notifier.py
│   │   └── webhook_notifier.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   └── ui/
│       └── dashboard.py       # Streamlit
├── data/
│   ├── uploads/
│   ├── evidence/              # crops, annotated frames (per incident)
│   └── reports/               # generated PDF/HTML reports
├── tests/
│   ├── test_scoring.py
│   ├── test_schemas.py
│   ├── test_dedupe.py
│   └── fixtures/              # short sample videos + golden JSON
└── scripts/
    └── analyze_video.py       # CLI: python scripts/analyze_video.py clip.mp4
```

## 5. Video Handling Details

- Accept `.mp4`, `.mov`, `.webm`. Max size configurable (e.g. 500 MB).
- Probe with `ffprobe`: duration, fps, resolution, any GPS metadata.
- **Chunking**: split into segments of ~60-120 s with ~5 s overlap, so long videos stay within limits and timestamps stay accurate. Keep the chunk offset so timestamps can be mapped back to the original video.
- Upload each chunk via the Gemini **Files API** and wait until the file state is `ACTIVE`.
- Sampling: default 1 FPS. Use a higher FPS (e.g. 3-5) for Pass B because dumping is a fast action. Use `video_metadata` (`fps`, `start_offset`, `end_offset`) in the request.
- Gemini returns timestamps as `MM:SS`. Convert to seconds, add the chunk offset, then pull the exact frame with OpenCV for evidence.
- Bounding boxes: ask for `box_2d` as `[ymin, xmin, ymax, xmax]` normalised to 0-1000 and scale to pixels on the extracted frame. Always clamp to image bounds.
- Delete uploaded Gemini files after processing.

### Location

The model cannot know where the video was shot. Resolve location in this order:

1. Per-video GPS (lat, lng) given by the uploader in the form.
2. GPX/SRT sidecar file (dashcam / drone) matched by timestamp.
3. EXIF/video metadata.
4. Landmark text the model can read from signboards (low confidence, flag as `location_source = "vlm_inferred"`).

Store `location_source` and `location_confidence` on every incident.

## 6. Context Prompts (in code, `prompts.py`)

The user wanted the context hard-coded. Put it in `prompts.py` as constants, not scattered in logic.

```python
SYSTEM_CONTEXT = """
You are CivicEye, an urban infrastructure inspector assisting an Indian municipal
corporation. You analyse street-level and drone video from Indian cities.
Be literal and evidence-based: report only what is visible. If unsure, lower the
confidence value instead of guessing. Never invent vehicle numbers: if a plate is
not legible, return null.
Indian context to remember: open nullahs/drains beside roads, manholes with missing
covers, roadside garbage dumping points (GVPs), mixed waste (plastic, food, debris,
construction waste), auto-rickshaws, two-wheelers, handcarts, and monsoon waterlogging.
"""

INFRA_PROMPT = """
Analyse this video. List every distinct issue in these categories:
- garbage: dump_pile, overflowing_bin, scattered_litter, burning_waste, construction_debris
- drainage: open_manhole, broken_manhole_cover, blocked_drain, sewer_overflow, stagnant_wastewater
- road: pothole, waterlogging, broken_edge, fallen_debris_blocking_road, missing_footpath_slab
- other: any other civic hazard (describe briefly)
For each: category, subtype, severity (1-5), start and end timestamp (MM:SS), the best
timestamp for a still frame, a bounding box on that frame, a one-sentence description,
and confidence 0-1. Merge repeated sightings of the same object across time into ONE entry.
"""

VIOLATOR_PROMPT = """
Find every instance of a person dumping, throwing or leaving garbage in a public place
(including from a vehicle, or from a shop/house onto the street). For each:
- timestamp when the act happens and the best frame timestamp
- bounding box of the person; bounding box of the garbage; bounding box of any vehicle
- vehicle type and the number plate text exactly as visible (null if not legible),
  with a plate bounding box and plate legibility (clear, partial, unreadable)
- short factual description of the act (what was thrown, how many items)
- confidence 0-1
Do NOT describe the person's identity, ethnicity, religion or any trait other than
clothing colour and apparent actions. Do not report people simply walking near garbage.
"""

SEWER_PROMPT = """
Look at the drain/manhole/sewer location at {timestamp}. Assess: water_level
(none, damp, pooling, flowing_over, gushing), whether the water is reaching the road,
trash_inside_drain (none, light, moderate, heavy, fully_blocked), trash_near_drain within
about 2 metres (none, light, moderate, heavy), whether drain inlet grating is covered,
whether the cover is missing/broken, whether it is raining or the road is wet,
and any visible hazards (open hole, children/vehicles nearby). Return the JSON schema only.
"""
```

Use `response_mime_type="application/json"` with `response_schema` set to the Pydantic models in `schemas.py`, `temperature=0.1`.

## 7. Data Schemas (`schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class BBox(BaseModel):
    ymin: int; xmin: int; ymax: int; xmax: int   # 0-1000 normalised

class InfraIssue(BaseModel):
    category: Literal["garbage", "drainage", "road", "other"]
    subtype: str
    severity: int = Field(ge=1, le=5)
    start_ts: str; end_ts: str; best_frame_ts: str   # "MM:SS"
    box: BBox
    description: str
    confidence: float = Field(ge=0, le=1)

class ViolatorEvent(BaseModel):
    act_ts: str; best_frame_ts: str
    person_box: Optional[BBox]
    garbage_box: Optional[BBox]
    vehicle_box: Optional[BBox]
    vehicle_type: Optional[str]
    plate_text: Optional[str]
    plate_box: Optional[BBox]
    plate_legibility: Literal["clear", "partial", "unreadable", "none"]
    description: str
    confidence: float = Field(ge=0, le=1)

class SewerAssessment(BaseModel):
    water_level: Literal["none", "damp", "pooling", "flowing_over", "gushing"]
    water_reaching_road: bool
    trash_inside: Literal["none", "light", "moderate", "heavy", "fully_blocked"]
    trash_near: Literal["none", "light", "moderate", "heavy"]
    grating_covered: bool
    cover_missing_or_broken: bool
    wet_conditions: bool
    hazards: list[str]
    confidence: float = Field(ge=0, le=1)
```

## 8. Sewer Overflow Score (`scoring.py`)

Deterministic and testable. The VLM supplies **categorical observations**; Python computes the number, so the score is explainable and tunable.

```
score = 100 * ( 0.35 * water
              + 0.25 * trash_inside
              + 0.15 * trash_near
              + 0.10 * inlet_blocked
              + 0.10 * hazard
              + 0.05 * wet_conditions )
```

Lookup values (0-1):

| Factor | Mapping |
|---|---|
| water | none 0, damp 0.2, pooling 0.5, flowing_over 0.85, gushing 1.0 |
| trash_inside | none 0, light 0.25, moderate 0.55, heavy 0.85, fully_blocked 1.0 |
| trash_near | none 0, light 0.25, moderate 0.6, heavy 1.0 |
| inlet_blocked | grating_covered = 1 else 0 |
| hazard | 1 if cover missing/broken or water reaches road, else 0 |
| wet_conditions | 1 / 0 |

Override rule: if `water_level` is `flowing_over` or `gushing`, floor the score at 70.

Bands: **0-29 Low**, **30-59 Watch**, **60-79 High**, **80-100 Critical**. Critical and High trigger an immediate alert; others go to the daily digest.

Weights live in `config.py` so the municipal team can tune them. Write `test_scoring.py` with at least 8 cases, including both extremes and the override.

Return the score together with a `breakdown` dict showing each factor's contribution, and put it in the report.

## 9. Violator Detection: Evidence and Safeguards

This is the sensitive part. It captures people's images and vehicle numbers and sends them to a government body. Build these in from the start, not later:

1. **Human review before dispatch.** Violator reports are created as `pending_review`. A municipal officer or operator approves in the dashboard before anything leaves the system. Infrastructure issues (garbage, drains, potholes) may auto-send.
2. **Confidence gates.** Only queue violator events where `confidence >= 0.7`. A plate is accepted only if `plate_legibility == "clear"` and the text matches the Indian format regex below. Otherwise store "plate unreadable" and still send the event with the vehicle crop.
3. **Plate validation.** `^[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4}$` (also allow BH-series `^\d{2}BH\d{4}[A-Z]{1,2}$`). Cross-check by running a second OCR (EasyOCR) on the plate crop. Mismatch means flag for manual review.
4. **Show the full act, not just a face.** The evidence package is: the clip (±5 s around the act), the annotated frame, the person crop, the garbage crop, the vehicle crop, and the plate crop. A single photo with no context is not good evidence and invites wrongful accusation.
5. **Authority sends the notice, not the app.** The system sends evidence and the plate number to the corporation. Fines and notices are issued by the corporation after verification, via the registered owner lookup that only they can do.
6. **Data protection.** Follow India's DPDP Act, 2023: collect only what the purpose needs, restrict access by role, keep an audit log of who viewed or approved what, encrypt evidence at rest, and delete crops of non-violations and rejected events within a short retention window (default 30 days; configurable). Do not store faces of bystanders; blur anyone who is not the flagged person in exported evidence.
7. **No identity inference.** The prompt forbids describing anything beyond clothing and actions. Never attempt face recognition or matching against any database.
8. **Reviewer can reject or edit.** Rejected events are deleted on schedule and used only as negative examples for prompt tuning.

Have the corporation's legal team confirm the evidence format and retention period before any real deployment.

## 10. Database Models

- `Job(id, filename, status, created_at, source_gps, error)`
- `Incident(id, job_id, type, subtype, severity, lat, lng, location_source, video_ts, description, confidence, status[new|sent|acknowledged|resolved|rejected], dedupe_key)`
- `Evidence(id, incident_id, kind[frame|annotated|crop_person|crop_vehicle|crop_plate|clip], path)`
- `Violation(id, incident_id, plate_text, plate_valid, plate_legibility, vehicle_type, review_status[pending_review|approved|rejected], reviewed_by, reviewed_at)`
- `SewerScore(id, incident_id, score, band, breakdown_json, raw_assessment_json)`
- `AlertLog(id, incident_id, channel, recipient, sent_at, status, response)`
- `AuditLog(id, user, action, entity, entity_id, at)`

### Deduplication

Two incidents are the same if they have the same category and subtype, are within ~15 m (when GPS is available) or within a 10 s window in the same job, and their bounding boxes overlap (IoU > 0.4). Keep the highest-confidence sighting and attach the others as supporting evidence. Across different uploads of the same street, use a geohash plus type within 24 hours.

## 11. Notifications

`Notifier` interface: `send(report: Report) -> DeliveryResult`.

- **Email**: HTML report with summary, map link, inline evidence images, and severity.
- **Telegram / WhatsApp Business**: short alert with image and map pin.
- **Webhook**: JSON POST so the corporation's existing complaint system (ward control rooms, helpline portals) can ingest it. Keep the payload schema versioned.
- Routing: map incident lat/lng to a **ward / department** (Solid Waste Management, Storm Water Drains, Roads). For the MVP, a `wards.json` with polygons or a manual dropdown is enough.
- Each report contains: incident ID, category, severity, score and band (if sewer), location with map link, timestamp, description, evidence images, and for violations the approved plate number.
- Retry with exponential backoff; log every attempt in `AlertLog`. Throttle repeat alerts for the same incident.

## 12. Build Plan (Phases)

Each phase ends with a demoable result and passing tests. Antigravity should produce an implementation plan artifact and wait for approval at the end of every phase.

**Phase 0: Setup (0.5 day)**
Repo, `pyproject.toml`, `.env.example` (`GEMINI_API_KEY`, `GEMINI_MODEL`, SMTP and Telegram values), folder skeleton, `config.py`, logging.

**Phase 1: Gemini wrapper + CLI spike (1 day)**
`gemini_client.py` with Files API upload, wait-for-active, retries, JSON-schema output. `scripts/analyze_video.py clip.mp4` prints Pass A JSON. Test with 3 short real clips.

**Phase 2: Infrastructure issues pipeline (1-2 days)**
Chunking, timestamp mapping, bbox scaling, frame extraction, annotated images, DB models, dedupe. Output: incidents with evidence in the DB.

**Phase 3: Sewer overflow (1 day)**
Pass C triggered on drain events, `scoring.py` plus tests, score breakdown stored.

**Phase 4: Violator detection (2 days)**
Pass B at higher FPS, crops, plate validation, second OCR, `pending_review` flow, evidence clip export, blurring of bystanders.

**Phase 5: API + Dashboard (2 days)**
Upload form (with GPS and datetime), job status, incident table, map, evidence viewer, review queue with approve/reject, audit log.

**Phase 6: Alerts (1-2 days)**
Notifier implementations, ward routing, retries, report template.

**Phase 7: Hardening (2 days)**
Background queue (Celery + Redis), cost and rate-limit controls, retention job, Dockerfile and docker-compose, end-to-end tests, evaluation set.

**Phase 8: Later**
Live RTSP/dashcam streams, mobile upload app, repeat-offender analytics (plate seen N times), heatmaps of garbage hotspots, monsoon-season drain risk dashboard, integration with the corporation's grievance portal.

## 13. Antigravity Instructions (`AGENTS.md`)

```
# AGENTS.md
- Language: Python 3.11, type hints everywhere, Pydantic v2.
- Never hard-code API keys. Read from environment via app/config.py.
- All prompts live in app/core/prompts.py. All Gemini response schemas live in app/core/schemas.py.
- Every Gemini call goes through app/core/gemini_client.py (retries, timeouts, JSON validation).
- Scoring is deterministic Python in app/core/scoring.py. The VLM must not output the score.
- Violator events must default to review_status = pending_review. Never auto-send them.
- Write or update tests for every new module. Run pytest before finishing a phase.
- Work one phase at a time from CIVICEYE_ARCHITECTURE_AND_PLAN.md; produce a plan artifact first,
  and a walkthrough with screenshots or sample output when done.
- Use the browser agent to verify the Streamlit dashboard actually loads and the upload flow works.
```

Suggested way to use it in Antigravity: open the empty project folder, place this file and `AGENTS.md` in the root, then in Agent Manager start with: *"Read CIVICEYE_ARCHITECTURE_AND_PLAN.md. Execute Phase 0 and Phase 1 only. Show me the plan first."* Run Phase 4 with a separate agent only after Phase 2 is merged, so work does not collide.

## 14. Evaluation and Quality

- Build a labelled set of 30-50 short clips (garbage, open drains, potholes, dumping events, clean streets). Compute precision and recall per category, plate-read accuracy, and false-positive rate on clean footage.
- Track cost per minute of video and latency. Keep a `--dry-run` mode and a per-job spend cap.
- Known weak spots: night footage, motion blur at high speed, small plates at distance, and rain on the lens. Surface a `video_quality` warning rather than guessing.
- Prompt-tune using rejected events from the review queue.

## 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| VLM hallucinated plate | Legibility gate, regex, second OCR, human review |
| Wrongly accusing someone | Full-context evidence, review step, authority issues notice |
| False sewer alarms | Score from categorical facts, thresholds tuned on the eval set |
| Wrong location | Source and confidence stored, manual correction in dashboard |
| API cost on long videos | Chunking, lower FPS for Pass A, caching, spend cap |
| Privacy complaints | DPDP-aligned retention, access roles, bystander blurring, audit log |
| Gemini rate limits | Queue plus backoff, one concurrent job at first |

## 16. MVP Definition of Done

- Upload a video, plus GPS, in the dashboard.
- Within a few minutes see a list of issues on a map, each with a frame, bounding box, severity, and description.
- Each drain issue shows a sewer overflow score with a breakdown.
- Dumping events appear in a review queue with the clip, crops, and plate.
- Approving an item sends a formatted report to the configured email or Telegram.
- All tests pass and the app runs with `docker compose up`.
