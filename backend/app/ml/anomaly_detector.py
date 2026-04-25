import os
import torch
import numpy as np
import pickle
import joblib
from .model_definition import TransactionAutoencoder

class AnomalyDetector:
    def __init__(self, model_dir: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Загрузка меты
        with open(os.path.join(model_dir, "meta.pkl"), "rb") as f:
            self.meta = pickle.load(f)
        
        # Загрузка Autoencoder
        self.ae = TransactionAutoencoder(self.meta["input_dim"]).to(self.device)
        self.ae.load_state_dict(torch.load(os.path.join(model_dir, "autoencoder.pt"), map_location=self.device))
        self.ae.eval()
        
        # Загрузка Isolation Forest
        self.iso = joblib.load(os.path.join(model_dir, "isolation_forest.joblib"))
        
        self.threshold = self.meta["threshold"]

    def detect(self, tx: dict) -> dict:
        try:
            # Препроцессинг
            X_num = self.meta["scaler"].transform([[tx.get(c, 0) for c in self.meta["num_cols"]]])
            X_cat = []
            for col in self.meta["cat_cols"]:
                val = tx.get(col, "unknown")
                le = self.meta["encoders"][col]
                # Безопасное кодирование
                if val in le.classes_:
                    X_cat.append(le.transform([val])[0])
                else:
                    X_cat.append(-1)
            
            X = np.hstack([X_num, [X_cat]])
            
            # AE Error
            X_torch = torch.FloatTensor(X).to(self.device)
            with torch.no_grad():
                err = torch.mean((X_torch - self.ae(X_torch))**2).item()
            
            # IF Decision
            is_iso_fraud = self.iso.predict(X)[0] == -1
            is_ae_fraud = err > self.threshold
            
            is_suspicious = is_ae_fraud or is_iso_fraud
            
            return {
                "is_suspicious": bool(is_suspicious),
                "anomaly_score": round(float(err / (self.threshold + 1e-9)), 4),
                "reason": self._generate_reason(tx, is_ae_fraud, is_iso_fraud),
                "details": {"ae_error": err, "threshold": self.threshold}
            }
        except Exception as e:
            return {"is_suspicious": False, "error": str(e)}

    def _generate_reason(self, tx, ae, iso):
        if not ae and not iso: return "Транзакция выглядит нормальной"
        reasons = []
        if tx.get("amount", 0) > tx.get("user_avg_amount", 0) * 5:
            reasons.append("Сумма значительно выше средней")
        if ae: reasons.append("Нетипичный паттерн (Autoencoder)")
        if iso: reasons.append("Аномальное сочетание параметров (Isolation Forest)")
        return "; ".join(reasons)

def detect_anomaly(tx: dict) -> dict:
    from .model_loader import registry
    det = registry.get("anomaly_detector")
    if not det: return {"is_suspicious": False, "error": "Detector not loaded"}
    return det.detect(tx)
