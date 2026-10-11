from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# Enable CORS for requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Explicitly handle preflight OPTIONS requests
@app.options("/{path:path}")
async def options_handler(path: str):
    return Response(status_code=200)

class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

DATA_FILE = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
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
        
        avg_latency = sum(latencies) / len(latencies)
        
        sorted_latencies = sorted(latencies)
        p95_index = int(0.95 * len(sorted_latencies))
        if p95_index >= len(sorted_latencies):
            p95_index = len(sorted_latencies) - 1
        p95_latency = sorted_latencies[p95_index]
        
        avg_uptime = sum(uptimes) / len(uptimes)
        breaches = sum(1 for l in latencies if l > threshold)
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 4),
            "breaches": breaches
        }
        
    return results