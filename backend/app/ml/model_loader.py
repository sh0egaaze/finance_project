import os
import json
import logging
import threading
import hashlib
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь к папке с обученными моделями
MODELS_BASE_DIR = Path(__file__).parent / "trained_models"

class ModelRegistry:
    def __init__(self):
        self._models: dict[str, Any] = {}
        self._loaded: dict[str, bool] = {}
        self._lock = threading.Lock()  

    def get(self, model_name: str) -> Optional[Any]:
        """Возвращает загруженную модель по имени"""
        with self._lock:  
            return self._models.get(model_name)
    
    def get_or_raise(self, model_name: str) -> Any:
        """Получить модель или выбросить чёткую ошибку"""
        with self._lock:
            model = self._models.get(model_name)
        if model is None:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=f"ML-модель '{model_name}' недоступна. Попробуйте позже."
            )
        return model

    def load_all(self):
        """Загружает все обученные модели из папки по умолчанию"""
        logger.info("🔄 Инициализация ML-модулей...")
        
        # 1. Категоризатор (RuBERT)
        self._load_generic_model("categorizer", self._load_rubert_logic)
        
        # 2. NLP Парсер (DeepPavlov RuBERT Multi-task)
        self._load_generic_model("nlp_parser", self._load_nlp_logic)
        
        # 3. Рекомендательная (Random Forest / Joblib)
        self._load_generic_model("recommender", self._load_recommender_logic)
        
        # 4. Детектор аномалий
        self._load_generic_model("anomaly_detector", self._load_anomaly_logic)

        loaded_count = sum(1 for v in self._loaded.values() if v)
        logger.info(f"✅ Загрузка завершена. Модели загружены: {loaded_count}")

    def _load_generic_model(self, name: str, loader_func):
        """Универсальный метод загрузки обученной модели"""
        model_dir = MODELS_BASE_DIR / name
        # Проверяем, существует ли папка и можно ли загрузить
        if model_dir.exists():
            for attempt in range(3):
                try:
                    self._models[name] = loader_func(model_dir)
                    with self._lock:
                        self._loaded[name] = True
                    logger.info(f"   [+] {name.upper()}: Успешно загружен")
                    break
                except Exception as e:
                    logger.error(f"   [-] {name.upper()}: Ошибка загрузки (попытка {attempt+1}/3): {e}")
                    if attempt == 2:
                        logger.error(f"   [-] {name.upper()}: Не удалось загрузить после 3 попыток")
        else:
            logger.warning(f"   [!] {name.upper()}: Папка не найдена в {model_dir}")

    def _load_rubert_logic(self, model_dir: Path):
        """Загрузка модели для парсинга категории (Categorizer)"""
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
        """Загрузка модели для умного парсинга (NLP Parser)"""
        from .nlp_parser import FinanceParser
        return FinanceParser(str(model_dir))

    def _load_recommender_logic(self, model_dir: Path):
        """Загрузка модели для рекомендаций (Recommender)"""
        from .recommender import FinanceRecommender
        return FinanceRecommender(str(model_dir))

    def _load_anomaly_logic(self, model_dir: Path):
        """Загрузка модели для поиска аномалий (Anomaly Detector)"""
        from .anomaly_detector import AnomalyDetector
        return AnomalyDetector(str(model_dir))
    
    def health_check(self) -> dict:
        with self._lock:
            status = {}
            for name in ["categorizer", "nlp_parser", "recommender", "anomaly_detector"]:
                loaded = self._loaded.get(name, False)
                model = self._models.get(name)
                status[name] = {
                    "loaded": loaded,
                    "healthy": model is not None,
                }
            return status

# Глобальный синглтон
registry = ModelRegistry()
