"""
Central data-access layer for the API.
- TTL-based in-memory caching for CSV data
- Proper structured logging (no print statements)
- Defensive data parsing
"""

import pandas as pd
import os
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.api.config import settings

logger = logging.getLogger("uba.data_loader")


# =============================================================================
# CACHE
# =============================================================================
class _Cache:
    """Simple TTL-based in-memory cache."""

    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def get(self, key: str):
        ts = self._timestamps.get(key)
        if ts is not None and (time.time() - ts) < self.ttl:
            return self._store.get(key)
        return None

    def set(self, key: str, value):
        self._store[key] = value
        self._timestamps[key] = time.time()

    def clear(self):
        self._store.clear()
        self._timestamps.clear()
        logger.info("Data cache cleared.")


# =============================================================================
# DATA LOADER
# =============================================================================
class DataLoader:
    """Central data access layer for the API."""

    def __init__(self):
        self._cache = _Cache(ttl_seconds=settings.DATA_CACHE_TTL_SECONDS)

    def clear_cache(self):
        """Public method for admin endpoint."""
        self._cache.clear()

    # ── CSV Loading ──────────────────────────────────────────────────────────
    def _load_csv(self, filename: str, directory: str = None) -> Optional[pd.DataFrame]:
        """Load a CSV file, with cache support."""
        dir_path = directory or settings.RISK_OUTPUT_DIR
        cache_key = f"{dir_path}/{filename}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        path = os.path.join(dir_path, filename)
        if not os.path.exists(path):
            logger.debug("File not found: %s", path)
            return None
        try:
            df = pd.read_csv(path)
            self._cache.set(cache_key, df)
            logger.debug("Loaded %s (%d rows)", filename, len(df))
            return df
        except Exception as e:
            logger.error("Error loading %s: %s", filename, e)
            return None

    # ── User Risk ────────────────────────────────────────────────────────────
    def get_users_risk_data(self, limit: int = 50, sort_desc: bool = True) -> List[dict]:
        df = self._load_csv("risk_report_users.csv")
        if df is None or df.empty:
            return []

        df = df.fillna({"total_risk_score": 0.0, "user": "Unknown"})

        if "total_risk_score" in df.columns:
            df = df.sort_values(by="total_risk_score", ascending=not sort_desc)

        return df.head(limit).to_dict(orient="records")

    # ── Single User Profile ──────────────────────────────────────────────────
    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Return risk profile for a single user, or None if not found."""
        df = self._load_csv("risk_report_users.csv")
        if df is None or df.empty or "user" not in df.columns:
            return None

        match = df[df["user"] == user_id]
        if match.empty:
            return None

        row = match.iloc[0].to_dict()
        row.setdefault("role", "Employee")
        row.setdefault("department", "General")
        score = float(row.get("total_risk_score", 0))
        row.setdefault(
            "risk_level",
            "Critical" if score > 80 else "High" if score > 50 else "Medium" if score > 25 else "Low",
        )
        # Compute rank among all users
        if "total_risk_score" in df.columns:
            ranked = df.sort_values("total_risk_score", ascending=False).reset_index(drop=True)
            rank_idx = ranked[ranked["user"] == user_id].index
            row["rank"] = int(rank_idx[0]) + 1 if len(rank_idx) > 0 else None
        return row

    # ── Event Risk ───────────────────────────────────────────────────────────
    def get_events_risk_data(self, limit: int = 100, min_score: float = 0.0) -> List[dict]:
        df = self._load_csv("risk_report_events.csv")
        if df is None or df.empty:
            return []

        df = df.fillna(0)

        if min_score > 0 and "risk_score" in df.columns:
            df = df[df["risk_score"] >= min_score]

        if "risk_score" in df.columns:
            df = df.sort_values("risk_score", ascending=False)

        return df.head(limit).to_dict(orient="records")

    # ── System Stats ─────────────────────────────────────────────────────────
    def get_system_stats(self) -> dict:
        users_df = self._load_csv("risk_report_users.csv")
        events_df = self._load_csv("risk_report_events.csv")

        stats = {
            "total_users": 0,
            "high_risk_users": 0,
            "total_events": 0,
            "high_risk_events": 0,
            "avg_risk_score": 0.0,
            "top_threat": "None",
        }

        if users_df is not None and not users_df.empty:
            stats["total_users"] = len(users_df)
            if "total_risk_score" in users_df.columns:
                stats["high_risk_users"] = int(
                    len(users_df[users_df["total_risk_score"] > 50])
                )
                stats["avg_risk_score"] = float(
                    round(users_df["total_risk_score"].mean(), 2)
                )
                stats["top_threat"] = str(
                    users_df.sort_values("total_risk_score", ascending=False).iloc[0]["user"]
                )

        if events_df is not None and not events_df.empty:
            stats["total_events"] = len(events_df)
            if "risk_score" in events_df.columns:
                stats["high_risk_events"] = int(
                    len(events_df[events_df["risk_score"] > 50])
                )

        return stats

    # ── Dashboard Summary ────────────────────────────────────────────────────
    def get_dashboard_summary(self) -> dict:
        """Combined payload for the dashboard: stats + top users + recent alerts + model health."""
        return {
            "stats": self.get_system_stats(),
            "top_risky_users": self.get_users_risk_data(limit=5),
            "recent_alerts": self.get_alerts(limit=5).get("alerts", []),
            "models": self.get_model_status(),
        }

    # ── User Timeline ────────────────────────────────────────────────────────
    def get_user_timeline(
        self, user_id: str, limit: int = 200, offset: int = 0
    ) -> dict:
        """Load and return the event timeline for a specific user."""
        events_df = self._load_csv("risk_report_events.csv")

        # Fallback to master timeline
        if events_df is None or events_df.empty:
            timeline_path = os.path.join(
                settings.PROCESSED_DATA_DIR, "master_timeline.parquet"
            )
            if os.path.exists(timeline_path):
                try:
                    events_df = pd.read_parquet(timeline_path)
                except Exception:
                    events_df = None

        if events_df is None or events_df.empty:
            return {"user_id": user_id, "total_events": 0, "anomaly_count": 0, "events": []}

        user_col = "user" if "user" in events_df.columns else None
        if user_col is None:
            return {"user_id": user_id, "total_events": 0, "anomaly_count": 0, "events": []}

        user_events = events_df[events_df[user_col] == user_id].copy()
        if user_events.empty:
            return {"user_id": user_id, "total_events": 0, "anomaly_count": 0, "events": []}

        anomaly_threshold = 50.0

        timeline = []
        for _, row in user_events.iterrows():
            ts = str(row.get("date", row.get("timestamp", "")))
            risk = float(row.get("risk_score", 0))
            anomaly_score = float(row.get("anomaly_score", risk / 100.0))

            event = {
                "timestamp": ts,
                "event_type": str(row.get("source", "Unknown")),
                "activity": str(row.get("activity", "Unknown")),
                "anomaly_score": round(anomaly_score, 4),
                "risk_score": round(risk, 2),
                "is_anomaly": risk > anomaly_threshold,
                "pc": str(row.get("pc", "")) if "pc" in row.index else None,
                "details": None,
            }
            timeline.append(event)

        # Sort descending
        timeline.sort(key=lambda x: x["timestamp"], reverse=True)

        total = len(timeline)
        anomaly_count = sum(1 for e in timeline if e["is_anomaly"])

        # Paginate
        paginated = timeline[offset: offset + limit]

        return {
            "user_id": user_id,
            "total_events": total,
            "anomaly_count": anomaly_count,
            "events": paginated,
        }

    # ── Alerts ───────────────────────────────────────────────────────────────
    def get_alerts(
        self,
        severity: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Load alerts with optional filtering."""
        df = self._load_csv("alerts.csv")

        # Fallback: generate alerts from high-risk events
        if df is None or df.empty:
            events_df = self._load_csv("risk_report_events.csv")
            if events_df is None or events_df.empty:
                return {"total": 0, "offset": offset, "limit": limit, "alerts": []}

            high_risk = pd.DataFrame()
            if "risk_score" in events_df.columns:
                high_risk = events_df[events_df["risk_score"] > 50].copy()

            if high_risk.empty:
                return {"total": 0, "offset": offset, "limit": limit, "alerts": []}

            high_risk = high_risk.sort_values("risk_score", ascending=False)
            df = high_risk.reset_index()
            df["alert_id"] = [f"ALT-{i + 1:04d}" for i in range(len(df))]
            df["severity"] = df["risk_score"].apply(
                lambda s: "Critical" if s > 90 else "High" if s > 70 else "Medium"
            )
            df["status"] = "open"

        # Apply filters
        if severity and "severity" in df.columns:
            df = df[df["severity"].str.lower() == severity.lower()]

        if user_id and "user" in df.columns:
            df = df[df["user"] == user_id]

        if status and "status" in df.columns:
            df = df[df["status"].str.lower() == status.lower()]

        total = len(df)
        df = df.iloc[offset: offset + limit]

        alerts = []
        for _, row in df.iterrows():
            alert = {
                "alert_id": str(row.get("alert_id", f"ALT-{_}")),
                "user": str(row.get("user", "Unknown")),
                "severity": str(row.get("severity", "Medium")),
                "risk_score": float(row.get("risk_score", 0)),
                "activity": str(row.get("activity", None)) if "activity" in row.index else None,
                "timestamp": str(row.get("date", row.get("timestamp", "")))
                    if "date" in row.index or "timestamp" in row.index else None,
                "status": str(row.get("status", "open")),
                "mitre_tactic": str(row.get("mitre_tactic", None)) if "mitre_tactic" in row.index else None,
                "mitre_technique": str(row.get("mitre_technique", None)) if "mitre_technique" in row.index else None,
            }
            alerts.append(alert)

        return {"total": total, "offset": offset, "limit": limit, "alerts": alerts}

    # ── Model Status ─────────────────────────────────────────────────────────
    def get_model_status(self) -> dict:
        """Check model files and return metadata."""
        model_entries = [
            {"name": "LSTM Autoencoder", "path": os.path.join(settings.MODELS_DIR, "lstm", "lstm_ae.pth")},
            {"name": "LSTM Scaler", "path": os.path.join(settings.MODELS_DIR, "lstm", "scaler.joblib")},
            {"name": "Isolation Forest", "path": os.path.join(settings.MODELS_DIR, "baseline", "isolation_forest.joblib")},
            {"name": "XGBoost (Hybrid)", "path": os.path.join(settings.MODELS_DIR, "hybrid", "xgboost.joblib")},
            {"name": "Bi-LSTM Attention (Hybrid)", "path": os.path.join(settings.MODELS_DIR, "hybrid", "bilstm.pth")},
        ]

        models_list = []
        available = 0
        for entry in model_entries:
            exists = os.path.exists(entry["path"])
            info = {
                "name": entry["name"],
                "path": entry["path"],
                "exists": exists,
                "size_bytes": None,
                "last_modified": None,
            }
            if exists:
                available += 1
                stat = os.stat(entry["path"])
                info["size_bytes"] = stat.st_size
                info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            models_list.append(info)

        # Load evaluation metrics
        eval_metrics = None
        eval_path = os.path.join(settings.RISK_OUTPUT_DIR, "evaluation_results.json")
        if not os.path.exists(eval_path):
            eval_path = os.path.join(
                os.path.dirname(settings.RISK_OUTPUT_DIR), "evaluation_results_full.txt"
            )
        if os.path.exists(eval_path):
            try:
                with open(eval_path, "r") as f:
                    eval_metrics = f.read()
            except Exception:
                pass

        return {
            "models": models_list,
            "total_models": len(models_list),
            "available_models": available,
            "evaluation_summary": eval_metrics,
        }


data_loader = DataLoader()
