from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List
import os
import aiofiles
from datetime import datetime
import json

router = APIRouter()

# Setup appending file destination
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/raw"))
TELEMETRY_LOG = os.path.join(DATA_DIR, "live_mouse_biometrics_1hz.jsonl")

# New Edge Computing Data Model (1-second summaries)
class PhysicsSummary(BaseModel):
    timestamp: str
    avg_velocity: float
    max_acceleration: float
    jerk: float
    click_count: int

class TelemetryPayload(BaseModel):
    user_id: str
    pc_id: str
    physics_sequence: List[PhysicsSummary]

async def append_telemetry_background(payload: TelemetryPayload):
    """
    Background task to write continuous mouse telemetry without blocking the API response.
    Saves in JSON Lines format for scalable ingestion.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        async with aiofiles.open(TELEMETRY_LOG, mode='a') as f:
            for summary in payload.physics_sequence:
                record = {
                    "user": payload.user_id,
                    "pc": payload.pc_id,
                    "timestamp": summary.timestamp,
                    "avg_velocity": summary.avg_velocity,
                    "max_acceleration": summary.max_acceleration,
                    "jerk": summary.jerk,
                    "click_count": summary.click_count,
                    "ingested_at": datetime.utcnow().isoformat()
                }
                await f.write(json.dumps(record) + "\n")
    except Exception as e:
        # In a real app, send this to a proper logging/monitoring system
        print(f"Failed to write background 1Hz telemetry: {e}")

@router.post("/mouse")
async def ingest_mouse_telemetry(payload: TelemetryPayload, background_tasks: BackgroundTasks):
    """
    Ingest a batch of 1-second physics summaries (Velocity, Jerk, etc.) from the endpoint.
    This edge-computing architecture keeps network and server load minimal.
    """
    if not payload.physics_sequence:
        raise HTTPException(status_code=400, detail="Physics sequence cannot be empty.")
    
    # Hand off disk I/O to background
    background_tasks.add_task(append_telemetry_background, payload)
    
    return {"status": "success", "message": f"Ingested {len(payload.physics_sequence)} seconds of biometric physics."}
