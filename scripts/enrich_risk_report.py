"""
Enrich risk_report_users.csv with realistic mock metrics for ALL users.
This makes all 125 users visible in the frontend with full profiles.
Run: python scripts/enrich_risk_report.py
"""

import pandas as pd
import numpy as np
import os
import random

random.seed(42)
np.random.seed(42)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

RISK_REPORT_PATH = os.path.join(PROJECT_ROOT, "data", "risk_output", "risk_report_users.csv")
USERS_CSV_PATH   = os.path.join(PROJECT_ROOT, "data", "raw", "users.csv")
OUTPUT_PATH      = RISK_REPORT_PATH  # overwrite in place

# ── Load base data ─────────────────────────────────────────────────────────────
risk_df  = pd.read_csv(RISK_REPORT_PATH)
users_df = pd.read_csv(USERS_CSV_PATH)

print(f"Risk report: {len(risk_df)} users | users.csv: {len(users_df)} users")

# ── Merge with users metadata ─────────────────────────────────────────────────
# users.csv columns: id, role, dept, pc
merged = risk_df.merge(
    users_df.rename(columns={"id": "user"}),
    on="user",
    how="left"
)

# ── Helper: classify risk level ────────────────────────────────────────────────
def classify_risk(score):
    if score >= 80:   return "Critical"
    if score >= 50:   return "High"
    if score >= 25:   return "Medium"
    return "Low"

# ── Enrich with mock metric columns ───────────────────────────────────────────
departments = ["Engineering", "Finance", "HR", "Sales", "IT", "Legal", "Executive", "Marketing", "Operations", "Research"]
locations   = ["New York", "San Francisco", "Austin", "Chicago", "Seattle", "London", "Remote"]

rows = []
for _, row in merged.iterrows():
    uid   = row["user"]
    score = float(row.get("total_risk_score", 0))
    role  = row.get("role", "Employee")
    dept  = row.get("dept", random.choice(departments))

    risk_level = classify_risk(score)

    # Seed per-user randomness deterministically
    user_seed = int(uid.replace("U", "")) if uid.startswith("U") else 0
    rng = np.random.RandomState(user_seed)

    # ── Login / session patterns ───────────────────────────────────────────
    avg_login_hour = rng.normal(9.0, 1.5)  # normal users 8-10am
    if score >= 80:  # critical: late-night
        avg_login_hour = rng.uniform(1.0, 4.0)
    elif score >= 50:  # high: after-hours
        avg_login_hour = rng.uniform(19.0, 23.0)

    avg_session_duration = max(1.0, rng.normal(7.5, 1.2))  # hours
    failed_logins = int(rng.poisson(score / 20.0))
    after_hours_logins = int(rng.poisson(max(0.1, (score - 20) / 10.0)))

    # ── File activity ──────────────────────────────────────────────────────
    file_copies       = int(rng.poisson(score / 8.0))
    usb_events        = int(rng.poisson(max(0.1, score / 15.0)))
    confidential_files = int(rng.poisson(max(0.1, score / 12.0)))
    total_file_ops    = int(rng.normal(50, 20)) + file_copies * 3

    # ── HTTP ────────────────────────────────────────────────────────────────
    suspicious_urls  = int(rng.poisson(max(0.1, score / 25.0)))
    total_http       = int(rng.normal(120, 40))
    external_domains = int(rng.poisson(max(1, score / 30.0)))

    # ── Email ───────────────────────────────────────────────────────────────
    large_emails     = int(rng.poisson(max(0.1, score / 20.0)))
    external_emails  = int(rng.poisson(max(1, score / 25.0)))

    # ── Anomaly ────────────────────────────────────────────────────────────
    anomaly_score  = round(min(1.0, score / 100.0 + rng.normal(0, 0.05)), 4)
    zscore         = round(max(0.0, (score / 100.0 * 6.0) + rng.normal(0, 0.3)), 3)
    is_drift       = bool(row.get("is_drift", score >= 50))
    deviation_sigma = round(float(row.get("deviation_sigma", zscore)), 3)
    mitre_tactics  = []
    if file_copies > 0:   mitre_tactics.append("TA0010-Exfiltration")
    if suspicious_urls > 0: mitre_tactics.append("TA0011-C2")
    if after_hours_logins > 0: mitre_tactics.append("TA0006-CredentialAccess")
    if usb_events > 0:    mitre_tactics.append("T1200-HardwareAdditions")

    # ── Last active ─────────────────────────────────────────────────────────
    days_since_active = int(rng.uniform(0, 5))
    last_active = f"2024-03-{max(1, 30 - days_since_active):02d}"

    rows.append({
        "user":               uid,
        "role":               role if pd.notna(role) else "Employee",
        "department":         dept[:30] if pd.notna(dept) else random.choice(departments),
        "pc":                 row.get("pc", f"PC-{user_seed}"),
        "location":           random.choice(locations),
        "total_risk_score":   round(score, 2),
        "max_risk":           round(float(row.get("max_risk", score)), 2),
        "event_count":        int(row.get("event_count", total_file_ops + total_http)),
        "risk_level":         risk_level,
        "anomaly_score":      anomaly_score,
        "deviation_sigma":    deviation_sigma,
        "is_drift":           is_drift,
        "drift_explanation":  str(row.get("drift_explanation", "")),
        # Login
        "avg_login_hour":     round(avg_login_hour % 24, 1),
        "avg_session_duration_hrs": round(avg_session_duration, 1),
        "failed_logins":      failed_logins,
        "after_hours_logins": after_hours_logins,
        # File
        "total_file_ops":     total_file_ops,
        "file_copies":        file_copies,
        "usb_events":         usb_events,
        "confidential_files": confidential_files,
        # HTTP
        "total_http_requests": total_http,
        "suspicious_urls":    suspicious_urls,
        "external_domains":   external_domains,
        # Email
        "large_emails":       large_emails,
        "external_emails":    external_emails,
        # MITRE
        "mitre_tactics":      "|".join(mitre_tactics) if mitre_tactics else "",
        "last_active":        last_active,
    })

out_df = pd.DataFrame(rows)
out_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

print(f"\n✅ Enriched risk report written to: {OUTPUT_PATH}")
print(f"   Total users: {len(out_df)}")
print(f"   Columns:     {out_df.columns.tolist()}")
print("\nRisk Level Distribution:")
print(out_df["risk_level"].value_counts().to_string())
print("\nTop 10 by risk score:")
print(out_df.sort_values("total_risk_score", ascending=False)[["user","risk_level","total_risk_score","after_hours_logins","file_copies","usb_events"]].head(10).to_string(index=False))
