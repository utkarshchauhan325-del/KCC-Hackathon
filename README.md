# 🌊 KCC Hackathon – FloodGuard: Pune Municipal Flood Risk & CCTV Intelligence Platform

An intelligent geospatial monitoring, computer vision, and early warning platform built for the **KCC Hackathon**, designed to monitor stormwater drainage systems and surveillance camera networks across Pune Municipal Corporation (PMC) zones to mitigate urban waterlogging and flood risks.

---

## 📌 Project Overview

Urban waterlogging and drainage blockage during monsoon seasons present severe challenges for civic authorities and citizens. **FloodGuard (CivicEye)** integrates spatial CCTV surveillance data with municipal drainage network telemetry to provide real-time visibility into choke points, critical drains, and high-risk flood zones.

### Core Objectives & Capabilities
- **Real-Time Flood Risk Overview:** Live executive dashboard tracking 53 municipal monitoring points, active waterlogging, critical junctions, and drainage blockage.
- **Geospatial GIS Map:** Interactive spatial telemetry of Pune with river catchment corridors (Mula-Mutha river basin), glowing risk hotspots, and satellite overlays.
- **AI Computer Vision Inspection:** Multi-pass Vision-Language Model (Gemini VLM) analyzing CCTV/drone video footage:
  - **Pass A:** Civic hazard detection (open manholes, broken culverts, standing wastewater).
  - **Pass B:** Illegal dumping detection & vehicle number plate OCR with DPDP Act bystander privacy blurring.
  - **Pass C:** Deterministic 0–100 Sewer Overflow Risk Scoring engine.
- **Municipal Priority Queue:** Human-in-the-loop review workflow for municipal officers to approve fine notices and dispatch emergency crews.
- **Operations & Interventions Tracker:** Live deployment monitoring of 500/1000 GPM mobile dewatering pumps, suction tankers, and robotic drain cleaning crawlers.
- **Flood Analytics & Certified Municipal Audit Reports:** Advanced hydrological correlation graphs and one-click export of official printable municipal reports (HTML/PDF), CSV sensor telemetry, and GeoJSON layers.

---

## 📊 Dataset & Surveillance Specifications

The repository includes curated spatial-risk mapping data in [`pune_camera_drain_1000.csv`](pune_camera_drain_1000.csv):

| Field | Type | Description | Example |
|---|---|---|---|
| `camera_id` | String | Unique CCTV Camera Identifier | `CAM-0001` |
| `drain_id` | String | Corresponding Drain / Inlet Node Identifier | `D-0001` |
| `area_reference` | String | Locality / Ward Name across Pune (31 areas) | `Shivajinagar`, `Kothrud` |
| `camera_lat` | Float | Latitude coordinate of the camera | `18.529724` |
| `camera_lon` | Float | Longitude coordinate of the camera | `73.845668` |
| `drain_lat` | Float | Latitude coordinate of the drain | `18.529628` |
| `drain_lon` | Float | Longitude coordinate of the drain | `73.845766` |
| `risk_status` | String | Current assessed flood/clogging risk level | `ok`, `low`, `medium`, `high`, `critical` |
| `data_type` | String | Dataset source / alignment classification | `synthetic_map_aligned` |

### Monitored Municipal Areas (31 Key Wards)
Shivajinagar, Deccan Gymkhana, Navi Peth, Swargate, Kasba Peth, Bhawani Peth, Guruwar Peth, Nana Peth, Kothrud, Karve Nagar, Aundh, Baner, Sus, Warje, Dhankawadi, Katraj, Bibwewadi, Dhayari, Nanded, Shivane, Hadapsar, Mundhwa, Kharadi, Viman Nagar, Dhanori, Vishrantwadi, Dighi, Lohgaon, Undri, Ambegaon Budruk, and Ambegaon Khurd.

---

## 🛠️ Technology Stack

- **Frontend & Visualizations:** Streamlit, Folium, Streamlit-Folium, Plotly, Altair, PyDeck, Vanilla CSS Design System
- **Computer Vision & VLM:** Google Gemini 2.5 Flash / 3 Flash Preview via `google-genai` SDK, OpenCV
- **Backend & Storage:** Python 3.9+, FastAPI, SQLAlchemy, SQLite / PostgreSQL
- **Testing & Quality:** pytest, Pydantic v2 type safety

---

## 🚀 Quickstart & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/utkarshchauhan325-del/KCC-Hackathon.git
cd KCC-Hackathon
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pyproject.toml  # or pip install streamlit plotly folium streamlit-folium pydantic sqlalchemy google-genai
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
# Add your GEMINI_API_KEY inside .env
```

### 4. Launch FloodGuard Dashboard
```bash
streamlit run app/ui/dashboard.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser to access the dashboard.

### 5. Run Test Suite
```bash
pytest
```

---

## 👥 Team & Collaboration Workflow

This repository uses dedicated feature branches for team collaboration:
- `main` – Production-ready stable release branch
- `rishikesh` – Feature development & geospatial analytics
- `utkarsh` – Core backend & model development
- `gautam` – Data pipelines & integration

---

## 📄 License
This project is developed as part of the KCC Hackathon. All rights reserved by the project contributors.
