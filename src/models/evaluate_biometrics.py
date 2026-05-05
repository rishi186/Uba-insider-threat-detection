import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import os
import sys
import logging
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
sys.path.insert(0, PROJECT_ROOT)

from src.models.train_biometrics import PhysicsCNN, SEQUENCE_LENGTH, create_sequences

logger = logging.getLogger("uba.models.eval_biometrics")

DATA_PATH = os.path.join(PROJECT_ROOT, "data/raw/mouse_biometrics_1hz.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models/biometrics/biometrics_cnn.pth")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data/risk_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def evaluate_mouse_biometrics():
    if not os.path.exists(DATA_PATH) or not os.path.exists(MODEL_PATH):
        logger.error("Missing data or trained model. Run data generation and training first.")
        return

    logger.info("Loading edge-telemetry physics sequences for batch evaluation...")
    df = pd.read_csv(DATA_PATH)

    features = ['avg_velocity', 'max_acceleration', 'jerk', 'click_count']
    
    # We fit a new scaler here on all data just for inference standardizing
    # In production, you would save the scaler object from training.
    scaler = StandardScaler()
    df[features] = scaler.fit_transform(df[features])
    
    # Needs a way to link sequences back to users
    user_scores = []
    
    model = PhysicsCNN(input_dim=len(features))
    model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
    model.eval()
    criterion = nn.MSELoss(reduction='none')

    logger.info("Calculating reconstruction error (Biometric Imposter Score)...")
    
    with torch.no_grad():
        for user_id, group in df.groupby('user'):
            group = group.sort_values('timestamp')
            
            # Group by day so we get daily scores
            group['day'] = pd.to_datetime(group['timestamp']).dt.date
            
            for day, day_group in group.groupby('day'):
                data = day_group[features].values
                if len(data) < SEQUENCE_LENGTH:
                    continue
                
                # Create sequences for this specific day/user
                seqs = []
                for i in range(len(data) - SEQUENCE_LENGTH):
                    seqs.append(data[i:i+SEQUENCE_LENGTH])
                
                tensor_x = torch.tensor(np.array(seqs), dtype=torch.float32)
                
                # Autoencoder output
                output = model(tensor_x)
                
                # Calculate mean squared error across features and seq length
                loss = criterion(output, tensor_x)
                
                # The mean loss for all sequences that day for that user
                daily_loss = loss.mean().item()
                
                user_scores.append({
                    "user": user_id,
                    "date": str(day),
                    "biometric_anomaly_score": daily_loss
                })

    scores_df = pd.DataFrame(user_scores)
    
    # Normalize the loss into a manageable 0-10 score range
    if len(scores_df) > 0:
        base_mean = scores_df['biometric_anomaly_score'].mean()
        base_std = scores_df['biometric_anomaly_score'].std()
        
        # Z-score normalization clamped at 0
        scores_df['biometric_z_score'] = (scores_df['biometric_anomaly_score'] - base_mean) / (base_std + 1e-6)
        scores_df['biometric_z_score'] = scores_df['biometric_z_score'].clip(lower=0)
    
    output_path = os.path.join(OUTPUT_DIR, "biometric_scores.csv")
    scores_df.to_csv(output_path, index=False)
    logger.info(f"Saved completed Biometric Risk Scores to {output_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    evaluate_mouse_biometrics()
