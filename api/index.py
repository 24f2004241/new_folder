from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# Load telemetry bundle data at startup
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")
try:
    with open(DATA_FILE, "r") as f:
        TELEMETRY_DATA = json.load(f)
except Exception:
    TELEMETRY_DATA = []

@app.post("/api/latency")
def analyze_latency(payload: TelemetryRequest):
    regions = payload.regions
    threshold = payload.threshold_ms
    
    results = {}
    
    for region in regions:
        # Filter records matching the specific region
        region_records = [r for r in TELEMETRY_DATA if r.get("region") == region]
        
        if not region_records:
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }
            continue
        
        latencies = [r.get("latency_ms", 0) for r in region_records]
        uptimes = [r.get("uptime", 0) for r in region_records]
        
        # Compute average latency
        avg_latency = sum(latencies) / len(latencies)
        
        # Compute 95th percentile latency
        sorted_latencies = sorted(latencies)
        p95_index = int(0.95 * len(sorted_latencies))
        if p95_index >= len(sorted_latencies):
            p95_index = len(sorted_latencies) - 1
        p95_latency = sorted_latencies[p95_index]
        
        # Compute average uptime
        avg_uptime = sum(uptimes) / len(uptimes)
        
        # Compute breaches (records above threshold)
        breaches = sum(1 for l in latencies if l > threshold)
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 4),
            "breaches": breaches
        }
        
    return results