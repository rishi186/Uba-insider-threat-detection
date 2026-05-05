"""
Pydantic response schemas for the UBA ITD API.
Uses json_schema_extra for examples (Pydantic V2 compatible).
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────
class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AlertSeverity(str, Enum):
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    INVESTIGATING = "investigating"


# ── User Risk ────────────────────────────────────────────────────────────────
class UserRiskProfile(BaseModel):
    user: str = Field(..., description="Unique user identifier")
    total_risk_score: float = Field(..., ge=0, description="Aggregated risk score (0-100+)")
    max_risk: Optional[float] = Field(None, description="Max single-event risk score")
    rank: Optional[int] = Field(None, ge=1, description="Risk ranking among all users")
    role: str = Field("Employee", description="Organisational role")
    department: str = Field("General", description="Department name")
    location: Optional[str] = Field(None, description="Office location")
    pc: Optional[str] = Field(None, description="Primary workstation")
    risk_level: str = Field("Low", description="Categorical risk level")
    anomaly_score: Optional[float] = Field(None, description="Normalised anomaly score 0-1")
    deviation_sigma: Optional[float] = Field(None, description="Z-score deviation from baseline")
    is_drift: Optional[bool] = Field(None, description="Whether user is in behavioural drift")
    drift_explanation: Optional[str] = Field(None, description="Human-readable drift explanation")
    # Activity metrics
    event_count: Optional[int] = Field(None, description="Total events recorded")
    after_hours_logins: Optional[int] = Field(None, description="Login events outside work hours")
    failed_logins: Optional[int] = Field(None, description="Failed login attempts")
    avg_login_hour: Optional[float] = Field(None, description="Average login hour (0-23)")
    avg_session_duration_hrs: Optional[float] = Field(None, description="Average session length in hours")
    file_copies: Optional[int] = Field(None, description="File copy events")
    usb_events: Optional[int] = Field(None, description="USB connect/disconnect events")
    confidential_files: Optional[int] = Field(None, description="Confidential file accesses")
    total_file_ops: Optional[int] = Field(None, description="Total file operations")
    suspicious_urls: Optional[int] = Field(None, description="Suspicious URL visits")
    total_http_requests: Optional[int] = Field(None, description="Total HTTP requests")
    external_domains: Optional[int] = Field(None, description="Distinct external domains visited")
    large_emails: Optional[int] = Field(None, description="Large email sends (>500KB)")
    external_emails: Optional[int] = Field(None, description="Emails sent to external addresses")
    mitre_tactics: Optional[str] = Field(None, description="Pipe-separated MITRE tactic IDs")
    last_active: Optional[str] = Field(None, description="Last activity date")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "user": "U105", "total_risk_score": 117.1, "rank": 1,
                "role": "Employee", "department": "Engineering", "risk_level": "Critical",
                "after_hours_logins": 5, "file_copies": 8, "usb_events": 8,
            }]
        }
    }


# ── Events ───────────────────────────────────────────────────────────────────
class RiskEvent(BaseModel):
    user: str = Field(..., description="User who generated the event")
    risk_score: float = Field(..., ge=0, description="Event risk score")
    activity: Optional[str] = Field("Unknown Activity", description="Type of activity")
    timestamp: Optional[str] = Field(None, description="Event timestamp (ISO 8601)")
    details: Optional[str] = Field(None, description="Additional context")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "user": "U105", "risk_score": 73.2,
                "activity": "File Copy", "timestamp": "2025-01-15T14:30:00",
            }]
        }
    }


# ── System Stats ─────────────────────────────────────────────────────────────
class SystemStats(BaseModel):
    total_users: int = Field(..., ge=0, description="Total monitored users")
    high_risk_users: int = Field(..., ge=0, description="Users with risk score > 50")
    total_events: int = Field(..., ge=0, description="Total events processed")
    high_risk_events: int = Field(..., ge=0, description="Events with risk score > 50")
    avg_risk_score: float = Field(..., ge=0, description="Mean risk score across users")
    top_threat: str = Field("None", description="User with highest risk")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_users": 100, "high_risk_users": 12, "total_events": 5420,
                "high_risk_events": 87, "avg_risk_score": 34.7, "top_threat": "U105",
            }]
        }
    }


# ── Dashboard Summary ───────────────────────────────────────────────────────
class DashboardSummary(BaseModel):
    """Combined payload for the dashboard — reduces frontend round-trips."""
    stats: SystemStats
    top_risky_users: List[dict] = Field(default_factory=list, description="Top 5 riskiest users")
    recent_alerts: List[dict] = Field(default_factory=list, description="5 most recent alerts")
    models: dict = Field(default_factory=dict, description="Model health summary")


# ── User Timeline ────────────────────────────────────────────────────────────
class TimelineEvent(BaseModel):
    timestamp: str = Field(..., description="Event timestamp")
    event_type: str = Field(..., description="Source category")
    activity: str = Field(..., description="Activity performed")
    anomaly_score: float = Field(0.0, ge=0, le=1, description="Normalised anomaly score")
    risk_score: float = Field(0.0, ge=0, description="Absolute risk score")
    is_anomaly: bool = Field(False, description="Whether this event is flagged anomalous")
    pc: Optional[str] = Field(None, description="Workstation identifier")
    details: Optional[str] = Field(None, description="Additional context")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "timestamp": "2025-01-15", "event_type": "device", "activity": "Connect",
                "anomaly_score": 0.82, "risk_score": 78.4, "is_anomaly": True,
                "pc": "PC-0421",
            }]
        }
    }


class UserTimeline(BaseModel):
    user_id: str = Field(..., description="User identifier")
    total_events: int = Field(..., ge=0, description="Total events for this user")
    anomaly_count: int = Field(..., ge=0, description="Number of anomalous events")
    events: List[TimelineEvent]


# ── Alerts ───────────────────────────────────────────────────────────────────
class AlertItem(BaseModel):
    alert_id: str = Field(..., description="Unique alert identifier")
    user: str = Field(..., description="User associated with alert")
    severity: str = Field("Medium", description="Alert severity level")
    risk_score: float = Field(0.0, ge=0, description="Risk score triggering alert")
    activity: Optional[str] = Field(None, description="Activity type")
    timestamp: Optional[str] = Field(None, description="Alert timestamp")
    status: str = Field("open", description="Alert status")
    mitre_tactic: Optional[str] = Field(None, description="MITRE ATT&CK tactic ID")
    mitre_technique: Optional[str] = Field(None, description="MITRE ATT&CK technique ID")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "alert_id": "ALT-0001", "user": "U105", "severity": "Critical",
                "risk_score": 92.1, "activity": "File Copy", "status": "open",
                "mitre_tactic": "TA0010", "mitre_technique": "T1052",
            }]
        }
    }


class AlertsResponse(BaseModel):
    total: int = Field(..., ge=0, description="Total matching alerts")
    offset: int = Field(..., ge=0, description="Current page offset")
    limit: int = Field(..., ge=1, description="Page size")
    alerts: List[AlertItem]


# ── Model Status ─────────────────────────────────────────────────────────────
class ModelInfo(BaseModel):
    name: str = Field(..., description="Model display name")
    path: str = Field(..., description="Filesystem path to model file")
    exists: bool = Field(..., description="Whether the model file is present")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    last_modified: Optional[str] = Field(None, description="Last modification time (ISO 8601)")


class ModelsStatusResponse(BaseModel):
    models: List[ModelInfo]
    total_models: int = Field(..., ge=0, description="Total registered models")
    available_models: int = Field(..., ge=0, description="Models present on disk")


# ── Health ───────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current server time (ISO 8601)")
    features: List[str]
    rate_limit: dict


# ── Error ────────────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error category")
    detail: Optional[str] = Field(None, description="Detailed error message")
    status_code: int = Field(500, description="HTTP status code")
    request_id: Optional[str] = Field(None, description="Correlation ID for tracing")
