import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import os
from tqdm import tqdm

random.seed(42)
np.random.seed(42)

class TransactionGenerator:
    def __init__(self):
        self.categories = {
            'продукты': {'avg': 1200, 'std': 800, 'min': 50, 'max': 15000},
            'рестораны': {'avg': 1500, 'std': 1000, 'min': 200, 'max': 20000},
            'транспорт': {'avg': 300, 'std': 200, 'min': 30, 'max': 5000},
            'одежда': {'avg': 3000, 'std': 2500, 'min': 500, 'max': 50000},
            'электроника': {'avg': 15000, 'std': 20000, 'min': 500, 'max': 200000},
            'здоровье': {'avg': 2000, 'std': 3000, 'min': 100, 'max': 50000},
            'переводы': {'avg': 5000, 'std': 10000, 'min': 100, 'max': 100000},
        }
        self.cities = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Владивосток']
        self.devices = ['mobile_app', 'web_browser', 'terminal', 'atm']

    def generate(self, n_transactions=100000, fraud_ratio=0.035):
        print(f"🚀 Генерация {n_transactions} транзакций (Версия Pro)...")
        data = []
        users = []
        for i in range(2500):
            users.append({
                'id': i,
                'city': random.choice(self.cities),
                'device': random.choice(self.devices),
                'mult': np.random.choice([0.4, 1.0, 2.5, 6.0], p=[0.25, 0.5, 0.2, 0.05]),
                'night_owl': random.random() < 0.15 # Юзеры, которые часто тратят ночью
            })

        for _ in tqdm(range(n_transactions)):
            user = random.choice(users)
            is_fraud = random.random() < fraud_ratio
            cat = random.choice(list(self.categories.keys()))
            info = self.categories[cat]
            
            # Базовая сумма
            amount = np.random.lognormal(np.log(info['avg'] * user['mult']), 0.35)
            amount = np.clip(amount, info['min'], info['max'] * user['mult'])
            
            # Базовые параметры
            city, device = user['city'], user['device']
            hour = int(np.random.normal(2, 2) if user['night_owl'] else np.random.normal(15, 3)) % 24
            is_weekend = int(random.random() < 0.28)
            
            if is_fraud:
                f_type = np.random.choice(['amt', 'loc', 'time', 'dev'], p=[0.4, 0.2, 0.2, 0.2])
                if f_type == 'amt': amount *= random.uniform(8, 25)
                if f_type == 'loc': city = random.choice([c for c in self.cities if c != user['city']])
                if f_type == 'time': hour = random.randint(2, 4) if not user['night_owl'] else 12
                if f_type == 'dev': device = random.choice([d for d in self.devices if d != user['device']])

            data.append({
                'user_id': user['id'],
                'amount': round(float(amount), 2),
                'category': cat,
                'city': city,
                'device': device,
                'hour': hour,
                'day_of_week': random.randint(0, 6),
                'is_weekend': is_weekend,
                'is_fraud': int(is_fraud),
                'user_avg_amount': info['avg'] * user['mult']
            })

        df = pd.DataFrame(data)
        # Добавляем продвинутый Z-score
        df['amount_zscore'] = (df['amount'] - df['user_avg_amount']) / (df['amount'].std() + 1)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        os.makedirs("data", exist_ok=True)
        df.to_csv("data/transactions.csv", index=False)
        print(f"✅ Датасет готов.")

if __name__ == "__main__":
    TransactionGenerator().generate()
