"""
Детектор аномалий — загрузка моделей и инференс.
"""
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
        self.loaded = False

        try:
            # Метаданные
            with open(os.path.join(model_dir, "meta.pkl"), "rb") as f:
                self.meta = pickle.load(f)

            # Autoencoder
            self.ae = TransactionAutoencoder(self.meta["input_dim"]).to(self.device)
            self.ae.load_state_dict(
                torch.load(
                    os.path.join(model_dir, "autoencoder.pt"),
                    map_location=self.device,
                    weights_only=True,
                )
            )
            self.ae.eval()

            # Isolation Forest
            import joblib, io
            iso_path = os.path.join(model_dir, "isolation_forest.joblib")
            with open(iso_path, "rb") as f:
                raw = f.read()
            file_hash = hashlib.sha256(raw).hexdigest()[:16]
            logger.info(f"    isolation_forest.joblib (sha256:{file_hash}...)")
            self.iso = joblib.load(io.BytesIO(raw))

            self.threshold = self.meta["threshold"]
            self.loaded = True
            logger.info(f"AnomalyDetector loaded  (input_dim={self.meta['input_dim']}, "
                         f"threshold={self.threshold:.6f})")
        except Exception as e:
            logger.error(f"AnomalyDetector failed to load: {e}")

    # ------------------------------------------------------------------ #
    def detect(self, tx: dict) -> dict:
        """
        tx  должен содержать:
            amount, hour, category (код), user_avg_amount
        Опционально: is_weekend, day_of_week
        """
        if not self.loaded:
            return {"is_suspicious": False, "error": "Model not loaded"}

        try:
            amount    = float(tx.get("amount", 0))
            hour      = int(tx.get("hour", 12))
            category  = str(tx.get("category", "other"))
            user_avg  = float(tx.get("user_avg_amount", amount))
            is_weekend = int(tx.get("is_weekend",
                            1 if tx.get("day_of_week", 0) >= 5 else 0))

            hour_sin = float(np.sin(2 * np.pi * hour / 24))
            hour_cos = float(np.cos(2 * np.pi * hour / 24))
            amount_ratio = amount / (user_avg + 1)

            # Числовые фичи (порядок = num_cols)
            num_vals = [amount, hour_sin, hour_cos,
                        is_weekend, user_avg, amount_ratio]
            X_num = self.meta["scaler"].transform([num_vals])

            # Категориальные
            X_cat = []
            for col in self.meta["cat_cols"]:
                le = self.meta["encoders"][col]
                val = tx.get(col, "other")
                if val in le.classes_:
                    X_cat.append(le.transform([val])[0])
                elif "other" in le.classes_:
                    X_cat.append(le.transform(["other"])[0])
                else:
                    X_cat.append(0)

            X = np.hstack([X_num, [X_cat]]).astype(np.float32)

            # VAE
            X_t = torch.FloatTensor(X).to(self.device)
            with torch.no_grad():
                recon, _, _ = self.ae(X_t)
                err = torch.mean((X_t - recon) ** 2).item()

            is_ae  = err > self.threshold
            is_iso = self.iso.predict(X)[0] == -1
            is_suspicious = is_ae or is_iso

            reason = self._make_reason(amount, hour, user_avg,
                                       amount_ratio, is_ae, is_iso)

            return {
                "is_suspicious": bool(is_suspicious),
                "anomaly_score": round(err / (self.threshold + 1e-9), 4),
                "reason": reason,
            }

        except Exception as e:
            logger.error(f"detect() error: {e}")
            return {"is_suspicious": False, "error": str(e)}

    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_reason(amount, hour, user_avg, ratio, ae, iso):
        if not ae and not iso:
            return ""
        parts = []
        if ratio > 3 and user_avg > 0:
            parts.append(
                f"Сумма в {ratio:.1f} раз выше вашей средней "
                f"({user_avg:,.0f}₽)".replace(",", " "))
        if 2 <= hour <= 5 and amount > 3000:
            parts.append("Крупная транзакция в ночное время")
        if amount > 30000:
            parts.append(f"Крупная сумма: {amount:,.0f}₽".replace(",", " "))
        if not parts:
            parts.append("Нетипичная транзакция для вашего профиля расходов")
        return "; ".join(parts)


# ── Публичный API (вызывается из transaction_service) ───────────
def detect_anomaly(tx: dict) -> dict:
    from .model_loader import registry
    det = registry.get("anomaly_detector")
    if not det or not getattr(det, "loaded", False):
        return {"is_suspicious": False, "error": "Detector not loaded"}
    return det.detect(tx)