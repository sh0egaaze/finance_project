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
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
BACKEND_MODEL_DIR = os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "anomaly_detector")
os.makedirs(BACKEND_MODEL_DIR, exist_ok=True)

# Сделаем импорт из общей папки проекта, но для удобства опишем здесь
class FinanceVAE(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, latent_dim=8):
        super().__init__()
        self.input_dim = input_dim
        self.encoder = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.BatchNorm1d(hidden_dim), nn.GELU(), nn.Linear(hidden_dim, hidden_dim // 2), nn.GELU())
        self.fc_mu = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim // 2, latent_dim)
        self.decoder = nn.Sequential(nn.Linear(latent_dim, hidden_dim // 2), nn.GELU(), nn.Linear(hidden_dim // 2, hidden_dim), nn.BatchNorm1d(hidden_dim), nn.GELU(), nn.Linear(hidden_dim, input_dim))

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        return mu + torch.randn_like(std) * std

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decoder(z), mu, logvar

def vae_loss(recon_x, x, mu, logvar):
    mse = nn.MSELoss()(recon_x, x)
    kld = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return mse + 0.001 * kld # Небольшой вес для KLD

def train():
    print("📂 Загрузка 100,000 транзакций...")
    df = pd.read_csv("data/transactions.csv")
    
    cat_cols = ['category', 'city', 'device']
    num_cols = ['amount', 'hour_sin', 'hour_cos', 'is_weekend', 'user_avg_amount', 'amount_zscore']
    
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
        
    scaler = StandardScaler()
    X_num = scaler.fit_transform(df[num_cols])
    X = np.hstack([X_num, df[cat_cols].values])
    y = df['is_fraud'].values

    print("🌲 Обучение Isolation Forest...")
    iso = IsolationForest(contamination=0.035, random_state=42, n_jobs=-1)
    iso.fit(X[y == 0])
    joblib.dump(iso, os.path.join(BACKEND_MODEL_DIR, "isolation_forest.joblib"))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    X_train = torch.FloatTensor(X[y == 0]).to(device)
    loader = DataLoader(TensorDataset(X_train, X_train), batch_size=512, shuffle=True)
    
    model = FinanceVAE(X.shape[1]).to(device)
    optimizer = optim.Adam(model.parameters(), lr=2e-3)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.5)
    
    print(f"🧠 Обучение VAE на {device} (20 эпох)...")
    for epoch in range(20):
        model.train()
        pbar = tqdm(loader, desc=f"Epoch {epoch+1}")
        for bx, _ in pbar:
            recon, mu, logvar = model(bx)
            loss = vae_loss(recon, bx, mu, logvar)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            pbar.set_postfix(loss=f"{loss.item():.6f}", lr=f"{optimizer.param_groups[0]['lr']:.5f}")
        scheduler.step()

    # Считаем порог
    model.eval()
    with torch.no_grad():
        recon, _, _ = model(X_train)
        errors = torch.mean((X_train - recon)**2, dim=1)
        threshold = np.percentile(errors.cpu().numpy(), 96) # Чуть агрессивнее

    print(f"\n🎯 Порог VAE: {threshold:.6f}")
    torch.save(model.state_dict(), os.path.join(BACKEND_MODEL_DIR, "autoencoder.pt"))
    with open(os.path.join(BACKEND_MODEL_DIR, "meta.pkl"), "wb") as f:
        pickle.dump({"scaler": scaler, "encoders": encoders, "threshold": threshold, "input_dim": X.shape[1], "num_cols": num_cols, "cat_cols": cat_cols}, f)
    print(f"✅ Готово!")

if __name__ == "__main__":
    train()
