from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: float

app = FastAPI()

# Allow POST from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.post("/api/latency")
async def compute_latency(data: RequestBody):
    # Load telemetry bundle
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_telemetry.json")
    try:
        with open(path) as f:
            bundle = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to load telemetry bundle")

    result = {}
    for region in data.regions:
        records = bundle.get(region, [])
        if not records:
            # Return zeros if no data
            result[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }
            continue

        latencies = np.array([r["latency_ms"] for r in records])
        uptimes = np.array([r["uptime"] for r in records])
        breaches = int((latencies > data.threshold_ms).sum())

        result[region] = {
            "avg_latency": float(np.mean(latencies)),
            "p95_latency": float(np.percentile(latencies, 95)),
            "avg_uptime": float(np.mean(uptimes)),
            "breaches": breaches
        }

    return {"regions": result}
