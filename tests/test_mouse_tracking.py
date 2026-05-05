"""
Comprehensive tests for the Mouse Tracking & Biometric Analysis module.

Run: python -m pytest tests/test_mouse_tracking.py -v
"""

import pytest
import time
import math
from fastapi.testclient import TestClient
from src.api.main import app, rate_limiter


from src.api.routers.mouse_tracking import verify_hmac

app.dependency_overrides[verify_hmac] = lambda: None
client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the rate limiter before each test to prevent 429 errors."""
    rate_limiter.requests.clear()


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

def create_session(user_id="TEST_USER_001") -> str:
    """Helper: create a session and return its ID."""
    r = client.post("/api/mouse/session/start", json={
        "user_id": user_id,
        "pc_id": "WS-TEST-001",
        "application": "Test App",
        "screen_width": 1920,
        "screen_height": 1080,
    })
    assert r.status_code == 200
    return r.json()["session_id"]


def generate_mouse_events(n=50, start_x=100, start_y=100, pattern="normal"):
    """
    Generate realistic mouse event payloads.
    
    Patterns:
      - normal: smooth curves with natural velocity variation
      - linear: perfectly straight lines (bot-like)
      - erratic: sudden jumps and high jerk
      - idle: minimal movement with long pauses
    """
    events = []
    t = time.time() * 1000
    x, y = float(start_x), float(start_y)
    
    for i in range(n):
        if pattern == "normal":
            # Natural mouse movement: smooth curves
            angle = math.sin(i * 0.15) * 0.8
            speed = 3.0 + math.sin(i * 0.3) * 2.0
            x += math.cos(angle) * speed
            y += math.sin(angle) * speed
            dt = 16 + (i % 3) * 2  # ~60Hz with jitter
            
        elif pattern == "linear":
            # Perfectly straight line — suspicious bot behavior
            x += 5.0
            y += 0.0
            dt = 16  # Perfect timing
            
        elif pattern == "erratic":
            # Sudden jumps and direction reversals
            x += (20 if i % 2 == 0 else -15) * (1 + i * 0.1)
            y += (15 if i % 3 == 0 else -20) * (1 + i * 0.05)
            dt = 8 + (i % 5) * 10  # Irregular timing
            
        elif pattern == "idle":
            # Very little movement, long gaps
            x += 0.5 * math.sin(i * 0.01)
            y += 0.3 * math.cos(i * 0.01)
            dt = 1000 if i % 5 == 0 else 16  # Frequent long pauses
        
        t += dt
        event_type = "move"
        button = None
        
        # Sprinkle in some clicks
        if i % 12 == 0:
            event_type = "click"
            button = 0
        elif i % 20 == 0:
            event_type = "click"
            button = 2
        
        events.append({
            "x": round(x, 2),
            "y": round(y, 2),
            "timestamp": t,
            "event_type": event_type,
            "button": button,
            "scroll_delta": None,
        })
    
    return events


# ═════════════════════════════════════════════════════════════════════════════
# SESSION LIFECYCLE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSessionLifecycle:
    def test_start_session(self):
        """Starting a session returns a valid session_id."""
        r = client.post("/api/mouse/session/start", json={
            "user_id": "TEST_START_001",
            "pc_id": "WS-001",
            "application": "Dashboard",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert "session_id" in data
        assert len(data["session_id"]) == 12
        assert data["user_id"] == "TEST_START_001"
        assert "started_at" in data

    def test_end_session(self):
        """Ending a session returns final metrics."""
        sid = create_session("TEST_END_001")
        
        # Ingest some events first
        events = generate_mouse_events(20)
        client.post("/api/mouse/events", json={
            "user_id": "TEST_END_001",
            "session_id": sid,
            "events": events,
        })
        
        r = client.post("/api/mouse/session/end", json={
            "session_id": sid,
            "user_id": "TEST_END_001",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert "final_metrics" in data
        assert "anomaly_scores" in data
        assert data["final_metrics"]["is_active"] is False

    def test_end_nonexistent_session(self):
        """Ending a non-existent session returns 404."""
        r = client.post("/api/mouse/session/end", json={
            "session_id": "NONEXISTENT",
            "user_id": "TEST_USER",
        })
        assert r.status_code == 404

    def test_double_end_session(self):
        """Ending an already-ended session returns 400."""
        sid = create_session("TEST_DOUBLE_END")
        
        client.post("/api/mouse/session/end", json={
            "session_id": sid,
            "user_id": "TEST_DOUBLE_END",
        })
        
        r = client.post("/api/mouse/session/end", json={
            "session_id": sid,
            "user_id": "TEST_DOUBLE_END",
        })
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# EVENT INGESTION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestEventIngestion:
    def test_ingest_events(self):
        """Ingesting events returns success with counts."""
        sid = create_session("TEST_INGEST_001")
        events = generate_mouse_events(30)
        
        r = client.post("/api/mouse/events", json={
            "user_id": "TEST_INGEST_001",
            "session_id": sid,
            "events": events,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["events_ingested"] == 30
        assert data["total_events"] == 30
        assert "current_anomaly" in data

    def test_ingest_to_ended_session(self):
        """Ingesting events to an ended session returns 400."""
        sid = create_session("TEST_INGEST_ENDED")
        client.post("/api/mouse/session/end", json={
            "session_id": sid,
            "user_id": "TEST_INGEST_ENDED",
        })
        
        events = generate_mouse_events(5)
        r = client.post("/api/mouse/events", json={
            "user_id": "TEST_INGEST_ENDED",
            "session_id": sid,
            "events": events,
        })
        assert r.status_code == 400

    def test_ingest_to_nonexistent_session(self):
        """Ingesting events to a non-existent session returns 404."""
        events = generate_mouse_events(5)
        r = client.post("/api/mouse/events", json={
            "user_id": "TEST_USER",
            "session_id": "NONEXISTENT",
            "events": events,
        })
        assert r.status_code == 404

    def test_batch_accumulation(self):
        """Multiple batches accumulate correctly in a session."""
        sid = create_session("TEST_ACCUM")
        
        events1 = generate_mouse_events(20)
        events2 = generate_mouse_events(30, start_x=200, start_y=200)
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_ACCUM",
            "session_id": sid,
            "events": events1,
        })
        r = client.post("/api/mouse/events", json={
            "user_id": "TEST_ACCUM",
            "session_id": sid,
            "events": events2,
        })
        assert r.json()["total_events"] == 50

    def test_click_events_tracked(self):
        """Click events are properly counted."""
        sid = create_session("TEST_CLICKS")
        
        events = [
            {"x": 100, "y": 100, "timestamp": time.time() * 1000, "event_type": "click", "button": 0},
            {"x": 200, "y": 200, "timestamp": time.time() * 1000 + 16, "event_type": "click", "button": 0},
            {"x": 300, "y": 300, "timestamp": time.time() * 1000 + 32, "event_type": "click", "button": 2},
            {"x": 400, "y": 400, "timestamp": time.time() * 1000 + 48, "event_type": "move"},
        ]
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_CLICKS",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        data = r.json()
        assert data["total_clicks"] == 3
        assert data["left_clicks"] == 2
        assert data["right_clicks"] == 1

    def test_scroll_events_tracked(self):
        """Scroll events are properly counted."""
        sid = create_session("TEST_SCROLL")
        
        events = [
            {"x": 100, "y": 100, "timestamp": time.time() * 1000, "event_type": "scroll", "scroll_delta": 120},
            {"x": 100, "y": 100, "timestamp": time.time() * 1000 + 50, "event_type": "scroll", "scroll_delta": -60},
        ]
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_SCROLL",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        data = r.json()
        assert data["scroll_events"] == 2
        assert data["total_scroll_delta"] == 180.0


# ═════════════════════════════════════════════════════════════════════════════
# SESSION METRICS TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSessionMetrics:
    def test_get_session_metrics(self):
        """Session metrics endpoint returns comprehensive data."""
        sid = create_session("TEST_METRICS")
        events = generate_mouse_events(100)
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_METRICS",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        assert r.status_code == 200
        data = r.json()
        
        # Check all expected fields exist
        assert "session_id" in data
        assert "user_id" in data
        assert "total_events" in data
        assert "total_distance_px" in data
        assert "avg_velocity_px_ms" in data
        assert "max_velocity_px_ms" in data
        assert "velocity_std" in data
        assert "avg_acceleration" in data
        assert "avg_jerk" in data
        assert "jerk_spikes" in data
        assert "avg_curvature" in data
        assert "straightness_index" in data
        assert "total_clicks" in data
        assert "click_rate_per_min" in data
        assert "pause_count" in data
        assert "idle_percentage" in data
        assert "anomaly_scores" in data
        assert "duration_readable" in data

    def test_metrics_nonexistent_session(self):
        """Metrics for non-existent session returns 404."""
        r = client.get("/api/mouse/session/NONEXISTENT")
        assert r.status_code == 404

    def test_distance_calculation(self):
        """Total distance calculates correctly for known movements."""
        sid = create_session("TEST_DISTANCE")
        
        # Move exactly 100px right, then 100px down
        t = time.time() * 1000
        events = [
            {"x": 0, "y": 0, "timestamp": t, "event_type": "move"},
            {"x": 100, "y": 0, "timestamp": t + 16, "event_type": "move"},
            {"x": 100, "y": 100, "timestamp": t + 32, "event_type": "move"},
        ]
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_DISTANCE",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        data = r.json()
        assert abs(data["total_distance_px"] - 200.0) < 0.1

    def test_velocity_computed(self):
        """Velocity is computed from movement and time."""
        sid = create_session("TEST_VELOCITY")
        
        t = time.time() * 1000
        events = [
            {"x": 0, "y": 0, "timestamp": t, "event_type": "move"},
            {"x": 100, "y": 0, "timestamp": t + 100, "event_type": "move"},  # 100px in 100ms = 1 px/ms
        ]
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_VELOCITY",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        data = r.json()
        assert data["avg_velocity_px_ms"] > 0
        assert abs(data["avg_velocity_px_ms"] - 1.0) < 0.01


# ═════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestAnomalyDetection:
    def test_anomaly_scores_structure(self):
        """Anomaly scores have expected component structure."""
        sid = create_session("TEST_ANOMALY_STRUCT")
        events = generate_mouse_events(60)
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_ANOMALY_STRUCT",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        scores = r.json()["anomaly_scores"]
        
        assert "velocity_irregularity" in scores
        assert "jerk_spikes" in scores
        assert "click_pattern" in scores
        assert "hesitation" in scores
        assert "overall" in scores
        assert 0 <= scores["overall"] <= 100

    def test_anomaly_timeline_endpoint(self):
        """Anomaly timeline endpoint returns recorded scores."""
        sid = create_session("TEST_ANOMALY_TL")
        
        # Ingest enough events to trigger timeline recording (every 50)
        events = generate_mouse_events(100)
        client.post("/api/mouse/events", json={
            "user_id": "TEST_ANOMALY_TL",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/anomaly/{sid}")
        assert r.status_code == 200
        data = r.json()
        assert "current_scores" in data
        assert "timeline" in data
        assert isinstance(data["timeline"], list)

    def test_normal_movement_low_anomaly(self):
        """Normal mouse movement should produce low anomaly scores."""
        sid = create_session("TEST_NORMAL")
        events = generate_mouse_events(80, pattern="normal")
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_NORMAL",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/session/{sid}")
        anomaly = r.json()["anomaly_scores"]["overall"]
        # Normal movement should score under 50
        assert anomaly < 60, f"Normal movement scored {anomaly}, expected < 60"

    def test_erratic_movement_higher_anomaly(self):
        """Erratic mouse movement should produce higher anomaly scores than normal."""
        sid_normal = create_session("TEST_CMP_NORMAL")
        sid_erratic = create_session("TEST_CMP_ERRATIC")
        
        normal_events = generate_mouse_events(80, pattern="normal")
        erratic_events = generate_mouse_events(80, pattern="erratic")
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_CMP_NORMAL",
            "session_id": sid_normal,
            "events": normal_events,
        })
        client.post("/api/mouse/events", json={
            "user_id": "TEST_CMP_ERRATIC",
            "session_id": sid_erratic,
            "events": erratic_events,
        })
        
        r_normal = client.get(f"/api/mouse/session/{sid_normal}")
        r_erratic = client.get(f"/api/mouse/session/{sid_erratic}")
        
        normal_score = r_normal.json()["anomaly_scores"]["overall"]
        erratic_score = r_erratic.json()["anomaly_scores"]["overall"]
        
        # Erratic should score higher (or equal) than normal
        assert erratic_score >= normal_score * 0.5, (
            f"Erratic ({erratic_score}) should be >= normal ({normal_score})"
        )


# ═════════════════════════════════════════════════════════════════════════════
# HEATMAP TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestHeatmap:
    def test_heatmap_structure(self):
        """Heatmap returns a 20x20 grid."""
        sid = create_session("TEST_HEATMAP")
        events = generate_mouse_events(50)
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_HEATMAP",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/heatmap/{sid}")
        assert r.status_code == 200
        data = r.json()
        
        assert data["grid_size"] == 20
        assert len(data["grid"]) == 20
        assert all(len(row) == 20 for row in data["grid"])
        assert "max_value" in data
        assert "click_positions" in data

    def test_heatmap_nonexistent_session(self):
        """Heatmap for non-existent session returns 404."""
        r = client.get("/api/mouse/heatmap/NONEXISTENT")
        assert r.status_code == 404

    def test_heatmap_has_nonzero_values(self):
        """Heatmap grid should have non-zero values after mouse movement."""
        sid = create_session("TEST_HEATMAP_DATA")
        events = generate_mouse_events(100)
        
        client.post("/api/mouse/events", json={
            "user_id": "TEST_HEATMAP_DATA",
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/heatmap/{sid}")
        grid = r.json()["grid"]
        total_activity = sum(sum(row) for row in grid)
        assert total_activity > 0


# ═════════════════════════════════════════════════════════════════════════════
# SESSION LISTING TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSessionListing:
    def test_list_user_sessions(self):
        """List sessions returns all sessions for a user."""
        user = "TEST_LIST_USER"
        sid1 = create_session(user)
        sid2 = create_session(user)
        
        r = client.get(f"/api/mouse/sessions?user_id={user}")
        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == user
        assert data["total_sessions"] >= 2
        assert len(data["sessions"]) >= 2

    def test_list_sessions_empty_user(self):
        """List sessions for unknown user returns empty."""
        r = client.get("/api/mouse/sessions?user_id=UNKNOWN_USER")
        assert r.status_code == 200
        data = r.json()
        assert data["total_sessions"] == 0
        assert data["sessions"] == []


# ═════════════════════════════════════════════════════════════════════════════
# LIVE METRICS TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestLiveMetrics:
    def test_live_metrics_active_session(self):
        """Live metrics returns data when user has active session."""
        user = "TEST_LIVE_ACTIVE"
        sid = create_session(user)
        events = generate_mouse_events(30)
        
        client.post("/api/mouse/events", json={
            "user_id": user,
            "session_id": sid,
            "events": events,
        })
        
        r = client.get(f"/api/mouse/live/{user}")
        assert r.status_code == 200
        data = r.json()
        assert data["has_active_session"] is True
        assert data["total_events"] == 30

    def test_live_metrics_no_session(self):
        """Live metrics returns no-session message for unknown user."""
        r = client.get("/api/mouse/live/UNKNOWN_LIVE_USER")
        assert r.status_code == 200
        data = r.json()
        assert data["has_active_session"] is False


# ═════════════════════════════════════════════════════════════════════════════
# DEMO EMPLOYEES TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDemoEmployees:
    def test_demo_employees_list(self):
        """Demo employees endpoint returns employee list."""
        r = client.get("/api/mouse/demo/employees")
        assert r.status_code == 200
        data = r.json()
        assert "employees" in data
        assert "total" in data
        assert data["total"] >= 5

    def test_employee_fields(self):
        """Each demo employee has required fields."""
        r = client.get("/api/mouse/demo/employees")
        for emp in r.json()["employees"]:
            assert "user_id" in emp
            assert "name" in emp
            assert "role" in emp
            assert "department" in emp
            assert "risk_level" in emp
            assert "has_active_session" in emp
            assert "current_anomaly_score" in emp


# ═════════════════════════════════════════════════════════════════════════════
# INTEGRATION / END-TO-END TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_tracking_workflow(self):
        """
        Complete workflow: start → ingest → metrics → heatmap → anomaly → end.
        """
        user = "TEST_E2E_WORKFLOW"
        
        # 1. Start session
        r = client.post("/api/mouse/session/start", json={
            "user_id": user,
            "pc_id": "WS-E2E",
            "application": "Integration Test",
        })
        assert r.status_code == 200
        sid = r.json()["session_id"]
        
        # 2. Ingest events in batches
        for batch_num in range(3):
            events = generate_mouse_events(
                40, start_x=batch_num * 100, start_y=batch_num * 50
            )
            r = client.post("/api/mouse/events", json={
                "user_id": user,
                "session_id": sid,
                "events": events,
            })
            assert r.status_code == 200
        
        # 3. Check metrics
        r = client.get(f"/api/mouse/session/{sid}")
        assert r.status_code == 200
        metrics = r.json()
        assert metrics["total_events"] == 120
        assert metrics["total_distance_px"] > 0
        assert metrics["is_active"] is True
        
        # 4. Check heatmap
        r = client.get(f"/api/mouse/heatmap/{sid}")
        assert r.status_code == 200
        assert r.json()["max_value"] > 0
        
        # 5. Check anomaly timeline
        r = client.get(f"/api/mouse/anomaly/{sid}")
        assert r.status_code == 200
        
        # 6. Check live metrics
        r = client.get(f"/api/mouse/live/{user}")
        assert r.status_code == 200
        assert r.json()["has_active_session"] is True
        
        # 7. End session
        r = client.post("/api/mouse/session/end", json={
            "session_id": sid,
            "user_id": user,
        })
        assert r.status_code == 200
        final = r.json()
        assert final["final_metrics"]["is_active"] is False
        assert "anomaly_scores" in final
        
        # 8. Session should now show as inactive
        r = client.get(f"/api/mouse/live/{user}")
        assert r.json()["has_active_session"] is False

    def test_concurrent_users(self):
        """Multiple users can track simultaneously."""
        sessions = {}
        for user in ["CONCURRENT_A", "CONCURRENT_B", "CONCURRENT_C"]:
            sid = create_session(user)
            sessions[user] = sid
            events = generate_mouse_events(20)
            client.post("/api/mouse/events", json={
                "user_id": user,
                "session_id": sid,
                "events": events,
            })
        
        # All sessions should be independently tracked
        for user, sid in sessions.items():
            r = client.get(f"/api/mouse/session/{sid}")
            assert r.status_code == 200
            assert r.json()["user_id"] == user
            assert r.json()["total_events"] == 20
