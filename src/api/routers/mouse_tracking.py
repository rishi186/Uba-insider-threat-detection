"""
Mouse Tracking & Biometric Analysis Router.

Provides real-time ingestion, analysis, and anomaly detection for mouse
movement biometrics as part of the UBA Insider Threat Detection system.

Endpoints:
  POST /mouse/session/start     — Begin a new tracking session
  POST /mouse/session/end       — End an active session, compute final metrics
  POST /mouse/events            — Ingest raw mouse events (batched)
  GET  /mouse/session/{id}      — Retrieve session analytics
  GET  /mouse/sessions          — List all sessions for a user
  GET  /mouse/heatmap/{id}      — Heatmap data for a session
  GET  /mouse/anomaly/{id}      — Anomaly timeline for a session
  GET  /mouse/live/{user}       — Live metrics snapshot for a user
  GET  /mouse/demo/employees    — Demo employee list with biometric status
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Header, Depends
from pydantic import BaseModel, Field
from src.api.routers import websockets
from src.api.services.webhook_service import dispatch_siem_webhook
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.api.config import settings
import hmac
import hashlib
import math
import uuid
import time
import logging
import statistics

logger = logging.getLogger("uba.mouse_tracking")
router = APIRouter()


# =============================================================================
# DATA MODELS
# =============================================================================
class MouseEvent(BaseModel):
    """A single raw mouse event captured at ~60Hz on the client."""
    x: float = Field(..., description="X coordinate (px)")
    y: float = Field(..., description="Y coordinate (px)")
    timestamp: float = Field(..., description="Unix timestamp in ms")
    event_type: str = Field(
        default="move",
        description="Type of event: move, click, scroll, drag"
    )
    button: Optional[int] = Field(None, description="Mouse button (0=left, 1=middle, 2=right)")
    scroll_delta: Optional[float] = Field(None, description="Scroll delta for scroll events")


class KeyboardMetrics(BaseModel):
    """Aggregate keystroke dynamics for a batch window."""
    total_strokes: int = Field(default=0, description="Number of keystrokes in this batch")
    avg_dwell_time_ms: float = Field(default=0.0, description="Average time a key is held")
    avg_flight_time_ms: float = Field(default=0.0, description="Average time between keys")
    delete_ratio: float = Field(default=0.0, description="Ratio of backspace/delete keys")


class MouseEventBatch(BaseModel):
    """Batch of mouse events for efficient ingestion."""
    user_id: str = Field(..., description="Employee user ID")
    session_id: str = Field(..., description="Active session ID")
    events: List[MouseEvent] = Field(..., min_length=1, max_length=500)
    screen_width: int = Field(default=1920)
    screen_height: int = Field(default=1080)
    keyboard_metrics: Optional[KeyboardMetrics] = Field(None, description="Optional keystroke dynamics")


class SessionStartRequest(BaseModel):
    """Request to begin a new tracking session."""
    user_id: str
    pc_id: str = Field(default="WORKSTATION-01")
    application: str = Field(default="UBA Dashboard")
    screen_width: int = Field(default=1920)
    screen_height: int = Field(default=1080)


class SessionEndRequest(BaseModel):
    """Request to end an active session."""
    session_id: str
    user_id: str


# =============================================================================
# IN-MEMORY SESSION STORE (Production would use Redis/DB)
# =============================================================================
class MouseSession:
    """Tracks all data for a single mouse tracking session."""

    def __init__(self, session_id: str, user_id: str, pc_id: str,
                 application: str, screen_w: int, screen_h: int):
        self.session_id = session_id
        self.user_id = user_id
        self.pc_id = pc_id
        self.application = application
        self.screen_width = screen_w
        self.screen_height = screen_h
        self.started_at = datetime.now(timezone.utc)
        self.ended_at: Optional[datetime] = None
        self.is_active = True

        # Raw event storage
        self.events: List[Dict] = []

        # Real-time computed metrics
        self.total_distance = 0.0
        self.total_clicks = 0
        self.left_clicks = 0
        self.right_clicks = 0
        self.double_clicks = 0
        self.scroll_events = 0
        self.total_scroll_delta = 0.0
        self.drag_events = 0

        # Physics metrics (updated in sliding windows)
        self.velocities: List[float] = []
        self.accelerations: List[float] = []
        self.jerks: List[float] = []
        self.curvatures: List[float] = []
        self.angular_velocities: List[float] = []

        # Pause/hesitation tracking
        self.pauses: List[float] = []  # Duration of pauses in ms
        self.idle_time_ms = 0.0

        # Keystroke dynamics
        self.total_keystrokes = 0
        self.avg_dwell_times: List[float] = []
        self.avg_flight_times: List[float] = []
        self.delete_ratios: List[float] = []

        # Trajectory data for heatmap
        self.heatmap_cells: Dict[str, int] = defaultdict(int)
        self.click_positions: List[Dict] = []

        # Anomaly scores over time
        self.anomaly_timeline: List[Dict] = []

        # Previous event for delta calculations
        self._prev_event: Optional[Dict] = None
        self._prev_velocity = 0.0
        self._prev_acceleration = 0.0

        # Click timing for double-click detection
        self._last_click_time = 0.0

    def add_event(self, event: MouseEvent):
        """Process a single mouse event, updating all metrics."""
        evt = {
            "x": event.x, "y": event.y,
            "t": event.timestamp, "type": event.event_type,
            "button": event.button, "scroll_delta": event.scroll_delta,
        }
        self.events.append(evt)

        if event.event_type == "click":
            self.total_clicks += 1
            if event.button == 0:
                self.left_clicks += 1
            elif event.button == 2:
                self.right_clicks += 1

            # Double-click detection (< 300ms between clicks)
            if event.timestamp - self._last_click_time < 300:
                self.double_clicks += 1
            self._last_click_time = event.timestamp

            self.click_positions.append({
                "x": event.x, "y": event.y, "t": event.timestamp
            })

        elif event.event_type == "scroll":
            self.scroll_events += 1
            self.total_scroll_delta += abs(event.scroll_delta or 0)

        elif event.event_type == "drag":
            self.drag_events += 1

        # Compute physics from movement
        if self._prev_event and event.event_type in ("move", "drag"):
            prev = self._prev_event
            dx = event.x - prev["x"]
            dy = event.y - prev["y"]
            dt = max(event.timestamp - prev["t"], 1)  # ms, prevent div-by-zero

            distance = math.sqrt(dx * dx + dy * dy)
            self.total_distance += distance

            # Velocity (px/ms)
            velocity = distance / dt
            self.velocities.append(velocity)

            # Acceleration (px/ms²)
            acceleration = (velocity - self._prev_velocity) / dt
            self.accelerations.append(abs(acceleration))

            # Jerk (px/ms³)
            jerk = (acceleration - self._prev_acceleration) / dt
            self.jerks.append(abs(jerk))

            # Curvature estimation (change in angle per unit distance)
            if distance > 0:
                angle = math.atan2(dy, dx)
                if hasattr(self, '_prev_angle'):
                    angle_diff = abs(angle - self._prev_angle)
                    # Normalize to [0, π]
                    if angle_diff > math.pi:
                        angle_diff = 2 * math.pi - angle_diff
                    curvature = angle_diff / max(distance, 0.001)
                    self.curvatures.append(curvature)
                    self.angular_velocities.append(angle_diff / dt)
                self._prev_angle = angle

            # Pause detection (> 500ms idle)
            if dt > 500:
                self.pauses.append(dt)
                self.idle_time_ms += dt

            self._prev_velocity = velocity
            self._prev_acceleration = acceleration

            # Heatmap — 20x20 grid
            gx = min(int(event.x / max(self.screen_width, 1) * 20), 19)
            gy = min(int(event.y / max(self.screen_height, 1) * 20), 19)
            self.heatmap_cells[f"{gx},{gy}"] += 1

        self._prev_event = evt

    def add_keyboard_metrics(self, metrics: KeyboardMetrics):
        """Update session with new batch of keystroke metrics."""
        self.total_keystrokes += metrics.total_strokes
        if metrics.total_strokes > 0:
            self.avg_dwell_times.append(metrics.avg_dwell_time_ms)
            if metrics.avg_flight_time_ms > 0:
                self.avg_flight_times.append(metrics.avg_flight_time_ms)
            self.delete_ratios.append(metrics.delete_ratio)

    def compute_anomaly_score(self) -> Dict:
        """
        Compute a biometric anomaly score based on current session metrics.
        
        The score considers:
        - Velocity consistency (std dev)
        - Jerk spikes (sudden direction changes)
        - Click patterns (frequency anomalies)
        - Pause patterns (hesitation detection)
        - Straightness index (bot detection)
        
        Returns a dict with individual component scores and overall score.
        """
        scores = {}

        # 1. Velocity irregularity score (0-25)
        if len(self.velocities) > 5:
            vel_cv = (statistics.stdev(self.velocities) /
                      max(statistics.mean(self.velocities), 0.001))
            # Very high or very low CV is suspicious
            scores["velocity_irregularity"] = min(25, vel_cv * 10)
        else:
            scores["velocity_irregularity"] = 0

        # 2. Jerk spike score (0-25)
        if len(self.jerks) > 5:
            jerk_mean = statistics.mean(self.jerks)
            jerk_std = statistics.stdev(self.jerks) if len(self.jerks) > 1 else 0
            spike_count = sum(1 for j in self.jerks if j > jerk_mean + 2 * jerk_std)
            spike_ratio = spike_count / len(self.jerks)
            scores["jerk_spikes"] = min(25, spike_ratio * 100)
        else:
            scores["jerk_spikes"] = 0

        # 3. Click pattern score (0-25)
        if self.total_clicks > 0:
            duration_s = max((time.time() * 1000 -
                              (self.events[0]["t"] if self.events else time.time() * 1000)) / 1000, 1)
            click_rate = self.total_clicks / duration_s
            # Abnormal click rate (too fast = automation, too slow = disengaged)
            if click_rate > 5:  # More than 5 clicks/sec is suspicious
                scores["click_pattern"] = min(25, (click_rate - 5) * 5)
            elif click_rate < 0.01 and duration_s > 60:
                scores["click_pattern"] = 10  # Very few clicks over long duration
            else:
                scores["click_pattern"] = 0
        else:
            scores["click_pattern"] = 0

        # 4. Hesitation/pause score (0-25)
        if len(self.pauses) > 0:
            avg_pause = statistics.mean(self.pauses)
            long_pauses = sum(1 for p in self.pauses if p > 3000)  # > 3 seconds
            scores["hesitation"] = min(25, long_pauses * 5 + (avg_pause / 1000))
        else:
            scores["hesitation"] = 0

        # Overall anomaly score (0-100)
        overall = sum(scores.values())
        scores["overall"] = min(100, overall)

        return scores

    def get_metrics(self) -> Dict:
        """Return computed metrics for this session."""
        duration_ms = ((self.ended_at or datetime.now(timezone.utc)) -
                       self.started_at).total_seconds() * 1000

        anomaly = self.compute_anomaly_score()

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "pc_id": self.pc_id,
            "application": self.application,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "is_active": self.is_active,
            "duration_ms": duration_ms,
            "duration_readable": self._format_duration(duration_ms),

            # Movement metrics
            "total_events": len(self.events),
            "total_distance_px": round(self.total_distance, 2),
            "avg_velocity_px_ms": round(
                statistics.mean(self.velocities), 4
            ) if self.velocities else 0,
            "max_velocity_px_ms": round(
                max(self.velocities), 4
            ) if self.velocities else 0,
            "velocity_std": round(
                statistics.stdev(self.velocities), 4
            ) if len(self.velocities) > 1 else 0,

            # Acceleration & jerk
            "avg_acceleration": round(
                statistics.mean(self.accelerations), 6
            ) if self.accelerations else 0,
            "avg_jerk": round(
                statistics.mean(self.jerks), 8
            ) if self.jerks else 0,
            "jerk_spikes": sum(
                1 for j in self.jerks
                if self.jerks and j > statistics.mean(self.jerks) + 2 * (
                    statistics.stdev(self.jerks) if len(self.jerks) > 1 else 0
                )
            ),

            # Curvature
            "avg_curvature": round(
                statistics.mean(self.curvatures), 6
            ) if self.curvatures else 0,
            "straightness_index": round(
                1 - (statistics.mean(self.curvatures)
                     if self.curvatures else 0), 4
            ),

            # Click metrics
            "total_clicks": self.total_clicks,
            "left_clicks": self.left_clicks,
            "right_clicks": self.right_clicks,
            "double_clicks": self.double_clicks,
            "click_rate_per_min": round(
                self.total_clicks / max(duration_ms / 60000, 0.001), 2
            ),

            # Scroll metrics
            "scroll_events": self.scroll_events,
            "total_scroll_delta": round(self.total_scroll_delta, 2),

            # Drag metrics
            "drag_events": self.drag_events,

            # Pause/idle metrics
            "pause_count": len(self.pauses),
            "total_idle_ms": round(self.idle_time_ms, 2),
            "idle_percentage": round(
                self.idle_time_ms / max(duration_ms, 1) * 100, 2
            ),
            "avg_pause_ms": round(
                statistics.mean(self.pauses), 2
            ) if self.pauses else 0,

            # Keystroke metrics
            "total_keystrokes": self.total_keystrokes,
            "keystroke_rate_per_min": round(
                self.total_keystrokes / max(duration_ms / 60000, 0.001), 2
            ),
            "avg_dwell_time_ms": round(
                statistics.mean(self.avg_dwell_times), 2
            ) if self.avg_dwell_times else 0,
            "avg_flight_time_ms": round(
                statistics.mean(self.avg_flight_times), 2
            ) if self.avg_flight_times else 0,
            "avg_delete_ratio": round(
                statistics.mean(self.delete_ratios), 4
            ) if self.delete_ratios else 0,

            # Anomaly scores
            "anomaly_scores": anomaly,

            # Screen info
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }

    def get_heatmap(self) -> Dict:
        """Return heatmap grid data."""
        grid = [[0] * 20 for _ in range(20)]
        for key, count in self.heatmap_cells.items():
            gx, gy = map(int, key.split(","))
            grid[gy][gx] = count

        max_val = max(max(row) for row in grid) if any(any(row) for row in grid) else 1

        return {
            "session_id": self.session_id,
            "grid": grid,
            "max_value": max_val,
            "grid_size": 20,
            "click_positions": self.click_positions[-200:],  # Last 200 clicks
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }

    def get_anomaly_timeline(self) -> List[Dict]:
        """Return anomaly scores computed at regular intervals."""
        return self.anomaly_timeline

    @staticmethod
    def _format_duration(ms: float) -> str:
        """Format milliseconds into human-readable duration."""
        seconds = int(ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


# =============================================================================
# GLOBAL SESSION REGISTRY
# =============================================================================
_sessions: Dict[str, MouseSession] = {}
_user_sessions: Dict[str, List[str]] = defaultdict(list)

# =============================================================================
# DEMO EMPLOYEE DATA
# =============================================================================
DEMO_EMPLOYEES = [
    {
        "user_id": "EMP001",
        "name": "Rishi Mishra",
        "role": "Security Analyst",
        "department": "Cybersecurity",
        "pc_id": "WS-SEC-001",
        "avatar_color": "#00d4ff",
        "risk_level": "low",
        "status": "active",
        "baseline_velocity": 0.42,
        "baseline_jerk": 0.0008,
    },
    {
        "user_id": "EMP002",
        "name": "Priya Sharma",
        "role": "Software Engineer",
        "department": "Engineering",
        "pc_id": "WS-ENG-012",
        "avatar_color": "#00ff88",
        "risk_level": "low",
        "status": "active",
        "baseline_velocity": 0.55,
        "baseline_jerk": 0.0012,
    },
    {
        "user_id": "EMP003",
        "name": "Alex Chen",
        "role": "Database Admin",
        "department": "IT Operations",
        "pc_id": "WS-DBA-003",
        "avatar_color": "#ff6b35",
        "risk_level": "medium",
        "status": "monitoring",
        "baseline_velocity": 0.38,
        "baseline_jerk": 0.0015,
    },
    {
        "user_id": "EMP004",
        "name": "Marcus Johnson",
        "role": "Contractor",
        "department": "Finance",
        "pc_id": "WS-FIN-007",
        "avatar_color": "#ff3366",
        "risk_level": "high",
        "status": "flagged",
        "baseline_velocity": 0.61,
        "baseline_jerk": 0.0022,
    },
    {
        "user_id": "EMP005",
        "name": "Sarah Williams",
        "role": "HR Manager",
        "department": "Human Resources",
        "pc_id": "WS-HR-002",
        "avatar_color": "#b366ff",
        "risk_level": "low",
        "status": "active",
        "baseline_velocity": 0.35,
        "baseline_jerk": 0.0006,
    },
]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/session/start")
async def start_session(req: SessionStartRequest):
    """
    Begin a new mouse tracking session.
    Returns a session_id that must be used for subsequent event ingestion.
    """
    session_id = str(uuid.uuid4())[:12]

    session = MouseSession(
        session_id=session_id,
        user_id=req.user_id,
        pc_id=req.pc_id,
        application=req.application,
        screen_w=req.screen_width,
        screen_h=req.screen_height,
    )

    _sessions[session_id] = session
    _user_sessions[req.user_id].append(session_id)

    logger.info(
        "Mouse session started: %s for user %s on %s",
        session_id, req.user_id, req.pc_id,
    )

    return {
        "status": "success",
        "session_id": session_id,
        "user_id": req.user_id,
        "started_at": session.started_at.isoformat(),
        "message": f"Tracking session {session_id} started for {req.user_id}",
    }


@router.post("/session/end")
async def end_session(req: SessionEndRequest):
    """End an active tracking session and compute final analytics."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {req.session_id} not found")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session already ended")

    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)

    metrics = session.get_metrics()
    anomaly = session.compute_anomaly_score()

    logger.info(
        "Mouse session ended: %s — %d events, anomaly=%.1f",
        req.session_id, len(session.events), anomaly["overall"],
    )

    return {
        "status": "success",
        "message": f"Session {req.session_id} ended",
        "final_metrics": metrics,
        "anomaly_scores": anomaly,
    }


