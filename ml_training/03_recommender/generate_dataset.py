"""
Генератор датасета для обучения модели рекомендаций.
Каждый сэмпл = месяц транзакций пользователя + рекомендации.
"""
import pandas as pd
import numpy as np
import json
import os
import random
from tqdm import tqdm

random.seed(42)
np.random.seed(42)

class TransactionGenerator:
    CATEGORIES = {
        "groceries":     {"amount": (80,  5000),  "freq": (8,  25)},
        "restaurants":   {"amount": (300, 5000),  "freq": (2,  20)},
        "transport":     {"amount": (50,  8000),  "freq": (8,  35)},
        "subscriptions": {"amount": (150, 2500),  "freq": (1,  8)},
        "shopping":      {"amount": (400, 40000), "freq": (1,  15)},
        "utilities":     {"amount": (500, 10000), "freq": (2,  5)},
        "health":        {"amount": (200, 15000), "freq": (0,  6)},
        "entertainment": {"amount": (200, 12000), "freq": (1,  10)},
        "education":     {"amount": (500, 25000), "freq": (0,  3)},
    }

    # Профили с подробными рекомендациями
    PROFILES = [
        {
            "name": "overspender_restaurants",
            "weights": {"restaurants": (3.5, 6.0), "groceries": (0.4, 0.8)},
            "recs": [
                {
                    "title": "Сократите расходы на рестораны",
                    "description": "Вы тратите на рестораны значительно больше среднего. Попробуйте готовить дома 3-4 раза в неделю вместо заказа еды.",
                    "potential_savings_pct": 0.25,
                    "saving_category": "restaurants",
                },
                {
                    "title": "Замените рестораны на домашнюю кухню",
                    "description": "Один обед в ресторане стоит как продукты на 2 дня. Составляйте меню на неделю заранее.",
                    "potential_savings_pct": 0.15,
                    "saving_category": "groceries",
                },
            ],
        },
        {
            "name": "subscription_hoarder",
            "weights": {"subscriptions": (4.0, 8.0)},
            "recs": [
                {
                    "title": "Оптимизируйте подписки",
                    "description": "У вас много подписок. Проверьте, какими вы реально пользуетесь, и отмените остальные.",
                    "potential_savings_pct": 0.50,
                    "saving_category": "subscriptions",
                },
                {
                    "title": "Ищите семейные тарифы",
                    "description": "Семейные подписки дешевле на 40-60%. Разделите с друзьями или семьёй.",
                    "potential_savings_pct": 0.20,
                    "saving_category": "subscriptions",
                },
            ],
        },
        {
            "name": "impulse_shopper",
            "weights": {"shopping": (3.5, 7.0), "entertainment": (2.0, 4.0)},
            "recs": [
                {
                    "title": "Контролируйте импульсивные покупки",
                    "description": "Перед покупкой дороже 3000₽ подождите 48 часов. 70% импульсивных желаний проходят.",
                    "potential_savings_pct": 0.30,
                    "saving_category": "shopping",
                },
                {
                    "title": "Ведите список желаний",
                    "description": "Записывайте все хотелки в список и покупайте по приоритету раз в месяц.",
                    "potential_savings_pct": 0.20,
                    "saving_category": "shopping",
                },
            ],
        },
        {
            "name": "taxi_addict",
            "weights": {"transport": (3.5, 7.0)},
            "recs": [
                {
                    "title": "Пересядьте на общественный транспорт",
                    "description": "Месячный проездной стоит как 5-6 поездок на такси. Используйте такси только для необходимых поездок.",
                    "potential_savings_pct": 0.40,
                    "saving_category": "transport",
                },
                {
                    "title": "Рассмотрите альтернативы",
                    "description": "Каршеринг и электросамокаты — в 3-5 раз дешевле такси на коротких маршрутах.",
                    "potential_savings_pct": 0.15,
                    "saving_category": "transport",
                },
            ],
        },
        {
            "name": "balanced",
            "weights": {},
            "recs": [
                {
                    "title": "Отличная финансовая дисциплина!",
                    "description": "Ваши расходы сбалансированы. Продолжайте в том же духе и наращивайте подушку безопасности.",
                    "potential_savings_pct": 0,
                    "saving_category": None,
                },
                {
                    "title": "Рассмотрите инвестирование",
                    "description": "С вашей дисциплиной можно начать инвестировать 10-15% дохода в надёжные инструменты.",
                    "potential_savings_pct": 0,
                    "saving_category": None,
                },
            ],
        },
        {
            "name": "food_lover",
            "weights": {"groceries": (3.0, 5.5), "restaurants": (2.0, 4.0)},
            "recs": [
                {
                    "title": "Оптимизируйте расходы на еду",
                    "description": "Еда занимает слишком большую долю бюджета. Составляйте список покупок и не ходите в магазин голодным.",
                    "potential_savings_pct": 0.20,
                    "saving_category": "groceries",
                },
                {
                    "title": "Используйте акции и кешбэк",
                    "description": "Карты лояльности магазинов и кешбэк-сервисы экономят 5-15% на продуктах.",
                    "potential_savings_pct": 0.10,
                    "saving_category": "groceries",
                },
            ],
        },
        {
            "name": "tech_spender",
            "weights": {"shopping": (2.5, 5.0), "subscriptions": (1.5, 3.0), "entertainment": (2.5, 5.0)},
            "recs": [
                {
                    "title": "Планируйте крупные покупки",
                    "description": "Техника и гаджеты дешевеют на 20-30% через 3-6 месяцев после выхода. Не покупайте в первый день.",
                    "potential_savings_pct": 0.25,
                    "saving_category": "shopping",
                },
                {
                    "title": "Контролируйте расходы на развлечения",
                    "description": "Установите месячный лимит на развлечения и придерживайтесь его.",
                    "potential_savings_pct": 0.20,
                    "saving_category": "entertainment",
                },
            ],
        },
        {
            "name": "no_savings",
            "weights": {
                "restaurants": (2.0, 3.0), "shopping": (2.0, 3.0),
                "transport": (1.5, 2.5), "entertainment": (1.5, 2.5),
            },
            "recs": [
                {
                    "title": "Создайте финансовую подушку",
                    "description": "Вы тратите почти весь доход. Начните откладывать хотя бы 10% — переводите в день зарплаты автоматически.",
                    "potential_savings_pct": 0.10,
                    "saving_category": None,
                },
                {
                    "title": "Установите бюджет по категориям",
                    "description": "Разбейте месячный бюджет: 50% необходимое, 30% желаемое, 20% сбережения.",
                    "potential_savings_pct": 0.15,
                    "saving_category": None,
                },
            ],
        },
    ]

    def generate_monthly(self, profile, salary):
        transactions = []
        variability = random.uniform(0.7, 1.3)

        for cat, info in self.CATEGORIES.items():
            w_range = profile["weights"].get(cat, (0.8, 1.2))
            weight = random.uniform(*w_range) * variability
            num_tx = max(0, int(random.randint(info["freq"][0], info["freq"][1]) * weight))

            for _ in range(num_tx):
                base = random.uniform(info["amount"][0], info["amount"][1])
                salary_mod = (salary / 100000) ** 0.55
                amt = base * salary_mod * random.uniform(0.8, 1.2)
                is_weekend = random.random() < 0.3
                transactions.append({
                    "amount": round(amt, 2),
                    "category": cat,
                    "type": "expense",
                    "weekend": int(is_weekend),
                    "merchant": "",
                })

        # Доход
        transactions.append({"amount": round(salary * 0.4), "category": "income", "type": "income", "weekend": 0, "merchant": ""})
        transactions.append({"amount": round(salary * 0.6), "category": "income", "type": "income", "weekend": 0, "merchant": ""})
        return transactions

    def build_recs(self, profile, transactions):
        """Строим рекомендации с реальными суммами на основе транзакций"""
        df = pd.DataFrame(transactions)
        exp = df[df["type"] == "expense"]
        total_expense = exp["amount"].sum() if not exp.empty else 0

        recs = []
        for r in profile["recs"]:
            saving_cat = r["saving_category"]
            pct = r["potential_savings_pct"]

            if saving_cat and pct > 0:
                cat_total = exp[exp["category"] == saving_cat]["amount"].sum() if not exp.empty else 0
                savings = round(cat_total * pct)
            elif pct > 0:
                savings = round(total_expense * pct)
            else:
                savings = 0

            recs.append({
                "title": r["title"],
                "description": r["description"],
                "potential_savings": savings if savings > 0 else None,
            })
        return recs

    def generate(self, num_samples=120000):
        dataset = []
        print(f"🚀 Генерация {num_samples} сэмплов...")
        for _ in tqdm(range(num_samples)):
            profile = random.choice(self.PROFILES)
            salary = int(np.random.lognormal(np.log(80000), 0.5))
            salary = max(30000, min(salary, 500000))
            txs = self.generate_monthly(profile, salary)
            recs = self.build_recs(profile, txs)
            dataset.append({
                "profile": profile["name"],
                "transactions": txs,
                "recommendations": recs,
            })
        return dataset


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    gen = TransactionGenerator()
    data = gen.generate(120000)

    # Статистика
    from collections import Counter
    profiles = Counter(d["profile"] for d in data)
    print("\n📊 Распределение профилей:")
    for p, c in profiles.most_common():
        print(f"   {p}: {c}")

    with open("data/dataset.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"\n✅ Датасет сохранён в data/dataset.json")