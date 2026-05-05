"""
Risk Scoring Engine — Model-Aware Thresholding with Explainability & MITRE Mapping.

Features:
  - Uses TRAINED model thresholds (from metadata JSON) instead of hardcoded values
  - Z-score based anomaly detection: only flags events significantly above threshold
  - Threat-discriminating feature multipliers (file_copy, USB, confidential files)
  - Alert logic with persistence and cooldown
  - MITRE ATT&CK mapping

Consolidated as the canonical implementation.
"""

import pandas as pd
import numpy as np
import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.config import config

logger = logging.getLogger("uba.risk_engine.scoring")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
MODEL_DIR = os.path.join(PROJECT_ROOT, "models/lstm")


@dataclass
class RiskExplanation:
    """Structured explanation for why an event was flagged."""
    primary_factor: str
    factors: List[str]
    mitre_tactic: str
    mitre_technique: str
    text_explanation: str
    risk_score: float


class AlertManager:
    """
    Manages alert generation with persistence and cooldown logic.
    Thresholds are read from config.yaml → alerting section.
    """

    def __init__(self):
        self.alert_config = config.alerting
        self.medium_threshold = self.alert_config.get('medium_threshold', 70)
        self.high_threshold = self.alert_config.get('high_threshold', 85)
        self.critical_threshold = self.alert_config.get('critical_threshold', 95)
        self.persistence_count = self.alert_config.get('persistence_count', 2)
        self.cooldown_hours = self.alert_config.get('cooldown_hours', 24)

        # Track user alert state
        self.user_high_risk_counts: Dict[str, int] = {}
        self.user_last_alert: Dict[str, datetime] = {}

    def should_generate_alert(self, user: str, risk_score: float, event_time: datetime) -> Tuple[bool, str]:
        """
        Determine if an alert should be generated based on persistence and cooldown.

        Returns:
            Tuple of (should_alert, severity)
        """
        if risk_score >= self.critical_threshold:
            severity = "CRITICAL"
        elif risk_score >= self.high_threshold:
            severity = "HIGH"
        elif risk_score >= self.medium_threshold:
            severity = "MEDIUM"
        else:
            self.user_high_risk_counts[user] = 0
            return False, ""

        # Check cooldown
        last_alert = self.user_last_alert.get(user)
        if last_alert:
            hours_since = (event_time - last_alert).total_seconds() / 3600
            if hours_since < self.cooldown_hours:
                if severity != "CRITICAL":
                    return False, ""

        # Check persistence
        current_count = self.user_high_risk_counts.get(user, 0) + 1
        self.user_high_risk_counts[user] = current_count

        if current_count >= self.persistence_count:
            self.user_last_alert[user] = event_time
            self.user_high_risk_counts[user] = 0
            return True, severity

        return False, ""

    def get_alert_stats(self) -> Dict:
        """Return current alert state statistics."""
        return {
            'users_in_warning': len([u for u, c in self.user_high_risk_counts.items() if c > 0]),
            'users_in_cooldown': len(self.user_last_alert),
        }