async def verify_hmac(request: Request, signature: str = Header(..., alias="X-HMAC-Signature")):
    body = await request.body()
    secret = getattr(settings, "HMAC_SECRET", "SUPER_SECRET_HMAC_KEY").encode('utf-8')
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid HMAC Signature")

@router.post("/events")
async def ingest_events(batch: MouseEventBatch, background_tasks: BackgroundTasks, _: None = Depends(verify_hmac)):
    """
    Ingest a batch of raw mouse events.
    Events are processed immediately for real-time metrics.
    """
    session = _sessions.get(batch.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {batch.session_id} not found")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is no longer active")

    for event in batch.events:
        session.add_event(event)
        
    if batch.keyboard_metrics:
        session.add_keyboard_metrics(batch.keyboard_metrics)

    # Compute anomaly snapshot every 50 events
    if len(session.events) % 50 == 0:
        anomaly = session.compute_anomaly_score()
        session.anomaly_timeline.append({
            "event_count": len(session.events),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scores": anomaly,
        })
        
        # Broadcast anomaly score update
        await websockets.manager.broadcast("biometric_update", {
            "user_id": batch.user_id,
            "session_id": batch.session_id,
            "anomaly_score": anomaly["overall"],
            "risk_level": "high" if anomaly["overall"] >= 75 else "medium" if anomaly["overall"] >= 40 else "low"
        })
        
        if anomaly["overall"] >= 75:
            alert_data = {
                "user_id": batch.user_id,
                "type": "Biometric Anomaly",
                "severity": "critical",
                "message": f"Critical biometric deviation detected ({anomaly['overall']:.1f}%)"
            }
            await websockets.manager.broadcast("new_alert", alert_data)
            # Dispatch to SIEM asynchronously
            background_tasks.add_task(dispatch_siem_webhook, alert_data)

    return {
        "status": "success",
        "events_ingested": len(batch.events),
        "total_events": len(session.events),
        "current_anomaly": session.compute_anomaly_score()["overall"],
    }


