# backend/app/ml/model_loader.py
import os
import json
import logging
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь к папке с весами
MODELS_BASE_DIR = Path(__file__).parent / "trained_models"

class ModelRegistry:
    def __init__(self):
        self._models: dict[str, Any] = {}
        self._loaded: dict[str, bool] = {}

    def get(self, model_name: str) -> Optional[Any]:
        """Получить загруженную модель по имени"""
        return self._models.get(model_name)

    def load_all(self):
        """Загрузить все доступные модели при старте приложения"""
        logger.info("🚀 Запуск инициализации всех ML-моделей...")
        
        # 1. Категоризатор (RuBERT)
        self._load_generic_model("categorizer", self._load_rubert_logic)
        
        # 2. NLP Парсер (DeepPavlov RuBERT Multi-task)
        self._load_generic_model("nlp_parser", self._load_nlp_logic)
        
        # 3. Рекомендатель (Random Forest / Joblib)
        self._load_generic_model("recommender", self._load_recommender_logic)
        
        # 4. Детектор аномалий (Будущая модель)
        self._load_generic_model("anomaly_detector", self._load_anomaly_logic)

        loaded_count = sum(1 for v in self._loaded.values() if v)
        logger.info(f"✅ Загрузка завершена. Моделей активно: {loaded_count}")

    def _load_generic_model(self, name: str, loader_func):
        """Вспомогательный метод для загрузки любой модели"""
        model_dir = MODELS_BASE_DIR / name
        # Проверяем, есть ли папка и ключевые файлы внутри
        if model_dir.exists():
            try:
                self._models[name] = loader_func(model_dir)
                self._loaded[name] = True
                logger.info(f"   [+] {name.upper()}: Успешно загружена")
            except Exception as e:
                logger.error(f"   [-] {name.upper()}: Ошибка загрузки: {e}")
        else:
            logger.warning(f"   [!] {name.upper()}: Папка не найдена в {model_dir}")

    def _load_rubert_logic(self, model_dir: Path):
        """Логика загрузки для первой модели (Categorizer)"""
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
        model.to(device)
        model.eval()

        with open(model_dir / "id2cat.json", "r", encoding="utf-8") as f:
            id2cat = {int(k): v for k, v in json.load(f).items()}
        with open(model_dir / "category_names.json", "r", encoding="utf-8") as f:
            category_names = json.load(f)
        with open(model_dir / "metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return {
            "model": model,
            "tokenizer": tokenizer,
            "id2cat": id2cat,
            "category_names": category_names,
            "metadata": metadata,
            "device": device
        }

    def _load_nlp_logic(self, model_dir: Path):
        """Логика загрузки для второй модели (NLP Parser)"""
        from .nlp_parser import FinanceParser
        return FinanceParser(str(model_dir))

    def _load_recommender_logic(self, model_dir: Path):
        """Логика загрузки для третьей модели (Recommender)"""
        from .recommender import FinanceRecommender
        return FinanceRecommender(str(model_dir))

    def _load_anomaly_logic(self, model_dir: Path):
        """Логика загрузки для четвертой модели (Anomaly Detector)"""
        from .anomaly_detector import AnomalyDetector
        return AnomalyDetector(str(model_dir))

# Глобальный синглтон
registry = ModelRegistry()