class AdvancedRiskScoringEngine:
    """
    Model-aware risk scoring with explainability and MITRE mapping.

    Uses trained model thresholds from metadata files to properly calibrate
    anomaly detection. Only anomalies significantly above the trained P99.5
    threshold generate meaningful risk scores.
    """

    def __init__(self):
        self.risk_config = config.risk_scoring
        self.mitre_mapping = config.mitre_mapping
        self.features_config = config.features

        self.role_multipliers = self.risk_config.get('role_multipliers', {
            'Admin': 1.5, 'Contractor': 1.2, 'Employee': 1.0
        })
        self.activity_multipliers = self.risk_config.get('activity_multipliers', {})
        self.after_hours_mult = self.risk_config.get('after_hours_multiplier', 1.5)
        self.max_risk = self.risk_config.get('max_risk', 100)

        self.work_start = self.features_config.get('work_start_hour', 7)
        self.work_end = self.features_config.get('work_end_hour', 20)

        # User metadata cache
        self.user_roles: Dict[str, str] = {}
        self.alert_manager = AlertManager()

        # Model-aware thresholds (loaded from metadata)
        self.model_thresholds: Dict[str, Dict] = {}
        self._load_model_thresholds()

        logger.info(
            "RiskScoringEngine initialised — roles=%s, work_hours=%d-%d, model_thresholds=%s",
            list(self.role_multipliers.keys()), self.work_start, self.work_end,
            list(self.model_thresholds.keys()),
        )

    def _load_model_thresholds(self):
        """Load trained model thresholds from metadata JSON files."""
        for role in ['employee', 'admin', 'contractor', 'global']:
            metadata_path = os.path.join(MODEL_DIR, f"metadata_{role}.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.model_thresholds[role] = json.load(f)
                logger.info(
                    "Loaded threshold for %s: mean=%.4f, std=%.4f, threshold=%.4f",
                    role,
                    self.model_thresholds[role].get('error_mean', 0),
                    self.model_thresholds[role].get('error_std', 0),
                    self.model_thresholds[role].get('threshold', 0),
                )

    def _get_threshold_for_user(self, user: str) -> Dict:
        """Get the appropriate threshold metadata for a user based on role."""
        role = self.user_roles.get(user, 'Employee').lower()
        if role in self.model_thresholds:
            return self.model_thresholds[role]
        if 'global' in self.model_thresholds:
            return self.model_thresholds['global']
        # Fallback
        return {'error_mean': 0.6, 'error_std': 0.6, 'threshold': 3.5}

    def load_user_metadata(self, users_path: str) -> None:
        """Load user role metadata from CSV."""
        if os.path.exists(users_path):
            users_df = pd.read_csv(users_path)
            self.user_roles = dict(zip(users_df['id'], users_df['role']))
            logger.info("Loaded metadata for %d users.", len(self.user_roles))

    def calculate_risk_score(
        self,
        row: pd.Series,
        anomaly_score: float,
        model_type: str = "lstm"
    ) -> Tuple[float, RiskExplanation]:
        """
        Calculate risk score with model-aware thresholding and full explainability.

        Returns:
            Tuple of (risk_score, RiskExplanation)
        """
        factors = []
        user = row.get('user', '')

        # ── 1. LSTM Anomaly Score (Model-Aware) ────────────────────────────
        base_risk = self._calculate_base_risk(anomaly_score, model_type, user)
        if base_risk > 5:
            factors.append(f"Anomaly score {anomaly_score:.3f}")

        # ── 2. Threat-Discriminating Feature Boosts ────────────────────────
        threat_risk = 0.0

        # File Copy events (STRONGEST signal for data exfiltration)
        file_copies = row.get('file_copy_count', 0)
        if file_copies > 0:
            # Even 1 file copy is unusual; 20 is an exfiltration
            threat_risk += min(50, file_copies * 3.0)
            factors.append(f"File copy activity ({int(file_copies)} copies)")

        # Removable media / USB
        to_removable = row.get('to_removable_count', 0)
        if to_removable > 0:
            threat_risk += min(40, to_removable * 2.0)
            factors.append(f"Removable media transfer ({int(to_removable)} files)")

        usb_events = row.get('usb_events', 0)
        if usb_events > 0:
            threat_risk += min(20, usb_events * 10.0)
            factors.append(f"USB device activity ({int(usb_events)} events)")

        # Confidential files
        confidential = row.get('confidential_file_count', 0)
        if confidential > 0:
            threat_risk += min(40, confidential * 2.5)
            factors.append(f"Confidential file access ({int(confidential)} files)")

        # ── 3. Role Multiplier ─────────────────────────────────────────────
        role = self.user_roles.get(user, 'Employee')
        role_mult = self.role_multipliers.get(role, 1.0)
        if role_mult > 1.0:
            factors.append(f"{role} role (+{int((role_mult-1)*100)}%)")

        # ── 4. After-Hours Multiplier ──────────────────────────────────────
        oaf = row.get('oaf', 0)
        after_hours_count = row.get('after_hours_event_count', 0)
        is_after_hours = oaf > 0.3 or after_hours_count > 3

        time_mult = 1.0
        if is_after_hours:
            time_mult = self.after_hours_mult
            factors.append(f"After-hours pattern ({oaf:.0%} of events)")

        # ── 5. Calculate Combined Risk ─────────────────────────────────────
        # Base risk from LSTM anomaly + explicit threat indicators
        combined_raw = base_risk + threat_risk

        # Apply multipliers
        final_risk = combined_raw * role_mult * time_mult

        # ── 6. Heuristic Override: Critical Threat Patterns ────────────────
        if file_copies > 5 and (usb_events > 0 or to_removable > 5):
            final_risk = max(final_risk, 90)
            if "PATTERN: Exfiltration combo" not in factors:
                factors.append("PATTERN: Exfiltration combo (copies + USB/removable)")

        if confidential > 5 and to_removable > 5:
            final_risk = max(final_risk, 95)
            factors.append("PATTERN: Confidential data exfiltration")

        final_risk = min(self.max_risk, final_risk)

        # ── 7. MITRE Mapping ───────────────────────────────────────────────
        activity = ""
        if file_copies > 0:
            activity = "File Copy"
        elif usb_events > 0:
            activity = "Connect"
        mitre = self._get_mitre_mapping(activity, is_after_hours)

        # ── 8. Build Explanation ───────────────────────────────────────────
        primary_factor = factors[0] if factors else "Normal activity"
        text_explanation = self._build_explanation(final_risk, factors, mitre)

        explanation = RiskExplanation(
            primary_factor=primary_factor,
            factors=factors,
            mitre_tactic=mitre.get('tactic', ''),
            mitre_technique=mitre.get('technique', ''),
            text_explanation=text_explanation,
            risk_score=final_risk
        )

        return final_risk, explanation

    def _calculate_base_risk(self, anomaly_score: float, model_type: str, user: str = '') -> float:
        """
        Convert raw anomaly score to base risk (0-100) using MODEL-AWARE thresholding.
        
        Only scores significantly above the trained P99.5 threshold generate risk.
        Uses Z-score relative to the model's trained error distribution.
        """
        if model_type == "lstm":
            threshold_meta = self._get_threshold_for_user(user)
            
            error_mean = threshold_meta.get('error_mean', 0.6)
            error_std = threshold_meta.get('error_std', 0.6)
            trained_threshold = threshold_meta.get('threshold', 3.5)
            
            if anomaly_score <= 0:
                return 0.0
            
            # Calculate Z-score relative to trained distribution
            if error_std > 0:
                z_score = (anomaly_score - error_mean) / error_std
            else:
                z_score = 0.0
            
            # Only generate risk if z_score indicates a strong anomaly
            # Z > 3.0 = notable, Z > 4.0 = strong, Z > 5.0 = extreme
            if z_score <= 3.0:
                return 0.0  # Within 3-sigma of normal distribution
            
            # Scale: z=3→5, z=4→15, z=5→30, z=6→50, z=7→70
            base = min(100, max(0, (z_score - 3.0) * 15.0))
            
            # Bonus if above the absolute trained threshold (P99.5)
            if anomaly_score > trained_threshold:
                above_thresh = (anomaly_score - trained_threshold) / max(trained_threshold, 0.1)
                base = min(100, base + above_thresh * 25)
            
            return base

        elif model_type == "baseline":
            if anomaly_score < 0:
                return min(100, abs(anomaly_score) * 400)
            return 0

        return 0

    def _get_mitre_mapping(self, activity: str, is_after_hours: bool) -> Dict:
        """Get MITRE ATT&CK mapping for activity."""
        if "Logon" in activity and is_after_hours:
            mapping = self.mitre_mapping.get('After Hours Logon', {})
            if mapping:
                return mapping

        for pattern, mapping in self.mitre_mapping.items():
            if pattern in activity:
                return mapping

        return {}

    def _build_explanation(self, risk: float, factors: List[str], mitre: Dict) -> str:
        """Build human-readable explanation."""
        if risk < 30:
            return "Low risk - normal activity pattern."

        explanation = f"Risk score {risk:.0f}/100. "

        if factors:
            explanation += "Contributing factors: " + "; ".join(factors[:4]) + ". "

        if mitre:
            explanation += f"Maps to MITRE {mitre.get('tactic', '')} - {mitre.get('tactic_name', '')}."

        return explanation

    def process_dataframe(
        self,
        df: pd.DataFrame,
        anomaly_scores: np.ndarray
    ) -> pd.DataFrame:
        """
        Process entire dataframe with risk scoring and explainability.

        Returns:
            DataFrame with risk_score and explanation columns
        """
        risk_scores = []
        explanations = []
        mitre_tactics = []
        should_alerts = []
        alert_severities = []

        for idx, row in df.iterrows():
            score_idx = min(idx, len(anomaly_scores) - 1)
            anomaly = anomaly_scores[score_idx] if len(anomaly_scores) > 0 else 0

            risk, explanation = self.calculate_risk_score(row, anomaly)

            risk_scores.append(risk)
            explanations.append(explanation.text_explanation)
            mitre_tactics.append(explanation.mitre_tactic)

            event_time = row.get('date', datetime.now())
            should_alert, severity = self.alert_manager.should_generate_alert(
                row['user'], risk, event_time
            )
            should_alerts.append(should_alert)
            alert_severities.append(severity)

        df['risk_score'] = risk_scores
        df['explanation'] = explanations
        df['mitre_tactic'] = mitre_tactics
        df['should_alert'] = should_alerts
        df['alert_severity'] = alert_severities

        return df


# ── Backward-compatible aliases ──────────────────────────────────────────────
RiskScoringEngine = AdvancedRiskScoringEngine

# Global singleton instances
alert_manager = AlertManager()
risk_engine = AdvancedRiskScoringEngine()
