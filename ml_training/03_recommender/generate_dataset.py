import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import random

random.seed(42)
np.random.seed(42)

class TransactionGenerator:
    CATEGORIES = {
        "groceries": {
            "name": "Продукты",
            "merchants": ["Пятёрочка", "Магнит", "Лента", "Перекрёсток", "ВкусВилл", "Ашан", "Дикси", "Метро"],
            "amount_range": (150, 5000),
            "frequency_per_month": (8, 25),
        },
        "restaurants": {
            "name": "Рестораны и кафе",
            "merchants": ["Якитория", "KFC", "McDonald's", "Бургер Кинг", "Шоколадница", "Кофемания", "Додо Пицца", "Тануки", "IL Patio", "Starbucks"],
            "amount_range": (200, 4000),
            "frequency_per_month": (2, 20),
        },
        "transport": {
            "name": "Транспорт",
            "merchants": ["Яндекс Такси", "Uber", "Метро Москва", "РЖД", "Аэрофлот", "Лукойл", "Газпромнефть", "Тройка пополнение", "СитиМобил"],
            "amount_range": (50, 15000),
            "frequency_per_month": (5, 30),
        },
        "subscriptions": {
            "name": "Подписки",
            "merchants": ["Яндекс Плюс", "Netflix", "Spotify", "YouTube Premium", "Кинопоиск", "Okko", "Apple Music", "VK Музыка", "Adobe", "Microsoft 365", "Фитнес клуб"],
            "amount_range": (99, 2500),
            "frequency_per_month": (1, 8),
        },
        "shopping": {
            "name": "Покупки",
            "merchants": ["Wildberries", "Ozon", "Яндекс Маркет", "AliExpress", "DNS", "М.Видео", "Lamoda", "ASOS", "Zara", "H&M", "IKEA"],
            "amount_range": (300, 30000),
            "frequency_per_month": (1, 15),
        },
        "utilities": {
            "name": "ЖКХ и связь",
            "merchants": ["МосЭнергоСбыт", "Мосводоканал", "МТС", "Билайн", "Мегафон", "Ростелеком", "Дом.ру", "Управляющая компания"],
            "amount_range": (300, 8000),
            "frequency_per_month": (2, 6),
        },
        "health": {
            "name": "Здоровье",
            "merchants": ["Аптека Горздрав", "Аптека 36.6", "Инвитро", "Медси", "СберЗдоровье", "Стоматология"],
            "amount_range": (100, 15000),
            "frequency_per_month": (0, 5),
        },
        "entertainment": {
            "name": "Развлечения",
            "merchants": ["Кинотеатр", "Steam", "PlayStation Store", "Боулинг", "Квест", "Концерт", "Театр", "Парк аттракционов"],
            "amount_range": (200, 8000),
            "frequency_per_month": (1, 10),
        },
        "education": {
            "name": "Образование",
            "merchants": ["Skillbox", "Coursera", "Udemy", "Яндекс Практикум", "Книжный магазин", "Литрес"],
            "amount_range": (200, 15000),
            "frequency_per_month": (0, 3),
        },
    }

    SPENDING_PROFILES = [
        {"name": "overspender_restaurants", "category_weights": {"restaurants": 3.0}, "recommendations": [{"title": "Сократите расходы на рестораны", "description": "Ваши траты на рестораны и кафе значительно выше среднего. Попробуйте готовить дома хотя бы 3-4 раза в неделю.", "category": "restaurants", "savings_percent": 0.4}]},
        {"name": "subscription_hoarder", "category_weights": {"subscriptions": 3.5}, "recommendations": [{"title": "Оптимизируйте подписки", "description": "У вас много активных подписок. Проверьте, какими вы реально пользуетесь, и отмените неиспользуемые.", "category": "subscriptions", "savings_percent": 0.5}]},
        {"name": "impulse_shopper", "category_weights": {"shopping": 3.0, "entertainment": 2.0}, "recommendations": [{"title": "Контролируйте импульсивные покупки", "description": "Много мелких покупок в онлайн-магазинах. Добавляйте товары в корзину и ждите 48 часов перед покупкой.", "category": "shopping", "savings_percent": 0.35}, {"title": "Установите лимит на развлечения", "description": "Расходы на развлечения выше нормы. Установите месячный бюджет на эту категорию.", "category": "entertainment", "savings_percent": 0.3}]},
        {"name": "taxi_addict", "category_weights": {"transport": 3.0}, "recommendations": [{"title": "Используйте общественный транспорт", "description": "Расходы на такси очень высоки. Рассмотрите покупку проездного или использование каршеринга.", "category": "transport", "savings_percent": 0.45}]},
        {"name": "balanced", "category_weights": {}, "recommendations": [{"title": "Отличная финансовая дисциплина!", "description": "Ваши расходы хорошо сбалансированы. Рекомендуем откладывать 10-20% дохода на сбережения.", "category": "general", "savings_percent": 0.05}]},
        {"name": "food_lover", "category_weights": {"groceries": 2.5, "restaurants": 2.0}, "recommendations": [{"title": "Оптимизируйте расходы на продукты", "description": "Составляйте список покупок заранее и используйте акции и скидочные карты.", "category": "groceries", "savings_percent": 0.25}, {"title": "Сократите походы в кафе", "description": "Берите обеды из дома на работу хотя бы 3 раза в неделю.", "category": "restaurants", "savings_percent": 0.35}]},
        {"name": "tech_spender", "category_weights": {"shopping": 2.5, "subscriptions": 2.0, "entertainment": 2.5}, "recommendations": [{"title": "Планируйте крупные покупки", "description": "Дождитесь распродаж (Чёрная пятница, 11.11) для покупки техники.", "category": "shopping", "savings_percent": 0.3}, {"title": "Пересмотрите игровые расходы", "description": "Покупайте игры на распродажах Steam и отмените неиспользуемые подписки.", "category": "entertainment", "savings_percent": 0.35}]},
        {"name": "no_savings", "category_weights": {"restaurants": 1.8, "shopping": 1.8, "entertainment": 1.8, "transport": 1.5}, "recommendations": [{"title": "Создайте финансовую подушку", "description": "Вы тратите почти весь доход. Настройте автоперевод 10% зарплаты на накопительный счёт.", "category": "general", "savings_percent": 0.15}, {"title": "Сократите необязательные расходы", "description": "Проанализируйте траты на рестораны, покупки и развлечения — сократите каждую категорию на 20%.", "category": "shopping", "savings_percent": 0.2}]},
    ]

    def __init__(self, salary_range=(30000, 200000)):
        self.salary_range = salary_range

    def generate_monthly_transactions(self, profile_idx: int, salary: float, year: int = 2024, month: int = 1) -> list[dict]:
        profile = self.SPENDING_PROFILES[profile_idx]
        transactions = []
        days_in_month = 30 # Упрощенно для генератора
        for cat_key, cat_info in self.CATEGORIES.items():
            weight = profile["category_weights"].get(cat_key, 1.0)
            freq_min, freq_max = cat_info["frequency_per_month"]
            num_transactions = int(np.random.randint(freq_min, freq_max + 1) * weight)
            salary_factor = salary / 80000
            for _ in range(num_transactions):
                amount_min, amount_max = cat_info["amount_range"]
                base_amount = np.random.uniform(amount_min, min(amount_max, amount_max * salary_factor))
                amount = max(amount_min, base_amount * np.random.uniform(0.7, 1.3))
                date = datetime(year, month, np.random.randint(1, days_in_month + 1), np.random.randint(7, 23), np.random.randint(0, 60))
                transactions.append({"date": date.strftime("%Y-%m-%d %H:%M"), "amount": round(amount, 2), "category": cat_key, "category_name": cat_info["name"], "merchant": random.choice(cat_info["merchants"]), "type": "expense"})
        transactions.append({"date": f"{year}-{month:02d}-05 10:00", "amount": round(salary * 0.4, 2), "category": "income", "category_name": "Доход", "merchant": "Работодатель", "type": "income"})
        transactions.append({"date": f"{year}-{month:02d}-20 10:00", "amount": round(salary * 0.6, 2), "category": "income", "category_name": "Доход", "merchant": "Работодатель", "type": "income"})
        transactions.sort(key=lambda x: x["date"])
        return transactions

    def generate_dataset(self, num_samples: int = 10000) -> list[dict]:
        dataset = []
        for i in range(num_samples):
            profile_idx = np.random.randint(0, len(self.SPENDING_PROFILES))
            profile = self.SPENDING_PROFILES[profile_idx]
            salary = np.random.randint(self.salary_range[0], self.salary_range[1])
            transactions = self.generate_monthly_transactions(profile_idx, salary)
            
            cat_totals, total_exp = {}, 0
            for t in transactions:
                if t["type"] == "expense":
                    cat_totals[t["category"]] = cat_totals.get(t["category"], 0) + t["amount"]
                    total_exp += t["amount"]
            
            recs = []
            for rec in profile["recommendations"]:
                cat = rec["category"]
                savings = round(cat_totals.get(cat, total_exp if cat == "general" else 0) * rec["savings_percent"])
                recs.append({"title": rec["title"], "description": rec["description"], "potential_savings": max(savings, 100)})
            dataset.append({"transactions": transactions, "recommendations": recs})
        return dataset

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    gen = TransactionGenerator()
    data = gen.generate_dataset(10000)
    with open("data/dataset.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Датасет на {len(data)} сэмплов сохранен в data/dataset.json")
