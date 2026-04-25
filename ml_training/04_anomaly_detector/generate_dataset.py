import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import os

# CONFIG (Твой файл 1)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

class TransactionGenerator:
    def __init__(self):
        self.categories = {
            'продукты': {'avg': 1200, 'std': 800, 'min': 50, 'max': 15000, 'weight': 0.25},
            'рестораны': {'avg': 1500, 'std': 1000, 'min': 200, 'max': 20000, 'weight': 0.12},
            'транспорт': {'avg': 300, 'std': 200, 'min': 30, 'max': 5000, 'weight': 0.15},
            'одежда': {'avg': 3000, 'std': 2500, 'min': 500, 'max': 50000, 'weight': 0.08},
            'электроника': {'avg': 15000, 'std': 20000, 'min': 500, 'max': 200000, 'weight': 0.05},
            'развлечения': {'avg': 800, 'std': 600, 'min': 100, 'max': 10000, 'weight': 0.08},
            'здоровье': {'avg': 2000, 'std': 3000, 'min': 100, 'max': 50000, 'weight': 0.05},
            'коммунальные': {'avg': 5000, 'std': 2000, 'min': 1000, 'max': 15000, 'weight': 0.07},
            'связь': {'avg': 600, 'std': 300, 'min': 100, 'max': 3000, 'weight': 0.05},
            'переводы': {'avg': 5000, 'std': 10000, 'min': 100, 'max': 100000, 'weight': 0.07},
            'снятие_наличных': {'avg': 5000, 'std': 5000, 'min': 500, 'max': 50000, 'weight': 0.03},
        }
        self.cities = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань', 'Нижний Новгород', 'Краснодар']
        self.devices = ['mobile_app', 'web_browser', 'terminal', 'atm']

    def generate_dataset(self, n_users=1000, days=30, fraud_ratio=0.035):
        print(f"🏭 Генерирую данные для {n_users} пользователей за {days} дней...")
        all_tx = []
        for u_id in range(1, n_users + 1):
            home_city = random.choice(self.cities)
            pref_dev = random.choice(self.devices)
            income_mult = np.random.choice([0.5, 1.0, 3.0], p=[0.4, 0.5, 0.1])
            
            for day in range(days):
                date = datetime(2024, 1, 1) + timedelta(days=day)
                for _ in range(np.random.poisson(3)): # в среднем 3 транзакции в день
                    is_fraud = random.random() < fraud_ratio
                    cat = random.choice(list(self.categories.keys()))
                    info = self.categories[cat]
                    
                    amount = np.random.lognormal(np.log(info['avg'] * income_mult), 0.5)
                    amount = np.clip(amount, info['min'], info['max'] * income_mult)
                    
                    if is_fraud:
                        amount *= np.random.uniform(5, 20) # Аномально большая сумма
                    
                    all_tx.append({
                        'user_id': u_id,
                        'amount': round(amount, 2),
                        'category': cat,
                        'city': home_city if random.random() > 0.1 else random.choice(self.cities),
                        'device': pref_dev if random.random() > 0.1 else random.choice(self.devices),
                        'hour': random.randint(0, 23),
                        'day_of_week': date.weekday(),
                        'is_fraud': int(is_fraud),
                        'account_age_days': random.randint(30, 1000)
                    })
        
        df = pd.DataFrame(all_tx)
        # Добавляем профильные фичи (из твоего файла 2)
        user_stats = df.groupby('user_id')['amount'].agg(['mean', 'std', 'max']).reset_index()
        user_stats.columns = ['user_id', 'user_avg_amount', 'user_std_amount', 'user_max_amount']
        df = df.merge(user_stats, on='user_id')
        df['amount_zscore'] = (df['amount'] - df['user_avg_amount']) / (df['user_std_amount'] + 1)
        
        path = os.path.join(DATA_DIR, "transactions.csv")
        df.to_csv(path, index=False)
        print(f"✅ Сохранено в {path}")

if __name__ == "__main__":
    TransactionGenerator().generate_dataset()
