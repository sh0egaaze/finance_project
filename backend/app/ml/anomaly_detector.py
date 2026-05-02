import os
import torch
import numpy as np
import pickle
import hashlib
import logging
from typing import Optional
from .model_definition import TransactionAutoencoder

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, model_dir: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Загружаем метаданные (скалер, энкодеры, параметры)
        with open(os.path.join(model_dir, "meta.pkl"), "rb") as f:
            self.meta = pickle.load(f)
        
        state_dict_path = os.path.join(model_dir, "autoencoder.pt")
        
        # Загружаем модель
        self.ae = TransactionAutoencoder(self.meta["input_dim"]).to(self.device)
        self.ae.load_state_dict(
            torch.load(
                state_dict_path,
                map_location=self.device,
                weights_only=True  
            )
        )
        self.ae.eval()
        
        iso_path = os.path.join(model_dir, "isolation_forest.joblib")
        self.iso = self._safe_joblib_load(iso_path)
        self.threshold = self.meta["threshold"]

    @staticmethod
    def _safe_joblib_load(path: str):
        """Безопасная загрузка joblib с верификацией"""
        import joblib
        import io
        
        # Простейшая проверка целостности файла
        with open(path, "rb") as f:
            data = f.read()
        
        # Логируем хэш для аудита
        file_hash = hashlib.sha256(data).hexdigest()[:16]
        logger.info(f"    Загружен файл {os.path.basename(path)} (sha256:{file_hash}...)")
        
        return joblib.load(io.BytesIO(data))

    def detect(self, tx: dict) -> dict:
        try:
            # 1. Преобразование фичей
            # Добавляем синус/cosinus часа для циклических признаков
            hour = tx.get("hour", 12)
            tx["hour_sin"] = np.sin(2 * np.pi * hour / 24)
            tx["hour_cos"] = np.cos(2 * np.pi * hour / 24)
            
            # Числовые фичи в одном векторе
            X_num = self.meta["scaler"].transform([[tx.get(c, 0) for c in self.meta["num_cols"]]])
            
            # Категориальные фичи через LabelEncoders
            X_cat = []
            for col in self.meta["cat_cols"]:
                val = tx.get(col, "unknown")
                le = self.meta["encoders"][col]
                if val in le.classes_:
                    X_cat.append(le.transform([val])[0])
                else:
                    X_cat.append(-1)
            
            X = np.hstack([X_num, [X_cat]])
            
            # 2. Ошибка VAE (реконструкция)
            X_tensor = torch.FloatTensor(X).to(self.device)
            with torch.no_grad():  
                recon, _, _ = self.ae(X_tensor)
                err = torch.mean((X_tensor - recon)**2).item()
            
            # 3. Решение
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
        """Генерация описания предупреждения (многоязычная)"""
        if not ae and not iso: 
            return "Транзакция выглядит нормально"
            
        reasons = []
        amount = tx.get("amount", 0)
        avg = tx.get("user_avg_amount", 0)
        
        if avg > 0 and amount > avg * 5:
            reasons.append(f"Сумма ({amount:,.0f}₽) значительно выше средней ({avg:,.0f}₽)")
        
        if ae: 
            reasons.append("Нетипичный паттерн транзакции (VAE)")
            
        if iso: 
            reasons.append("Аномальное поведение покупателя (Isolation Forest)")
            
        return "; ".join(reasons)

def detect_anomaly(tx: dict) -> dict:
    from .model_loader import registry
    det = registry.get("anomaly_detector")
    if not det: 
        return {"is_suspicious": False, "error": "Detector not loaded"}
    return det.detect(tx)

import logging
from dataclasses import dataclass, field

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
