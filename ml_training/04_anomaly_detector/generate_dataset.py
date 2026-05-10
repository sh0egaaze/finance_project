"""
Генератор датасета для обучения детектора аномалий.
Фичи совпадают с тем, что приложение передаёт в detect().
"""
import numpy as np
import pandas as pd
import random
import os
from tqdm import tqdm

random.seed(42)
np.random.seed(42)


class TransactionGenerator:
    def __init__(self):
        # Коды категорий КАК В БАЗЕ ДАННЫХ приложения
        self.categories = {
            'food':          {'avg': 1200, 'std': 600,  'min': 80,   'max': 8000},
            'transport':     {'avg': 400,  'std': 250,  'min': 40,   'max': 3000},
            'entertainment': {'avg': 2000, 'std': 1500, 'min': 200,  'max': 15000},
            'shopping':      {'avg': 3000, 'std': 2500, 'min': 300,  'max': 30000},
            'health':        {'avg': 2500, 'std': 2000, 'min': 150,  'max': 25000},
            'restaurants':   {'avg': 1800, 'std': 1000, 'min': 300,  'max': 12000},
            'utilities':     {'avg': 5000, 'std': 2000, 'min': 800,  'max': 15000},
            'salary':        {'avg': 80000,'std': 30000,'min': 25000, 'max': 350000},
            'transfers':     {'avg': 5000, 'std': 8000, 'min': 100,  'max': 80000},
            'education':     {'avg': 3000, 'std': 2000, 'min': 500,  'max': 30000},
            'subscriptions': {'avg': 500,  'std': 300,  'min': 50,   'max': 3000},
            'other':         {'avg': 2000, 'std': 2500, 'min': 100,  'max': 30000},
        }

    def generate(self, n_transactions=150000, fraud_ratio=0.04):
        print(f"🚀 Генерация {n_transactions} транзакций...")
        data = []

        # 3000 пользователей с разными привычками
        users = []
        for uid in range(3000):
            income_mult = np.random.choice([0.4, 0.7, 1.0, 1.5, 3.0],
                                            p=[0.10, 0.20, 0.40, 0.20, 0.10])
            users.append({
                'id': uid,
                'income_mult': income_mult,
                'night_person': random.random() < 0.08,
                'fav_cats': random.sample(
                    [c for c in self.categories if c != 'salary'],
                    k=random.randint(3, 6)),
            })

        expense_cats = [c for c in self.categories if c != 'salary']

        for _ in tqdm(range(n_transactions)):
            user = random.choice(users)
            is_fraud = random.random() < fraud_ratio

            # Категория
            if random.random() < 0.03:
                cat = 'salary'
            elif random.random() < 0.65:
                cat = random.choice(user['fav_cats'])
            else:
                cat = random.choice(expense_cats)

            info = self.categories[cat]
            base = info['avg'] * user['income_mult']

            # Сумма — логнормальное распределение
            amount = np.random.lognormal(np.log(max(base, 10)), 0.35)
            amount = float(np.clip(amount, info['min'],
                                    info['max'] * user['income_mult']))

            # Час
            if user['night_person']:
                hour = int(np.random.normal(2, 1.5)) % 24
            else:
                hour = int(np.clip(np.random.normal(14, 3.5), 7, 23))

            day_of_week = random.randint(0, 6)
            is_weekend = 1 if day_of_week >= 5 else 0

            # ======= Фрод =======
            fraud_type = None
            if is_fraud:
                fraud_type = np.random.choice(
                    ['huge_amount', 'night_big', 'unusual_cat', 'rapid_spend'],
                    p=[0.35, 0.25, 0.25, 0.15])

                if fraud_type == 'huge_amount':
                    amount *= random.uniform(6, 25)

                elif fraud_type == 'night_big':
                    if not user['night_person']:
                        hour = random.randint(2, 4)
                    amount *= random.uniform(3, 10)

                elif fraud_type == 'unusual_cat':
                    other = [c for c in expense_cats
                             if c not in user['fav_cats']]
                    if other:
                        cat = random.choice(other)
                    amount *= random.uniform(4, 12)

                elif fraud_type == 'rapid_spend':
                    amount *= random.uniform(8, 20)

            # Средняя сумма пользователя (без salary)
            user_avg = sum(self.categories[c]['avg']
                           for c in user['fav_cats']) / len(user['fav_cats'])
            user_avg *= user['income_mult']

            amount_ratio = amount / (user_avg + 1)

            # Циклические фичи часа
            hour_sin = float(np.sin(2 * np.pi * hour / 24))
            hour_cos = float(np.cos(2 * np.pi * hour / 24))

            data.append({
                'amount':           round(amount, 2),
                'hour_sin':         round(hour_sin, 6),
                'hour_cos':         round(hour_cos, 6),
                'is_weekend':       is_weekend,
                'user_avg_amount':  round(user_avg, 2),
                'amount_ratio':     round(amount_ratio, 6),
                'category':         cat,
                'is_fraud':         int(is_fraud),
                'fraud_type':       fraud_type,
                # Для отладки (не идут в модель):
                'user_id':          user['id'],
                'hour':             hour,
            })

        df = pd.DataFrame(data)
        os.makedirs("data", exist_ok=True)
        df.to_csv("data/transactions.csv", index=False)

        fraud_df = df[df.is_fraud == 1]
        print(f"\n📊 Статистика:")
        print(f"   Всего:   {len(df)}")
        print(f"   Фрод:    {len(fraud_df)} ({len(fraud_df)/len(df)*100:.2f}%)")
        print(f"   Категории: {sorted(df['category'].unique())}")
        print(f"\n   Типы фрода:")
        for ft, cnt in fraud_df['fraud_type'].value_counts().items():
            print(f"      {ft}: {cnt}")
        print(f"\n✅ Сохранено в data/transactions.csv")


if __name__ == "__main__":
    TransactionGenerator().generate()