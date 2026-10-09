# Tech stack and models

## Models

| Model | Provider | Where it runs | Used for | Why this one |
|---|---|---|---|---|
| **Gemini 3.8 Flash** (`gemini-3.8-flash`) | Google, via the Gemini API | Cloud | Understanding the video: infrastructure issues (Pass A), dumping violators and plates (Pass B), drain condition (Pass C), and marking garbage on keyframes | Native video input, structured JSON output, bounding boxes; Flash keeps latency and cost low. Set by `GEMINI_MODEL` in `.env`. |
| Gemini fallbacks | Google | Cloud | Same calls when the primary model is rate-limited or unavailable | Free-tier quota is per model (20 requests/day). Order: 3.8, 3.7, 3.6, 3.5 Flash; 3 Flash preview; Flash latest; 3.5 and 3.1 Flash-Lite. |
| **YOLOE-26s-seg** (`yoloe-26s-seg.pt`) | Ultralytics | Local CPU | Per-frame instance segmentation of people, vehicles, drains, potholes, plates, bins and (via visual prompts) garbage | Open-vocabulary: classes come from text or example boxes, so no training data was needed. About 0.3 s per frame at 640 px on CPU. |
| **MobileCLIP2-B** (`mobileclip2_b.ts`) | Apple, packaged by Ultralytics | Local, build time only | Turning the text class names into embeddings once, when the CivicEye model is built | Needed by YOLOE for text prompts; not loaded at runtime once the baked model exists. |
| **YOLOE visual-prompt encoder** | Ultralytics (part of YOLOE) | Local CPU | Turning Gemini's garbage boxes into class embeddings for each video | Text prompts could not see real garbage (best score 7%); example boxes from the same video work. |
| **BoT-SORT** | Ultralytics tracker | Local CPU | Keeping one ID per person/vehicle/drain across frames, with sparse optical-flow camera-motion compensation | Handles handheld and panning phone footage better than plain ByteTrack. |
| **Haar cascade, frontal face** | OpenCV | Local CPU | Blurring bystander faces in violation evidence | Small, no download, good enough for a privacy pass before human review. |

Evaluated and not used:

| Model | Result |
|---|---|
| YOLOE-11s-seg | Superseded by the YOLOE-26 generation shipped with Ultralytics 8.4. |
| YOLOE-26l-seg (large) | 2.4x slower (97 s against 40 s on the test clip) and no better on garbage; it painted water as garbage. |
| Gemini 2.5 Flash | Not available to this API key (404). |
| ByteTrack (Ultralytics default) | Replaced by BoT-SORT for camera-motion compensation. |
| BoT-SORT ReID on native features | Needs features that are only produced inside Ultralytics' own tracking loop; no effect with this pipeline. |

## Languages and core libraries

| Layer | Technology | Version (tested) | Notes |
|---|---|---|---|
| Language | Python | 3.14 (project supports 3.9+) | |
| VLM SDK | `google-genai` | 2.28 | Files API upload, `generate_content` with `response_schema` |
| Detection | `ultralytics` | 8.4.174 | YOLOE, visual prompts, trackers |
| Deep learning | `torch`, `torchvision` | 2.14 (CPU build) | Install from the PyTorch CPU index for laptops without NVIDIA GPUs |
| Tracking support | `lap` | 0.5.13 | Linear assignment for the tracker |
| Text encoder support | `clip` (Ultralytics fork) | 1.0 | Only used when building the detector model |
| Computer vision | `opencv-python` | 4.14 (< 5 required) | Frame extraction, crops, drawing, face blur, contours |
| Video encoding | `imageio-ffmpeg` | 0.6 | Bundled ffmpeg for the H.264 transcode |
| Validation | `pydantic`, `pydantic-settings` | 2.13, 2.15 | Gemini response schemas and `.env` settings |
| Database | `sqlalchemy` + SQLite | 2.1 | PostgreSQL-ready through SQLAlchemy |
| Dashboard | `streamlit` | 1.65 | `st.navigation`, popovers, keyed containers |
| Maps and charts | `folium`, `streamlit-folium`, `plotly` | 0.20, 0.27, 7.1 | Risk map and analytics |
| HTTP | `requests`, `urllib` | | Telegram and webhook alerts; weather and traffic clients |
| Email | `smtplib` (standard library) | | STARTTLS on 587, SSL on 465 |
| Tests | `pytest` | 9.1 | 66 tests |

## External services

| Service | Purpose | Key |
|---|---|---|
| Google Gemini API | Video understanding | `GEMINI_API_KEY` |
| WeatherAPI.com | Live Pune rainfall, forecast and humidity for the dashboard ranking (cached 5 min) | `WEATHER_API_KEY` |
| TomTom Traffic Flow API | Live congestion per monitored location | `TOMTOM_API_KEY` |
| SMTP server | Email alerts | `SMTP_*`, `ALERT_EMAIL_RECIPIENT` |
| Telegram Bot API | Telegram alerts | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Any HTTPS endpoint | Webhook alerts with evidence as base64 | `WEBHOOK_URL` |

## Front end

| Aspect | Choice |
|---|---|
| Framework | Streamlit, multipage via `st.navigation(position="hidden")` with a custom top bar |
| Navigation | Fixed frosted top bar with page links, clock and a pop-up command-palette menu (`st.popover`) |
| Theme | Light canvas `#F3F5F8`, white surfaces, hairline borders `#E3E8EF`, single teal accent `#0A7C8F`, status colours for critical/high/watch/low |
| Type | Space Grotesk (headings), Inter (body), JetBrains Mono (numbers, IDs, timestamps) |
| Icons | Inline SVG line icons; no emojis |

## Hardware used during development

Windows 11 laptop, CPU only (no GPU). Every timing in the docs comes from this machine. With an NVIDIA GPU and the CUDA build of PyTorch, the detector step should be several times faster.
