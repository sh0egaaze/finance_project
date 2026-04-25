"""
AI Детектор аномалий - выявляет подозрительные транзакции.
"""
from typing import Dict, Any, Optional

class AnomalyDetector:
    """
    Задача: Определить, является ли транзакция аномальной для данного пользователя.
    Вход: Объект транзакции.
    Выход: Флаг подозрительности и причина.
    """
    
    def analyze(self, transaction: Any) -> Dict[str, Any]:
        # ЗАГЛУШКА: Здесь будет твоя нейросеть (напр. Isolation Forest)
        # Входные фичи: сумма, время часа, код категории
        
        amount = float(transaction.amount)
        
        # Пример простейшей логики аномалии
        if abs(amount) > 50000:
            return {
                "is_suspicious": True,
                "reason": "Критически крупная сумма для вашего профиля"
            }
            
        return {
            "is_suspicious": False,
            "reason": None
        }