@router.get("/session/{session_id}")
async def get_session_metrics(session_id: str):
    """Retrieve full analytics for a tracking session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return session.get_metrics()


@router.get("/sessions")
async def list_user_sessions(user_id: str, limit: int = 20):
    """List all tracking sessions for a user."""
    session_ids = _user_sessions.get(user_id, [])
    sessions = []
    for sid in reversed(session_ids[-limit:]):
        session = _sessions.get(sid)
        if session:
            sessions.append({
                "session_id": sid,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "is_active": session.is_active,
                "total_events": len(session.events),
                "anomaly_score": session.compute_anomaly_score()["overall"],
            })

    return {
        "user_id": user_id,
        "total_sessions": len(session_ids),
        "sessions": sessions,
    }


@router.get("/heatmap/{session_id}")
async def get_heatmap(session_id: str):
    """Get movement heatmap data for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return session.get_heatmap()


@router.get("/anomaly/{session_id}")
async def get_anomaly_timeline(session_id: str):
    """Get anomaly score timeline for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "session_id": session_id,
        "current_scores": session.compute_anomaly_score(),
        "timeline": session.get_anomaly_timeline(),
    }


@router.get("/live/{user_id}")
async def get_live_metrics(user_id: str):
    """Get live metrics snapshot for the most recent active session of a user."""
    session_ids = _user_sessions.get(user_id, [])

    # Find the most recent active session
    active_session = None
    for sid in reversed(session_ids):
        s = _sessions.get(sid)
        if s and s.is_active:
            active_session = s
            break

    if not active_session:
        return {
            "user_id": user_id,
            "has_active_session": False,
            "message": "No active tracking session for this user",
        }

    metrics = active_session.get_metrics()
    return {
        "user_id": user_id,
        "has_active_session": True,
        **metrics,
    }


@router.get("/demo/employees")
async def get_demo_employees():
    """
    Get demo employee list with biometric tracking status.
    Used by the frontend demo page to show realistic employee data.
    """
    employees = []
    for emp in DEMO_EMPLOYEES:
        # Check if employee has an active session
        sessions = _user_sessions.get(emp["user_id"], [])
        active_session = None
        for sid in reversed(sessions):
            s = _sessions.get(sid)
            if s and s.is_active:
                active_session = s
                break

        emp_data = {
            **emp,
            "has_active_session": active_session is not None,
            "active_session_id": active_session.session_id if active_session else None,
            "current_anomaly_score": (
                active_session.compute_anomaly_score()["overall"]
                if active_session else 0
            ),
            "total_sessions": len(sessions),
            "total_events_tracked": sum(
                len(_sessions[sid].events)
                for sid in sessions
                if sid in _sessions
            ),
        }
        employees.append(emp_data)

    return {
        "employees": employees,
        "total": len(employees),
        "active_tracking": sum(
            1 for e in employees if e["has_active_session"]
        ),
    }
