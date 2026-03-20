import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import polars as pl
import joblib
import os
import sys
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from lstm_autoencoder import LSTMAutoencoder
from baseline import BaselineAnomalyDetector

# Robust path handling
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/master_timeline.parquet")
MODEL_DIR_BASELINE = os.path.join(PROJECT_ROOT, "models/baseline")
MODEL_DIR_LSTM = os.path.join(PROJECT_ROOT, "models/lstm")

# Config (Must match training)
SEQ_LEN = 10
HIDDEN_DIM = 32
NUM_LAYERS = 2

def load_data():
    if not os.path.exists(PROCESSED_DATA_PATH):
        print(f"Error: Data file not found at {PROCESSED_DATA_PATH}")
        sys.exit(1)
    
    df_pl = pl.read_parquet(PROCESSED_DATA_PATH)
    df = df_pl.to_pandas()
    return df

def evaluate_baseline(df):
    print("\n--- Evaluating Baseline (Isolation Forest) ---")
    model_path = os.path.join(MODEL_DIR_BASELINE, "isolation_forest.joblib")
    if not os.path.exists(model_path):
        print("Model not found.")
        return

    # Load Model
    detector = BaselineAnomalyDetector(model_type="isolation_forest")
    detector.load(model_path)
    
    # Preprocess (Same as training)
    # Note: In a real prod pipeline, we should reuse a saved pipeline/transformer
    df['hour'] = df['date'].dt.hour
    df['day_of_week'] = df['date'].dt.dayofweek
    features = ['hour', 'day_of_week']
    
    # We need to scale. Ideally use the SAME scaler from training.
    # For baseline training, I created a scaler locally and didn't save it (my bad in train_baseline.py).
    # For now, fit_transform again (approximation for this demo)
    scaler = StandardScaler()
    X = scaler.fit_transform(df[features])

    # Predict
    # decision_function: lower = more anomalous
    scores = detector.decision_function(X)
    
    # Thresholding
    # IF returns scores around 0. Negative is anomaly.
    # Let's say -0.1 is threshold? Or dynamic?
    threshold = scores.mean() - 2 * scores.std()
    print(f"Score Stats: Mean={scores.mean():.4f}, Std={scores.std():.4f}")
    print(f"Dynamic Threshold (Mean - 2*Std): {threshold:.4f}")
    
    y_pred = (scores < threshold).astype(int)
    
    # Ground Truth
    # We know U105 is the "Insider Threat" (generator.py)
    # Specifically, they did "Data Exfiltration" (File Copy with to_removable_media=True)
    # Let's mark ANY activity by U105 after Day 25 as anomaly for strict testing,
    # OR better: mark specific malicious events if we can infer them.
    # The generator didn't flag the rows in 'master_timeline', but we can infer:
    
    # Logic from generator:
    # "if uid == "U105" and day > 25: -> Exfiltration"
    # But wait, generated data doesn't have explicit "is_anomaly" column in final parquet.
    # We'll heuristic it: User U105 AND activity='File Copy' AND date > 25th day
    
    start_date = df['date'].min()
    # Days > 25
    is_threat_time = (df['date'] - start_date).dt.days > 25
    is_u105 = df['user'] == 'U105'
    
    # Actually, the generator marks specific file copies. 
    # But in the normalized data, we might have lost "to_removable_media" logic unless we join back?
    # Wait, normalization.py just selects common cols. Source='File' might be enough context if we had feature.
    # For Baseline features (hour, day), it likely won't catch file copy semantics. 
    # It might catch "Off hours" work if U105 did it at night.
    
    # Let's define Ground Truth as: U105 doing weird stuff late at night OR just U105 in general during attack phase.
    y_true = (is_u105 & is_threat_time).astype(int)
    
    print(f"Ground Truth Anomalies: {y_true.sum()}")
    print(f"Detected Anomalies: {y_pred.sum()}")
    
    if y_true.sum() > 0:
        prec = precision_score(y_true, y_pred)
        rec = recall_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        print(f"Precision: {prec:.4f}")
        print(f"Recall:    {rec:.4f}")
        print(f"F1 Score:  {f1:.4f}")
    else:
        print("No ground truth anomalies (check data generation logic).")

