import pandas as pd
import numpy as np
import os
import sys
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.config import config

logger = logging.getLogger("uba.data_pipeline.mouse_generator_edge")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data/raw")
os.makedirs(DATA_DIR, exist_ok=True)

# Configuration
data_gen_cfg = config.get('data_generation', {})
NUM_USERS = data_gen_cfg.get('num_users', 100)
DAYS_TO_SIMULATE = data_gen_cfg.get('days_to_simulate', 30)
START_DATE = datetime(2024, 1, 1)

INSIDER_THREAT_USER = data_gen_cfg.get('insider_threat_user', 'U105')
INSIDER_THREAT_START_DAY = data_gen_cfg.get('insider_threat_start_day', 25)

# Simulate edge computing: we pretend the mouse is tracked at 60Hz locally
# but we only OUTPUT a 1-second string of mathematical summaries.
SESSIONS_PER_DAY = 5
SESSION_DURATION_SECONDS = 60 # Send sixty 1-second payloads per session

def generate_edge_telemetry():
    telemetry_logs = []
    logger.info("Generating Edge-Computed mouse biometric summaries (1Hz)...")

    for day in range(DAYS_TO_SIMULATE):
        date = START_DATE + timedelta(days=day)
        if date.weekday() >= 5 and np.random.rand() > 0.1: # Skip most weekends
            continue

        for user_id in range(100, 100 + NUM_USERS):
            uid = f"U{user_id}"
            
            # Base Biometric Profile (different users have different base physics)
            base_speed = 50 + (user_id % 50) * 2  # px/sec
            erraticness = 0.1 + (user_id % 10) * 0.05 # randomness 0.1 - 0.6
            base_jerk = 0.05 + (user_id % 5) * 0.02
            
            # Anomaly injection: "Imposter at Keyboard"
            if uid == INSIDER_THREAT_USER and day >= INSIDER_THREAT_START_DAY:
                base_speed = 300 # Imposter moves much faster
                erraticness = 1.8 # Highly erratic, unfamiliar UI layout
                base_jerk = 0.8  # Jumpy hand movements

            for _ in range(SESSIONS_PER_DAY):
                session_start = date + timedelta(hours=np.random.randint(8, 18), minutes=np.random.randint(0, 59))
                
                for second in range(SESSION_DURATION_SECONDS):
                    t = (session_start + timedelta(seconds=second)).isoformat()
                    
                    # Instead of generating 60 rows, we generate the edge-computed statistical payload for this 1 second.
                    avg_velocity = np.random.normal(loc=base_speed, scale=base_speed*0.1)
                    max_acceleration = np.random.normal(loc=base_speed*1.5, scale=base_speed*0.2)
                    jerk_metric = abs(np.random.normal(loc=base_jerk, scale=base_jerk*0.5))
                    
                    # 5% chance the user clicked in this 1-second window
                    clicks = 1 if np.random.rand() < 0.05 else 0
                    
                    # Zero out motion if they are reading/inactive for this second
                    if np.random.rand() < 0.2: 
                        avg_velocity, max_acceleration, jerk_metric = 0.0, 0.0, 0.0
                        
                    telemetry_logs.append([
                        uid, 
                        f"PC-{user_id}",
                        t, 
                        round(max(0, avg_velocity), 2), 
                        round(max(0, max_acceleration), 2), 
                        round(max(0, jerk_metric), 4),
                        clicks
                    ])

    logger.info(f"Generated {len(telemetry_logs)} 1-second boundary payloads.")
    
    # Save standard CSV metric file
    output_path = os.path.join(DATA_DIR, "mouse_biometrics_1hz.csv")
    df = pd.DataFrame(telemetry_logs, columns=["user", "pc", "timestamp", "avg_velocity", "max_acceleration", "jerk", "click_count"])
    df.to_csv(output_path, index=False)
    logger.info(f"Saved lightweight telemetry to {output_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    np.random.seed(42)
    generate_edge_telemetry()
