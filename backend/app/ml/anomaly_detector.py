import os
import torch
import numpy as np
import pickle
import joblib
from dataclasses import dataclass
from typing import Optional
from .model_definition import TransactionAutoencoder

class AnomalyDetector:
    def __init__(self, model_dir: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Загрузка метаданных (скалер, энкодеры, порог)
        with open(os.path.join(model_dir, "meta.pkl"), "rb") as f:
            self.meta = pickle.load(f)
        
        # Загрузка VAE
        self.ae = TransactionAutoencoder(self.meta["input_dim"]).to(self.device)
        self.ae.load_state_dict(torch.load(os.path.join(model_dir, "autoencoder.pt"), map_location=self.device))
        self.ae.eval()
        
        # Загрузка Isolation Forest
        self.iso = joblib.load(os.path.join(model_dir, "isolation_forest.joblib"))
        self.threshold = self.meta["threshold"]

    def detect(self, tx: dict) -> dict:
        try:
            # 1. Подготовка фичей
            # Добавляем sin/cos часа для лучшей работы с цикличностью времени
            hour = tx.get("hour", 12)
            tx["hour_sin"] = np.sin(2 * np.pi * hour / 24)
            tx["hour_cos"] = np.cos(2 * np.pi * hour / 24)
            
            # Числовые фичи через скалер
            X_num = self.meta["scaler"].transform([[tx.get(c, 0) for c in self.meta["num_cols"]]])
            
            # Категориальные фичи через LabelEncoder
            X_cat = []
            for col in self.meta["cat_cols"]:
                val = tx.get(col, "unknown")
                le = self.meta["encoders"][col]
                if val in le.classes_:
                    X_cat.append(le.transform([val])[0])
                else:
                    X_cat.append(-1)
            
            X = np.hstack([X_num, [X_cat]])
            
            # 2. Ошибка VAE (Нейросеть)
            X_torch = torch.FloatTensor(X).to(self.device)
            with torch.no_grad():
                # VAE возвращает (recon, mu, logvar), берем только реконструкцию
                recon, _, _ = self.ae(X_torch)
                err = torch.mean((X_torch - recon)**2).item()
            
            # 3. Вердикт
            is_ae_fraud = err > self.threshold
            is_iso_fraud = self.iso.predict(X)[0] == -1
            
            is_suspicious = is_ae_fraud or is_iso_fraud
            
            return {
                "is_suspicious": bool(is_suspicious),
                "anomaly_score": round(float(err / (self.threshold + 1e-9)), 4),
                "reason": self._generate_reason(tx, is_ae_fraud, is_iso_fraud),
                "details": {
                    "vae_error": round(err, 6),
                    "threshold": round(float(self.threshold), 6),
                    "iso_forest_fraud": bool(is_iso_fraud)
                }
            }
        except Exception as e:
            return {"is_suspicious": False, "error": str(e)}

    def _generate_reason(self, tx, ae, iso):
        """Твоя оригинальная логика объяснения причин (восстановлена)"""
        if not ae and not iso: 
            return "Транзакция выглядит нормальной"
            
        reasons = []
        amount = tx.get("amount", 0)
        avg = tx.get("user_avg_amount", 0)
        
        if avg > 0 and amount > avg * 5:
            reasons.append(f"Сумма ({amount:,.0f}₽) значительно выше вашей средней ({avg:,.0f}₽)")
        
        if ae: 
            reasons.append("Нетипичный паттерн транзакции (VAE)")
            
        if iso: 
            reasons.append("Аномальное сочетание параметров (Isolation Forest)")
            
        return "; ".join(reasons)

def detect_anomaly(tx: dict) -> dict:
    from .model_loader import registry
    det = registry.get("anomaly_detector")
    if not det: 
        return {"is_suspicious": False, "error": "Detector not loaded"}
    return det.detect(tx)

@dataclass
class AnomalyResult:
    is_suspicious: bool
    anomaly_score: float = 0.0
    reason: str = ""
    details: dict = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> dict:
        result = {"is_suspicious": self.is_suspicious}
        if self.error:
            result["error"] = self.error
        else:
            result.update({
                "anomaly_score": self.anomaly_score,
                "reason": self.reason,
                "details": self.details,
            })
        return result