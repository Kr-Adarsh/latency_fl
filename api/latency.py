from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from pathlib import Path
import json

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load JSON once at startup
DATA_PATH = Path(__file__).parent.parent / "assets" / "q-vercel-latency.json"
try:
    with open(DATA_PATH) as f:
        raw = json.load(f)
except Exception as e:
    raise RuntimeError(f"Could not load telemetry JSON: {e}")

# Flatten into DataFrame
records = []
for region, recs in raw.items():
    for r in recs:
        records.append({
            "region": region,
            "latency_ms": r.get("latency_ms"),
            "uptime": r.get("uptime")
        })
df = pd.DataFrame.from_records(records)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/")
async def get_latency_stats(request: Request):
    payload = await request.json()
    regions = payload.get("regions", [])
    threshold = float(payload.get("threshold_ms", 0))

    result = {}
    for region in regions:
        sub = df[df["region"] == region]
        if sub.empty:
            result[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }
            continue

        lat = sub["latency_ms"].to_numpy()
        up  = sub["uptime"].to_numpy()
        result[region] = {
            "avg_latency": round(lat.mean(), 2),
            "p95_latency": round(np.percentile(lat, 95), 2),
            "avg_uptime":  round(up.mean(), 3),
            "breaches":    int((lat > threshold).sum())
        }

    return {"regions": result}
