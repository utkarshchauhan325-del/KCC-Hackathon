# 🌊 KCC Hackathon – Pune Smart Drain & CCTV Flood Risk Monitoring

An intelligent geospatial monitoring and civic intelligence platform built for the **KCC Hackathon**, designed to monitor stormwater drainage systems and surveillance camera networks across Pune Municipal Corporation (PMC) zones to mitigate urban waterlogging and flood risks.

---

## 📌 Project Overview

Urban waterlogging and drainage blockage during monsoon seasons present severe challenges for civic authorities and citizens. This project integrates spatial CCTV surveillance data with municipal drainage network telemetry to provide actionable visibility into choke points, critical drains, and high-risk zones.

### Core Objectives
- **Spatial Correlation:** Map surveillance cameras (`camera_id`) to their respective drainage inlets (`drain_id`) across Pune's wards.
- **Risk Assessment:** Classify drain vulnerability into standard risk tiers (`ok`, `low`, `medium`, `high`, `critical`).
- **Emergency Preparedness:** Enable municipal response teams to dispatch maintenance crews to critical hotspots before severe flooding occurs.
- **Civic Analytics:** Provide actionable metrics and distribution dashboards for smart city administrators.

---

## 📊 Dataset Specifications

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

### Risk Distribution
- **Medium Risk:** 324 points
- **OK (Normal):** 253 points
- **High Risk:** 192 points
- **Low Risk:** 147 points
- **Critical Risk:** 84 points

### Monitored Municipal Zones (31 Areas)
Shivajinagar, Deccan Gymkhana, Navi Peth, Swargate, Kasba Peth, Bhawani Peth, Guruwar Peth, Nana Peth, Kothrud, Karve Nagar, Aundh, Baner, Sus, Warje, Dhankawadi, Katraj, Bibwewadi, Dhayari, Nanded, Shivane, Hadapsar, Mundhwa, Kharadi, Viman Nagar, Dhanori, Vishrantwadi, Dighi, Lohgaon, Undri, Ambegaon Budruk, and Ambegaon Khurd.

---

## 🛠️ Tech Stack & Architecture

- **Data Processing & Analytics:** Python, Pandas, GeoPandas, NumPy
- **Spatial Visualization:** Leaflet.js / Folium / Mapbox
- **Backend / APIs:** FastAPI / Flask / Node.js
- **Frontend Dashboard:** Interactive Web UI for real-time alerts and map markers

---

## 🚀 Getting Started

### 1. Clone Repository & Setup Branch
```bash
git clone https://github.com/utkarshchauhan325-del/KCC-Hackathon.git
cd KCC-Hackathon
```

### 2. Switch to your Feature Branch
```bash
git checkout rishikesh
git pull --rebase origin main
```

### 3. Explore Dataset with Python
```bash
python -c "import pandas as pd; df = pd.read_csv('pune_camera_drain_1000.csv'); print(df.head()); print(df['risk_status'].value_counts())"
```

---

## 👥 Team & Collaboration Workflow

This repository uses dedicated feature branches for team collaboration:
- `main` – Production-ready stable release branch
- `rishikesh` – Feature development & geospatial analytics
- `utkarsh` – Core backend & model development
- `gautam` – Data pipelines & integration

### Recommended Git Flow
1. Fetch latest changes from `main`:
   ```bash
   git pull --rebase origin main
   ```
2. Commit your feature updates to your respective branch:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```
3. Push to your remote branch:
   ```bash
   git push origin <your-branch-name>
   ```

---

## 📄 License
This project is developed as part of the KCC Hackathon. All rights reserved by the project contributors.