def create_sequences_with_labels(df, seq_len, scaler):
    sequences = []
    labels = []
    
    # Need to reproduce features
    df['hour'] = df['date'].dt.hour
    df['day_of_week'] = df['date'].dt.dayofweek
    source_map = {k: v for v, k in enumerate(df['source'].unique())}
    df['source_idx'] = df['source'].map(source_map)
    feature_cols = ['hour', 'day_of_week', 'source_idx']
    
    # Scale
    df[feature_cols] = scaler.transform(df[feature_cols])
    
    # Ground Truth Logic
    start_date = df['date'].min()
    is_threat_time = (df['date'] - start_date).dt.days > 25
    is_u105 = df['user'] == 'U105'
    df['is_anomaly'] = (is_u105 & is_threat_time).astype(int)
    
    for user, group in df.groupby('user'):
        data = group[feature_cols].values
        lbls = group['is_anomaly'].values
        
        if len(data) < seq_len:
            continue
            
        for i in range(len(data) - seq_len + 1):
            seq = data[i:i+seq_len]
            # If ANY event in window is anomaly, mark window as anomaly? Or majority?
            # Usually ANY.
            label = 1 if np.any(lbls[i:i+seq_len]) else 0
            
            sequences.append(seq)
            labels.append(label)
            
    return np.array(sequences), np.array(labels)



def evaluate_lstm(df):
    print("\n--- Evaluating LSTM Autoencoder ---", flush=True)
    model_path = os.path.join(MODEL_DIR_LSTM, "lstm_ae.pth")
    scaler_path = os.path.join(MODEL_DIR_LSTM, "scaler.joblib")
    
    if not os.path.exists(model_path):
        print("LSTM Model not found.", flush=True)
        return
        
    print("Loading Scaler...", flush=True)
    scaler = joblib.load(scaler_path)
    
    print("Creating Sequences...", flush=True)
    X_seq, y_true = create_sequences_with_labels(df, SEQ_LEN, scaler)
    print(f"Sequences created: {len(X_seq)}", flush=True)
    if len(X_seq) == 0:
        print("No sequences.", flush=True)
        return
        
    X_tensor = torch.FloatTensor(X_seq)
    
    print("Loading Model...", flush=True)
    input_dim = X_seq.shape[2]
    model = LSTMAutoencoder(input_dim=input_dim, hidden_dim=HIDDEN_DIM, num_layers=NUM_LAYERS)
    model.load_state_dict(torch.load(model_path, map_location='cpu', weights_only=True))
    model.eval()
    
    print("Predicting...", flush=True)
    loss_fn = nn.MSELoss(reduction='none')
    with torch.no_grad():
        reconstructed = model(X_tensor)
        diff = (X_tensor - reconstructed) ** 2
        anomaly_scores = diff.mean(dim=(1, 2)).numpy()
        
    print("Calculating Metrics...", flush=True)
    mean_score = np.mean(anomaly_scores)
    std_score = np.std(anomaly_scores)
    
    threshold = mean_score + 2 * std_score
    print(f"Score Stats: Mean={mean_score:.4f}, Std={std_score:.4f}", flush=True)
    print(f"Dynamic Threshold (Mean + 2*Std): {threshold:.4f}", flush=True)
    
    y_pred = (anomaly_scores > threshold).astype(int)
    
    print(f"Ground Truth Anomalies: {y_true.sum()}", flush=True)
    print(f"Detected Anomalies: {y_pred.sum()}", flush=True)
    
    if y_true.sum() > 0:
        prec = precision_score(y_true, y_pred)
        rec = recall_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred)
        auc = roc_auc_score(y_true, anomaly_scores)
        print(f"Precision: {prec:.4f}", flush=True)
        print(f"Recall:    {rec:.4f}", flush=True)
        print(f"F1 Score:  {f1:.4f}", flush=True)
        print(f"ROC AUC:   {auc:.4f}", flush=True)
    else:
        print("No ground truth anomalies.", flush=True)

if __name__ == "__main__":
    main_df = load_data()
    
    # Quick fix for source column in baseline eval if needed, 
    # but evaluate_baseline does its own simplified process for now.
    
    evaluate_baseline(main_df.copy())
    evaluate_lstm(main_df.copy())
