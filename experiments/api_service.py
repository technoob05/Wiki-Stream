"""
🌉 WIKI-STREAM API SERVICE (v1.0)
────────────────────────────────────────────────────────────
FastAPI Bridge for the Forensic Dashboard.
Exposes intelligence_master.json and detailed edit data.
────────────────────────────────────────────────────────────
"""

import json
import csv
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys

# ── Config ──
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
REPORT_DIR = ROOT_DIR / "reports"
PIPELINE_SCRIPT = ROOT_DIR / "00_pipeline_manager.py"

app = FastAPI(title="Wiki-Stream Intelligence API")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this!
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Endpoints ──

@app.get("/api/status")
def get_status():
    """Check if the system is ready and reports exist."""
    master_exists = (REPORT_DIR / "intelligence_master.json").exists()
    return {
        "status": "online",
        "has_reports": master_exists,
        "last_updated": Path(REPORT_DIR / "intelligence_master.json").stat().st_mtime if master_exists else None
    }

@app.get("/api/threats")
def get_threats():
    """Get the latest threat distribution and top alerts."""
    master_f = REPORT_DIR / "intelligence_master.json"
    if not master_f.exists():
        raise HTTPException(status_code=404, detail="Intelligence report not found. Run the pipeline first.")

    with open(master_f, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/geo/threats")
def get_geo_threats():
    """Get BLOCK/FLAG threats with geographic coordinates for globe visualization.
    Maps Wikipedia domain to approximate region, then scatters edits within that region."""
    import random
    master_f = REPORT_DIR / "intelligence_master.json"
    if not master_f.exists():
        raise HTTPException(status_code=404, detail="No data")

    with open(master_f, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Domain -> approximate geo center + scatter radius
    DOMAIN_GEO = {
        "en.wikipedia.org": [
            # English Wikipedia: global, scatter across major regions
            {"lat": 40.0, "lon": -95.0, "label": "North America"},
            {"lat": 51.5, "lon": -0.1, "label": "Europe"},
            {"lat": 35.7, "lon": 139.7, "label": "East Asia"},
            {"lat": -33.9, "lon": 151.2, "label": "Oceania"},
            {"lat": 28.6, "lon": 77.2, "label": "South Asia"},
        ],
        "vi.wikipedia.org": [
            {"lat": 21.0, "lon": 105.8, "label": "Vietnam"},
        ],
    }

    random.seed(42)  # Deterministic for consistent display
    markers = []
    for v in data.get("all_verdicts", []):
        if v["action"] not in ("BLOCK", "FLAG", "REVIEW"):
            continue
        domain = v.get("domain", "en.wikipedia.org")
        regions = DOMAIN_GEO.get(domain, DOMAIN_GEO["en.wikipedia.org"])
        region = random.choice(regions)
        markers.append({
            "lat": region["lat"] + random.uniform(-8, 8),
            "lon": region["lon"] + random.uniform(-8, 8),
            "user": v["user"],
            "title": v["title"],
            "action": v["action"],
            "score": v["score"],
            "region": region["label"],
        })

    return {"markers": markers, "total": len(markers)}

@app.get("/api/edits/detail")
def get_edit_detail(user: str, title: str):
    """Search for the most recent processed edit detail across all lang folders."""
    # This is an expensive search, in production we'd use a database.
    # For this project, we audit the latest 'attributed' CSV files.
    
    found_edits = []
    for f in DATA_DIR.glob("**/processed/*_attributed.csv"):
        try:
            with open(f, "r", encoding="utf-8") as csvf:
                reader = csv.DictReader(csvf)
                for row in reader:
                    if row["user"] == user and row["title"] == title:
                        found_edits.append(row)
        except: continue
        
    if not found_edits:
        raise HTTPException(status_code=404, detail="Edit forensic data not found.")
        
    # Return the most recent one
    return found_edits[-1]

@app.get("/api/reports/master")
def get_master_report():
    """Get the latest synthesized markdown report."""
    report_f = REPORT_DIR / "final_forensic_report.md"
    if not report_f.exists():
        raise HTTPException(status_code=404, detail="Forensic report not found.")
    
    with open(report_f, "r", encoding="utf-8") as f:
        return {"content": f.read()}

@app.post("/api/pipeline/run")
def run_pipeline(background_tasks: BackgroundTasks):
    """Trigger the 7-stage pipeline in the background."""
    def run():
        subprocess.run([sys.executable, str(PIPELINE_SCRIPT)])
        
    background_tasks.add_task(run)
    return {"message": "Pipeline started in background."}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Wiki-Stream API starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
