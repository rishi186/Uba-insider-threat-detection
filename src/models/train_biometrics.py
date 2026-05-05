import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
import os
import logging
from sklearn.preprocessing import StandardScaler
from torch.utils.data import TensorDataset, DataLoader

logger = logging.getLogger("uba.models.train_biometrics")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
DATA_PATH = os.path.join(PROJECT_ROOT, "data/raw/mouse_biometrics_1hz.csv")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models/biometrics")
os.makedirs(MODELS_DIR, exist_ok=True)

# Sequence configuration
SEQUENCE_LENGTH = 10 # Predict using 10 seconds of contiguous physics history
BATCH_SIZE = 64
EPOCHS = 2

class PhysicsCNN(nn.Module):
    """
    1D CNN specialized for learning continuous physics features (Velocity, Jerk) across time.
    Outputs a highly sensitive biometric embedding.
    """
    def __init__(self, input_dim=4):
        super(PhysicsCNN, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=16, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(kernel_size=2)
        self.conv2 = nn.Conv1d(in_channels=16, out_channels=32, kernel_size=3, padding=1)
        
        # Output after CNN/Pool layers for a seq length of 10
        self.fc1 = nn.Linear(32 * (SEQUENCE_LENGTH // 4), 16)
        
        # We output to the dimensional space of the input to act as an Autoencoder
        # High reconstruction error = "Imposter at Keyboard"
        self.fc2 = nn.Linear(16, input_dim * SEQUENCE_LENGTH)

    def forward(self, x):
        # x shape: (Batch, Seq, Features) -> CNN needs (Batch, Features, Seq)
        x = x.transpose(1, 2)
        
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        
        x = x.view(x.size(0), -1) # Flatten
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        
        # Reshape back to (Batch, Seq, Features)
        return x.view(x.size(0), SEQUENCE_LENGTH, -1)


def create_sequences(df, features):
    """Prepare overlap windows per user"""
    seqs = []
    for user_id, group in df.groupby('user'):
        group = group.sort_values('timestamp')
        data = group[features].values
        
        if len(data) < SEQUENCE_LENGTH:
            continue
            
        for i in range(len(data) - SEQUENCE_LENGTH):
            seqs.append(data[i:i+SEQUENCE_LENGTH])
            
    return np.array(seqs)


def train_mouse_biometrics():
    if not os.path.exists(DATA_PATH):
        logger.error(f"Cannot train biometrics. Missing edge-telemetry file: {DATA_PATH}")
        return

    logger.info("Loading edge-telemetry physics sequences...")
    df = pd.read_csv(DATA_PATH)
    
    # Exclude imposter data from baseline training
    df_train = df[~((df['user'] == 'U105') & (df['timestamp'] >= '2024-01-25'))].copy()

    features = ['avg_velocity', 'max_acceleration', 'jerk', 'click_count']
    
    scaler = StandardScaler()
    df_train[features] = scaler.fit_transform(df_train[features])
    
    sequences = create_sequences(df_train, features)
    if len(sequences) == 0:
        logger.error("Not enough data to create sequences.")
        return
        
    tensor_x = torch.tensor(sequences, dtype=torch.float32)
    dataset = TensorDataset(tensor_x, tensor_x) # Autoencoder tries to predict itself
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    model = PhysicsCNN(input_dim=len(features))
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    
    logger.info(f"Training Continuous Biometric Authentication Model on {len(sequences)} sequences...")
    
    for epoch in range(EPOCHS):
        total_loss = 0
        for batch_x, _ in dataloader:
            optimizer.zero_grad()
            output = model(batch_x)
            loss = criterion(output, batch_x)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        logger.info(f"Epoch {epoch+1}/{EPOCHS} -> Loss: {total_loss / len(dataloader):.4f}")
        
    model_path = os.path.join(MODELS_DIR, "biometrics_cnn.pth")
    torch.save(model.state_dict(), model_path)
    logger.info(f"Saved completed Biometric Model to {model_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    train_mouse_biometrics()
