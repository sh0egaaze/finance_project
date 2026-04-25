import torch
import joblib
import pickle
import numpy as np
import logging
from .anomaly_architecture import TransactionAutoencoder

logger = logging.getLogger(__name__)

class AnomalyModel:
    def __init__(self):
        self.ae = None
        self.clf = None
        self.meta = None
        self.loaded = False

    def load(self, path):
        try:
            weights = path / "ae_weights.pth"
            forest = path / "iso_forest.joblib"
            meta = path / "meta.pkl"
            
            if weights.exists() and forest.exists() and meta.exists():
                with open(meta, "rb") as f:
                    self.meta = pickle.load(f)
                
                self.ae = TransactionAutoencoder(len(self.meta["features"]))
                self.ae.load_state_dict(torch.load(str(weights), map_location="cpu"))
                self.ae.eval()
                
                self.clf = joblib.load(str(forest))
                self.loaded = True
                logger.info("✅ Детектор аномалий успешно загружен")
        except Exception as e:
            logger.error(f"Ошибка загрузки аномалий: {e}")

    def analyze(self, transaction_obj):
        if not self.loaded:
            return {"is_suspicious": False, "reason": None}

        try:
            # Подготовка вектора признаков
            # Для реальной проверки нам нужно заполнить все поля из meta["features"]
            # Здесь я использую упрощенный профиль пользователя
            features = []
            for f in self.meta["features"]:
                if f == 'amount': val = float(transaction_obj.amount)
                elif f == 'hour': val = transaction_obj.transaction_date.hour
                # Остальные поля заполняем средними значениями или нулями если их нет в объекте
                else: val = 0 
                features.append(val)
            
            X = np.array([features])
            X_scaled = self.meta["scaler"].transform(X)
            
            # 1. Лес
            is_iso = self.clf.predict(X_scaled)[0] == -1
            
            # 2. Нейросеть
            with torch.no_grad():
                error = self.ae.get_error(torch.FloatTensor(X_scaled)).item()
                is_ae = error > self.meta["threshold"]

            if is_iso and is_ae:
                return {"is_suspicious": True, "reason": "Критическая аномалия поведения"}
            elif is_ae:
                return {"is_suspicious": True, "reason": "Нетипичная транзакция"}
            
        except Exception as e:
            logger.warning(f"Ошибка анализа: {e}")
            
        return {"is_suspicious": False, "reason": None}
