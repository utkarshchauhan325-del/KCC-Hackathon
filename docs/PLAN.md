# Plan

Where the project stands against the original build brief ([`CIVICEYE_ARCHITECTURE_AND_PLAN.md`](../CIVICEYE_ARCHITECTURE_AND_PLAN.md)), and what to do next, in priority order.

Status as of 8 October 2026, branch `utkarsh`.

---

## 1. Status against the original phases

| Phase | Original goal | Status | Notes |
|---|---|---|---|
| 0. Setup | Repo, config, `.env`, logging | **Done** | Editable install fixed; storage paths resolve against the project root |
| 1. Gemini wrapper + CLI | Files API upload, retries, JSON schemas, CLI | **Done** | `scripts/analyze_video.py`; model fallback chain for free-tier limits |
| 2. Infrastructure pipeline | Frames, boxes, evidence, DB, de-duplication | **Done** | Fake fallback detections removed |
| 3. Sewer overflow score | Pass C + deterministic score | **Done** | Per-drain score with breakdown |
| 4. Violator detection | Crops, plate validation, review flow, face blur | **Mostly done** | Person, vehicle and plate crops; Indian plate regex; `pending_review`; bystander blur. Missing: second OCR check, evidence clip export |
| 5. API + dashboard | Upload, status, incidents, map, review queue | **Dashboard done, API not built** | Streamlit dashboard redesigned; `app/api/` is empty (no FastAPI endpoints) |
| 6. Alerts | Email, Telegram, webhook, routing | **Done except routing** | All three channels with logging; no per-ward routing; not yet tested against live credentials |
| 7. Hardening | Queue, rate limits, retention, Docker, end-to-end tests, evaluation set | **Not started** | 66 unit and integration tests exist; no Docker, queue, retention or evaluation set |
| 8. Later | Live streams, mobile upload, repeat offenders, heatmaps | **Not started** | |

**Added beyond the brief:**
- Local per-frame segmentation and tracking (YOLOE + BoT-SORT).
- Garbage taught per video from Gemini's boxes, measured as area, and sorted by waste stream.
- An honest evidence video and scores.
- A redesigned front end.

## 2. Definition of done (MVP) check

| Requirement | Met? |
|---|---|
| Upload a video, plus GPS, in the dashboard | Yes |
| See a list of issues within a few minutes, each with frame, box, severity, description | Yes (about 2 minutes for an 11-second clip on CPU) |
| See issues on a map | **No**: the map shows seed locations, not pipeline incidents |
| Each drain issue shows a sewer overflow score with a breakdown | Yes (stored; shown as the drainage score) |
| Dumping events appear in a review queue with crops and plate | Yes (no video clip export yet) |
| Approving sends a formatted report by email or Telegram | Built and unit-tested; not yet tried with real credentials |
| All tests pass | Yes, 66 passing |
| Runs with `docker compose up` | **No** |

---

## 3. Next steps

Ordered by value to a real municipal pilot, cheapest first within each group.

### P0: Before anyone relies on the output

1. **Build an evaluation set.** Collect 30-50 short clips: garbage, open drains, potholes, dumping events and clean streets, from both fixed CCTV and phones. Label them, then measure precision and recall per category, plate-read accuracy, and false alerts on clean footage. Only one real clip has been analysed so far.
2. **Configure and test one alert channel end to end.** A Telegram bot is the quickest. Then click through approve and reject on a real violation in the redesigned UI.
3. **Fix the TomTom SSL failure** ([Problem 17](PROBLEMS_AND_FIXES.md#17-tomtom-traffic-requests-fail-with-an-ssl-error-open)): use `truststore` so the OS certificate store is used, and switch WeatherAPI to `https://`.
4. **Gemini quota.** Move to a paid key, or cache Gemini responses per video hash so re-renders and retries cost nothing. Each video uses about 5 requests and the free tier allows 20 per model per day.

### P1: Detection quality

5. **Persist the garbage examples** (`exemplars.json` per job) so a video can be re-rendered without new Gemini calls.
6. **Water and garbage overlap** ([Problem 24](PROBLEMS_AND_FIXES.md#24-water-masks-spill-over-garbage-open)): where a garbage mask and a water mask overlap, count the overlap as garbage, or add Gemini examples for water.
7. **Refresh garbage examples when the scene changes**, for example when frame similarity to all keyframes drops, instead of a fixed 4 keyframes.
8. **People re-identification** ([Problem 21](PROBLEMS_AND_FIXES.md#21-one-person-many-track-ids)): plug a small dedicated ReID model into BoT-SORT to cut ID switches on handheld footage.
9. **Waste-stream sorting** ([Problem 23](PROBLEMS_AND_FIXES.md#23-geminis-garbage-boxes-are-coarse-open)): prompt Gemini to split heaps by stream more aggressively, and check the result on clips with sorted waste.
10. **Fine-tune a detector** on Indian street garbage once the evaluation set exists. Open datasets (TACO, garbage-in-water sets) plus labelled municipal footage would remove the per-video dependency on Gemini examples.
11. **Plate second check**: run a dedicated OCR on the plate crop and flag disagreements with Gemini's reading.

### P2: Product

12. **Show pipeline incidents on the risk map**, using job GPS, instead of only seed locations.
13. **FastAPI layer** (`app/api/`): upload, job status, incidents and review endpoints, so the corporation's systems and a mobile app can use it.
14. **Background jobs**: analysis currently runs inside the Streamlit request. Move it to a worker queue (Celery or RQ with Redis).
15. **Evidence clip export**: save a few seconds of video around each violation for the reviewer.
16. **Read GPS and time from video metadata** where present, instead of manual entry.
17. **Per-ward alert routing**: send each incident to the responsible ward office.
18. **Replace seed data** (`pune_data.py`) with real camera registry, incident and crew data from the corporation.

### P3: Operations

19. **Docker and docker-compose** for one-command setup (CPU and GPU images).
20. **CI**: run `pytest` on every push; add a lint step.
21. **Retention job**: delete raw video and person crops after a set period (DPDP-aligned), and keep audit logs.
22. **Access control**: officer login and roles for the review queue.
23. **GPU deployment**: the detector is the slowest step on CPU (about 45 s for an 11-second clip).

---

## 4. Open risks

| Risk | Current mitigation | Gap |
|---|---|---|
| Wrongly accusing someone | Officer approval with name and audit log; bystander blur; plate legibility shown | No second OCR; no clip for context |
| False hazard alerts | Severity threshold; deterministic scores with sources | No evaluation set to tune thresholds |
| Missed garbage | Gemini examples; area measurement | Detector finds garbage in about half the frames on the test clip |
| Quota or API outage | Model fallback chain; non-essential steps degrade | Free tier is too small for daily use |
| Privacy | Blur, human review, local storage | No retention policy or access control yet |
| Network interception | | TomTom calls fail on the current machine |
