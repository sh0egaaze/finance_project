import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь внутри Docker контейнера
TRAINED_MODELS_PATH = Path("/app/app/ml/trained_models")

class ModelRegistry:
    def __init__(self):
        self.categorizer = None
        self.nlp_parser = None
        self.recommender = None
        self.anomaly_detector = None
        self.status = {}

    def load_all(self):
        logger.info("📡 Инициализация ML моделей...")
        
        # Заглушка для каждой модели
        models = ["categorizer", "nlp_parser", "recommender", "anomaly"]
        
        for model in models:
            model_path = TRAINED_MODELS_PATH / model
            if model_path.exists() and any(model_path.iterdir()):
                # Если папка существует и не пуста - загружаем (логика в самих классах)
                self.status[model] = "Loaded"
                logger.info(f"✅ {model.upper()} успешно подгружен из файлов")
            else:
                self.status[model] = "Not Found / Using Fallback"
                logger.warning(f"⚠️ {model.upper()} веса не найдены. Модель будет работать в демо-режиме.")

registry = ModelRegistry()
