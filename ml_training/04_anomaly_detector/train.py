"""
Обучение детектора аномалий (Autoencoder + Isolation Forest).
Фичи: amount, hour_sin, hour_cos, is_weekend, user_avg_amount, amount_ratio, category
"""
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
from sklearn.metrics import classification_report
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
BACKEND_MODEL_DIR = os.path.join(
    PROJECT_DIR, "backend", "app", "ml", "trained_models", "anomaly_detector"
)
os.makedirs(BACKEND_MODEL_DIR, exist_ok=True)

# ── Архитектура ────────────────────────────────────────────
class TransactionAutoencoder(nn.Module):
    """Автоэнкодер для аномалий (должен совпадать с model_definition.py)"""
    def __init__(self, input_dim, hidden=48, latent=10):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.BatchNorm1d(hidden),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, hidden // 2),
            nn.GELU(),
        )
        self.fc_mu     = nn.Linear(hidden // 2, latent)
        self.fc_logvar = nn.Linear(hidden // 2, latent)
        self.decoder = nn.Sequential(
            nn.Linear(latent, hidden // 2),
            nn.GELU(),
            nn.Linear(hidden // 2, hidden),
            nn.BatchNorm1d(hidden),
            nn.GELU(),
            nn.Linear(hidden, input_dim),
        )

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


def vae_loss(recon, x, mu, logvar):
    mse = nn.MSELoss()(recon, x)
    kld = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return mse + 0.0005 * kld


# ── Главная функция ────────────────────────────────────────
def train():
    print("📂 Загрузка датасета...")
    df = pd.read_csv("data/transactions.csv")

    # ---------- фичи ТОЧНО как в anomaly_detector.detect() ----------
    num_cols = [
        'amount', 'hour_sin', 'hour_cos',
        'is_weekend', 'user_avg_amount', 'amount_ratio',
    ]
    cat_cols = ['category']

    # Кодируем категории
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df[col + '_enc'] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
        print(f"   {col} → {list(le.classes_)}")

    # Нормализуем числовые
    scaler = StandardScaler()
    X_num = scaler.fit_transform(df[num_cols].values)
    X_cat = df[[c + '_enc' for c in cat_cols]].values
    X = np.hstack([X_num, X_cat]).astype(np.float32)
    y = df['is_fraud'].values

    input_dim = X.shape[1]
    print(f"\n   input_dim = {input_dim}  (num={len(num_cols)}, cat={len(cat_cols)})")
    print(f"   Normal: {(y==0).sum()},  Fraud: {(y==1).sum()}")

    # ── Isolation Forest ──────────────────────────────────
    print("\n🌲 Isolation Forest...")
    iso = IsolationForest(
        n_estimators=300,
        contamination=0.04,
        max_features=0.8,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X[y == 0])
    joblib.dump(iso, os.path.join(BACKEND_MODEL_DIR, "isolation_forest.joblib"))
    iso_pred = (iso.predict(X) == -1).astype(int)
    print(f"   ISO found anomalies: {iso_pred.sum()}")

    # ── VAE Autoencoder ───────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n🧠 VAE Autoencoder  (device={device})")

    X_normal = torch.FloatTensor(X[y == 0]).to(device)
    loader = DataLoader(
        TensorDataset(X_normal, X_normal),
        batch_size=512, shuffle=True,
    )

    model = TransactionAutoencoder(input_dim).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=30)

    epochs = 30
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0
        for bx, _ in loader:
            recon, mu, logvar = model(bx)
            loss = vae_loss(recon, bx, mu, logvar)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        scheduler.step()
        if epoch % 5 == 0 or epoch == 1:
            print(f"   Epoch {epoch:>2}/{epochs}  loss={epoch_loss/len(loader):.6f}"
                  f"  lr={optimizer.param_groups[0]['lr']:.5f}")

    # Порог
    model.eval()
    with torch.no_grad():
        X_all_t = torch.FloatTensor(X).to(device)
        recon, _, _ = model(X_all_t)
        errors = torch.mean((X_all_t - recon) ** 2, dim=1).cpu().numpy()

    normal_err = errors[y == 0]
    fraud_err  = errors[y == 1]
    threshold  = float(np.percentile(normal_err, 97))

    print(f"\n🎯 Threshold: {threshold:.6f}")
    print(f"   Normal errors:  mean={normal_err.mean():.6f}  "
          f"p50={np.median(normal_err):.6f}  p99={np.percentile(normal_err,99):.6f}")
    print(f"   Fraud  errors:  mean={fraud_err.mean():.6f}  "
          f"p50={np.median(fraud_err):.6f}  min={fraud_err.min():.6f}")

    ae_pred = (errors > threshold).astype(int)

    # ── Комбинированный результат ─────────────────────────
    combined = ((iso_pred == 1) | (ae_pred == 1)).astype(int)
    print(f"\n📋 Результаты на всём датасете:")
    print(classification_report(y, combined,
          target_names=['Normal', 'Fraud'], digits=3))

    # ── Сохранение ────────────────────────────────────────
    torch.save(model.state_dict(),
               os.path.join(BACKEND_MODEL_DIR, "autoencoder.pt"))

    meta = {
        "scaler":    scaler,
        "encoders":  encoders,
        "threshold": threshold,
        "input_dim": input_dim,
        "num_cols":  num_cols,
        "cat_cols":  cat_cols,
    }
    with open(os.path.join(BACKEND_MODEL_DIR, "meta.pkl"), "wb") as f:
        pickle.dump(meta, f)

    print(f"\n✅ Модели сохранены в {BACKEND_MODEL_DIR}")


if __name__ == "__main__":
    train()