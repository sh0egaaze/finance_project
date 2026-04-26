import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import random
from tqdm import tqdm

random.seed(42)
np.random.seed(42)

class TransactionGenerator:
    CATEGORIES = {
        "groceries": {"name": "Продукты", "amount": (100, 6000), "freq": (10, 30)},
        "restaurants": {"name": "Рестораны", "amount": (300, 5000), "freq": (2, 25)},
        "transport": {"name": "Транспорт", "amount": (50, 10000), "freq": (10, 40)},
        "subscriptions": {"name": "Подписки", "amount": (199, 3000), "freq": (1, 10)},
        "shopping": {"name": "Покупки", "amount": (500, 50000), "freq": (1, 20)},
        "utilities": {"name": "ЖКХ", "amount": (500, 10000), "freq": (2, 5)},
        "health": {"name": "Здоровье", "amount": (200, 20000), "freq": (0, 8)},
        "entertainment": {"name": "Развлечения", "amount": (300, 15000), "freq": (1, 12)},
        "education": {"name": "Образование", "amount": (1000, 30000), "freq": (0, 4)},
    }

    PROFILES = [
        {"name": "overspender_restaurants", "weights": {"restaurants": (4.0, 7.0), "groceries": (0.3, 0.7)}, "title": "Сократите расходы на рестораны"},
        {"name": "subscription_hoarder", "weights": {"subscriptions": (5.0, 9.0)}, "title": "Оптимизируйте подписки"},
        {"name": "impulse_shopper", "weights": {"shopping": (4.0, 8.0), "entertainment": (2.0, 5.0)}, "title": "Контролируйте импульсивные покупки"},
        {"name": "taxi_addict", "weights": {"transport": (4.0, 7.5)}, "title": "Используйте общественный транспорт"},
        {"name": "balanced", "weights": {}, "title": "Отличная финансовая дисциплина!"},
        {"name": "food_lover", "weights": {"groceries": (3.5, 6.0), "restaurants": (2.0, 4.5)}, "title": "Оптимизируйте расходы на продукты"},
        {"name": "tech_spender", "weights": {"shopping": (3.0, 6.0), "subscriptions": (1.5, 3.0), "entertainment": (3.0, 6.0)}, "title": "Планируйте крупные покупки"},
        {"name": "no_savings", "weights": {"restaurants": (2.0, 3.5), "shopping": (2.0, 3.5), "transport": (1.5, 3.0), "entertainment": (1.5, 3.0)}, "title": "Создайте финансовую подушку"},
    ]

    def generate_monthly(self, profile, salary):
        transactions = []
        user_variability = random.uniform(0.7, 1.3) # Каждый юзер уникален
        
        for cat, info in self.CATEGORIES.items():
            # Берем случайный вес из диапазона профиля или 1.0
            w_range = profile["weights"].get(cat, (0.8, 1.2))
            weight = random.uniform(*w_range) * user_variability
            
            num_tx = int(np.random.randint(info["freq"][0], info["freq"][1] + 1) * weight)
            for _ in range(num_tx):
                # Сумма зависит от зарплаты и случая
                base_amt = random.uniform(info["amount"][0], info["amount"][1])
                salary_mod = (salary / 100000) ** 0.6
                amt = base_amt * salary_mod * random.uniform(0.8, 1.2)
                
                # Рандомный день (будни/выходные)
                is_weekend = random.random() < 0.3
                transactions.append({
                    "amount": round(amt, 2),
                    "category": cat,
                    "type": "expense",
                    "weekend": int(is_weekend)
                })
        
        # Доход (разбитый на 2 части)
        transactions.append({"amount": salary * 0.4, "category": "income", "type": "income", "weekend": 0})
        transactions.append({"amount": salary * 0.6, "category": "income", "type": "income", "weekend": 0})
        return transactions

    def generate(self, num_samples=100000):
        dataset = []
        print(f"🚀 Генерация БОЛЬШОГО датасета ({num_samples} сэмплов)...")
        for _ in tqdm(range(num_samples)):
            profile = random.choice(self.PROFILES)
            salary = np.random.randint(35000, 450000)
            txs = self.generate_monthly(profile, salary)
            dataset.append({
                "transactions": txs,
                "recommendations": [{"title": profile["title"], "potential_savings": 2000}]
            })
        return dataset

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    gen = TransactionGenerator()
    data = gen.generate(100000)
    with open("data/dataset.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Датасет на 100к записей готов.")
