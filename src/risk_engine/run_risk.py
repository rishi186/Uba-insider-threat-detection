"""
Risk Pipeline — Role-Based LSTM Inference with Model-Aware Scoring.

Entry point for the complete risk scoring pipeline:
  1. Load processed data with behavioral + threat features
  2. Run inference using role-specific LSTM models
  3. Calculate risk scores using model-aware thresholds + threat features
  4. Aggregate user risk with drift detection
  5. Generate alerts and save reports

Consolidated as the canonical implementation.
"""

import pandas as pd
import numpy as np
import torch
import polars as pl
import joblib
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.lstm_autoencoder import LSTMAutoencoder
from risk_engine.scoring import AdvancedRiskScoringEngine, risk_engine
from risk_engine.aggregation import RiskAggregator, risk_aggregator
from utils.config import config

logger = logging.getLogger("uba.risk_engine.run_risk")

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/featured_timeline.parquet")
FALLBACK_DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/master_timeline.parquet")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models/lstm")
USERS_PATH = os.path.join(PROJECT_ROOT, "data/raw/users.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data/risk_output")


class RoleBasedInference:
    """Runs inference using role-specific LSTM models."""

    def __init__(self):
        self.lstm_config = config.lstm
        self.seq_len = self.lstm_config.get('sequence_length', 10)
        self.hidden_dim = self.lstm_config.get('hidden_dim', 32)
        self.num_layers = self.lstm_config.get('num_layers', 2)

        self.models: Dict[str, LSTMAutoencoder] = {}
        self.scalers: Dict[str, object] = {}
        self.metadata: Dict[str, Dict] = {}
        self.user_roles: Dict[str, str] = {}

        # LSTM features — only the columns the LSTM was trained on
        # The featured_timeline has: far, eds, iav, oaf, login_entropy, file_count, email_count
        # (threat-discriminating columns are NOT fed to LSTM, they go to risk scoring)
        self.feature_cols = [
            'far', 'eds', 'iav', 'oaf',
            'login_entropy', 'file_count', 'email_count'
        ]

    def load_models(self) -> None:
        """Load all role-specific models."""
        roles = ['employee', 'admin', 'contractor', 'global']

        for role in roles:
            model_path = os.path.join(MODEL_DIR, f"lstm_{role}.pth")
            scaler_path = os.path.join(MODEL_DIR, f"scaler_{role}.joblib")
            metadata_path = os.path.join(MODEL_DIR, f"metadata_{role}.json")

            if os.path.exists(model_path):
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        self.metadata[role] = json.load(f)
                    n_features = self.metadata[role].get('n_features', len(self.feature_cols))
                else:
                    n_features = len(self.feature_cols)

                model = LSTMAutoencoder(
                    input_dim=n_features,
                    hidden_dim=self.hidden_dim,
                    num_layers=self.num_layers
                )
                model.load_state_dict(torch.load(model_path, weights_only=True))
                model.eval()
                self.models[role] = model

                if os.path.exists(scaler_path):
                    self.scalers[role] = joblib.load(scaler_path)

                logger.info("Loaded model: %s (n_features=%d)", role, n_features)

        if not self.models:
            logger.warning("No role-specific LSTM models found. Using fallback scoring.")

    def load_user_roles(self) -> None:
        """Load user role metadata."""
        if os.path.exists(USERS_PATH):
            users_df = pd.read_csv(USERS_PATH)
            # Support both 'id' and 'user' column names
            id_col = 'id' if 'id' in users_df.columns else 'user'
            self.user_roles = dict(zip(users_df[id_col], users_df['role']))

    def get_model_for_user(self, user: str) -> tuple:
        """Get the appropriate model for a user based on their role."""
        role = self.user_roles.get(user, 'Employee').lower()

        if role in self.models:
            return self.models[role], self.scalers.get(role), self.metadata.get(role, {})

        if 'global' in self.models:
            return self.models['global'], self.scalers.get('global'), self.metadata.get('global', {})

        if self.models:
            first_role = list(self.models.keys())[0]
            return self.models[first_role], self.scalers.get(first_role), self.metadata.get(first_role, {})

        return None, None, {}

    def calculate_anomaly_scores(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate anomaly scores for all events using role-specific models."""
        self.load_models()
        self.load_user_roles()

        scores = np.zeros(len(df))
        available_cols = [c for c in self.feature_cols if c in df.columns]

        if not available_cols:
            logger.warning("No feature columns found. Using basic features.")
            if 'date' in df.columns:
                df['hour'] = pd.to_datetime(df['date']).dt.hour if df['date'].dtype == object else df['date'].dt.hour
                df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek if df['date'].dtype == object else df['date'].dt.dayofweek
            available_cols = [c for c in ['hour', 'day_of_week'] if c in df.columns]

        logger.info("LSTM features: %s", available_cols)

        for user, group in df.groupby('user'):
            model, scaler, metadata = self.get_model_for_user(user)

            if model is None:
                continue

            user_indices = group.index.tolist()
            user_data = group.sort_values('day' if 'day' in group.columns else 'date')
            features = user_data[available_cols].values.astype(np.float32)

            if len(features) < self.seq_len:
                continue

            if scaler is not None:
                try:
                    features = scaler.transform(features)
                except Exception:
                    pass  # Dimension mismatch — use raw features

            sequences = []
            seq_indices = []

            for i in range(len(features) - self.seq_len + 1):
                seq = features[i:i + self.seq_len]
                sequences.append(seq)
                seq_indices.append(user_indices[i + self.seq_len - 1])

            if not sequences:
                continue

            X = torch.FloatTensor(np.array(sequences))

            with torch.no_grad():
                reconstructed = model(X)
                errors = ((X - reconstructed) ** 2).mean(dim=(1, 2)).numpy()

            for idx, error in zip(seq_indices, errors):
                scores[idx] = error

        return scores


def run_risk_pipeline():
    """Run the complete risk scoring pipeline."""
    logger.info("=" * 60)
    logger.info("UBA & ITD Risk Pipeline (Model-Aware)")
    logger.info("=" * 60)

    # 1. Load Data
    logger.info("[1/5] Loading data...")
    if os.path.exists(PROCESSED_DATA_PATH):
        df = pd.read_parquet(PROCESSED_DATA_PATH)
        logger.info("  Loaded featured data: %d rows, columns: %s", len(df), list(df.columns))
    elif os.path.exists(FALLBACK_DATA_PATH):
        df = pl.read_parquet(FALLBACK_DATA_PATH).to_pandas()
        logger.info("  Loaded fallback data: %d events", len(df))
    else:
        logger.error("No processed data found!")
        return

    # Ensure date column exists
    if 'day' in df.columns and 'date' not in df.columns:
        df['date'] = pd.to_datetime(df['day'])
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])

    # Add day_of_week if not present (needed for LSTM features)
    if 'day_of_week' not in df.columns:
        df['day_of_week'] = df['date'].dt.dayofweek

    # 2. Run LSTM Inference
    logger.info("[2/5] Running role-based LSTM inference...")
    inference = RoleBasedInference()
    anomaly_scores = inference.calculate_anomaly_scores(df)
    df['lstm_score'] = anomaly_scores
    
    nonzero = (anomaly_scores > 0).sum()
    if nonzero > 0:
        nz_scores = anomaly_scores[anomaly_scores > 0]
        logger.info("  Anomaly scores: %d non-zero, mean=%.4f, max=%.4f",
                     nonzero, nz_scores.mean(), nz_scores.max())
    else:
        logger.info("  Anomaly scores: all zero (no LSTM model loaded?)")

    # 2.5 Load Biometric Scores (if available)
    biometric_path = os.path.join(OUTPUT_DIR, "biometric_scores.csv")
    if os.path.exists(biometric_path):
        logger.info("[2.5/5] Loading batch mouse biometric scores...")
        bio_df = pd.read_csv(biometric_path)
        bio_df['date_str'] = pd.to_datetime(bio_df['date']).dt.date.astype(str)
        df['date_str'] = df['date'].dt.date.astype(str)
        
        # Merge on user and date
        df = df.merge(bio_df[['user', 'date_str', 'biometric_z_score']], on=['user', 'date_str'], how='left')
        df['biometric_z_score'] = df['biometric_z_score'].fillna(0.0)
    else:
        df['biometric_z_score'] = 0.0

    # 3. Calculate Risk Scores
    logger.info("[3/5] Calculating risk scores with model-aware thresholds...")
    risk_engine.load_user_metadata(USERS_PATH)

    risk_scores = []
    explanations = []
    mitre_tactics = []
    should_alerts = []
    alert_severities = []

    for idx, row in df.iterrows():
        lstm_score = row['lstm_score']
        risk, explanation = risk_engine.calculate_risk_score(row, lstm_score)
        
        # Apply Edge Computing Biometrics multiplier
        bio_score = row.get('biometric_z_score', 0.0)
        if bio_score > 1.5:
            risk = min(100.0, risk * 3.0) 
            explanation.text_explanation += f" | BIOMETRIC IMPOSTER ALERT (z={bio_score:.2f})"
            if "Account Takeover" not in explanation.mitre_tactic:
                explanation.mitre_tactic += ", Account Takeover"

        risk_scores.append(risk)
        explanations.append(explanation.text_explanation)
        mitre_tactics.append(explanation.mitre_tactic)

        event_time = row.get('date', datetime.now())
        should_alert, severity = risk_engine.alert_manager.should_generate_alert(
            row['user'], risk, event_time
        )
        should_alerts.append(should_alert)
        alert_severities.append(severity)

    df['risk_score'] = risk_scores
    df['explanation'] = explanations
    df['mitre_tactic'] = mitre_tactics
    df['should_alert'] = should_alerts
    df['alert_severity'] = alert_severities

    high_risk_count = (df['risk_score'] > 50).sum()
    alert_count = df['should_alert'].sum()
    logger.info("  High-risk events (>50): %d / %d (%.1f%%)",
                high_risk_count, len(df), high_risk_count / len(df) * 100)
    logger.info("  Alerts generated: %d", alert_count)

    # Risk score distribution
    logger.info("  Risk distribution: mean=%.1f, median=%.1f, P95=%.1f, P99=%.1f",
                df['risk_score'].mean(), df['risk_score'].median(),
                df['risk_score'].quantile(0.95), df['risk_score'].quantile(0.99))

    # 4. Aggregate User Risk
    logger.info("[4/5] Aggregating user risk with drift detection...")
    user_risk_df = risk_aggregator.aggregate_all_users(df)

    drift_users = user_risk_df[user_risk_df['is_drift'] == True]
    logger.info("  Users with behavioral drift: %d / %d", len(drift_users), len(user_risk_df))

    # 5. Save Reports
    logger.info("[5/5] Saving reports...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    events_path = os.path.join(OUTPUT_DIR, "risk_report_events.csv")
    df.to_csv(events_path, index=False)

    users_path = os.path.join(OUTPUT_DIR, "risk_report_users.csv")
    user_risk_df.to_csv(users_path, index=False)

    alerts_df = df[df['should_alert'] == True][
        ['date', 'user', 'risk_score', 'alert_severity', 'explanation', 'mitre_tactic']
    ]
    alerts_path = os.path.join(OUTPUT_DIR, "alerts.csv")
    alerts_df.to_csv(alerts_path, index=False)

    logger.info("  Saved: %s", events_path)
    logger.info("  Saved: %s", users_path)
    logger.info("  Saved: %s", alerts_path)

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("  Total Events: %d", len(df))
    logger.info("  Total Users: %d", len(user_risk_df))
    logger.info("  High-Risk Events: %d (%.1f%%)", high_risk_count, high_risk_count / len(df) * 100)
    logger.info("  Alerts Generated: %d", alert_count)

    # Check threat user ranking
    threat_user = config.get('data_generation', {}).get('insider_threat_user', 'U105')
    threat_row = user_risk_df[user_risk_df['user'] == threat_user]
    if not threat_row.empty:
        rank = user_risk_df.index.get_loc(threat_row.index[0]) + 1
        logger.info("  Threat User %s: Rank %d/%d, Score %.1f",
                     threat_user, rank, len(user_risk_df),
                     threat_row.iloc[0]['total_risk_score'])

    logger.info("  Top 5 Risky Users:")
    for _, row in user_risk_df.head(5).iterrows():
        drift_marker = " [DRIFT]" if row['is_drift'] else ""
        logger.info("    %s: %.1f%s", row['user'], row['total_risk_score'], drift_marker)

    return df, user_risk_df


# Backward compatibility aliases
run_risk_pipeline_v2 = run_risk_pipeline


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_risk_pipeline()
