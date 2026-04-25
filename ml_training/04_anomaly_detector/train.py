import os
import sys
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import pickle
import joblib
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import IsolationForest

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
BACKEND_MODEL_DIR = os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "anomaly_detector")
os.makedirs(BACKEND_MODEL_DIR, exist_ok=True)

# Импортируем модель (определим локально для обучения)
class TransactionAutoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32), nn.ReLU(),
            nn.Linear(32, 16), nn.ReLU(),
            nn.Linear(16, 8)
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16), nn.ReLU(),
            nn.Linear(16, 32), nn.ReLU(),
            nn.Linear(32, input_dim)
        )
    def forward(self, x): return self.decoder(self.encoder(x))

def train():
    df = pd.read_csv(os.path.join(BASE_DIR, "data", "transactions.csv"))
    
    # 1. Preprocessing (Файл 3)
    cat_cols = ['category', 'city', 'device']
    num_cols = ['amount', 'hour', 'day_of_week', 'account_age_days', 'user_avg_amount', 'user_std_amount', 'amount_zscore']
    
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
        
    scaler = StandardScaler()
    X_num = scaler.fit_transform(df[num_cols])
    X = np.hstack([X_num, df[cat_cols].values])
    y = df['is_fraud'].values

    # 2. Isolation Forest (Файл 5)
    iso = IsolationForest(contamination=0.035, random_state=42)
    iso.fit(X[y == 0]) # Учим только на нормальных
    joblib.dump(iso, os.path.join(BACKEND_MODEL_DIR, "isolation_forest.joblib"))

    # 3. Autoencoder (Файл 6)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    X_train = torch.FloatTensor(X[y == 0])
    loader = DataLoader(TensorDataset(X_train, X_train), batch_size=256, shuffle=True)
    
    model = TransactionAutoencoder(X.shape[1]).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    print("🚀 Обучение Autoencoder...")
    for epoch in range(10):
        for bx, _ in loader:
            recon = model(bx.to(device))
            loss = nn.MSELoss()(recon, bx.to(device))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    
    # Считаем порог (threshold)
    model.eval()
    with torch.no_grad():
        errors = torch.mean((X_train.to(device) - model(X_train.to(device)))**2, dim=1)
        threshold = np.percentile(errors.cpu().numpy(), 97)

    # Сохраняем всё в бэкенд
    torch.save(model.state_dict(), os.path.join(BACKEND_MODEL_DIR, "autoencoder.pt"))
    with open(os.path.join(BACKEND_MODEL_DIR, "meta.pkl"), "wb") as f:
        pickle.dump({
            "scaler": scaler,
            "encoders": encoders,
            "threshold": threshold,
            "input_dim": X.shape[1],
            "num_cols": num_cols,
            "cat_cols": cat_cols
        }, f)
    print(f"✅ Модели сохранены в {BACKEND_MODEL_DIR}")

if __name__ == "__main__":
    train()
