import pandas as pd
import numpy as np
import json
import os
import random
from tqdm import tqdm
from typing import List, Dict, Tuple
from collections import defaultdict
random.seed(42)
np.random.seed(42)
EXPENSE_CATEGORIES = [
    "groceries", "restaurants", "transport", "subscriptions",
    "shopping", "utilities", "health", "entertainment", "education"
]
BASE_SHARES = {
    "groceries": 0.25,
    "restaurants": 0.08,
    "transport": 0.12,
    "subscriptions": 0.04,
    "shopping": 0.15,
    "utilities": 0.12,
    "health": 0.06,
    "entertainment": 0.08,
    "education": 0.05,
}
class TransactionGenerator:
    """Генератор реалистичных транзакций с поведенческими паттернами"""
    
    MERCHANTS = {
        "groceries": ["Пятёрочка", "Магнит", "Перекрёсток", "Ашан", "Лента", "ВкусВилл"],
        "restaurants": ["Яндекс Еда", "Delivery Club", "KFC", "McDonald's", "Кофемания", "Тануки", "Шоколадница"],
        "transport": ["Яндекс Такси", "Uber", "Метро", "РЖД", "Делимобиль", "Ситимобил", "Bolt"],
        "subscriptions": ["Spotify", "Netflix", "Яндекс Плюс", "YouTube Premium", "iCloud", "VK Music", "Кинопоиск", "Apple One"],
        "shopping": ["Wildberries", "Ozon", "AliExpress", "Lamoda", "М.Видео", "DNS", "IKEA"],
        "utilities": ["МосЭнергоСбыт", "Ростелеком", "МТС", "Билайн", "Тинькофф ЖКХ"],
        "health": ["Аптека.ру", "Здоровье", "Invitro", "EMC", "Медси"],
        "entertainment": ["Steam", "PlayStation", "Кинопоиск", "Афиша", "Концертный зал", "Кино"],
        "education": ["Skillbox", "Coursera", "Яндекс Практикум", "GeekBrains"],
    }
    
    TRANSACTION_COUNTS = {
        "groceries": (8, 20),
        "restaurants": (1, 18),
        "transport": (5, 30),
        "subscriptions": (1, 8),
        "shopping": (0, 10),
        "utilities": (2, 4),
        "health": (0, 4),
        "entertainment": (0, 10),
        "education": (0, 2),
    }
    
    # Профили с ПОВЕДЕНЧЕСКИМИ особенностями
    PROFILES = [
        {
            "name": "balanced",
            "multipliers": {},
            "expense_ratio": (0.55, 0.75),
            "weekend_bias": 0.30,        # Обычный паттерн выходных
            "impulse_factor": 1.0,       # Обычная импульсивность
            "frequency_factor": 1.0,     # Обычная частота
        },
        {
            "name": "restaurant_lover",
            "multipliers": {"restaurants": (2.0, 3.5), "groceries": (0.4, 0.7)},
            "expense_ratio": (0.70, 0.88),
            "weekend_bias": 0.50,        # Много тратит в выходные (рестораны)
            "impulse_factor": 1.3,
            "frequency_factor": 1.2,
        },
        {
            "name": "subscription_hoarder",
            "multipliers": {"subscriptions": (3.0, 5.0)},
            "expense_ratio": (0.60, 0.80),
            "weekend_bias": 0.25,
            "impulse_factor": 0.8,       # Менее импульсивный (подписки = регулярные)
            "frequency_factor": 0.9,
        },
        {
            "name": "shopaholic",
            "multipliers": {"shopping": (2.5, 4.0), "entertainment": (1.3, 2.0)},
            "expense_ratio": (0.80, 0.95),
            "weekend_bias": 0.55,        # Шоппинг в выходные
            "impulse_factor": 2.5,       # Очень импульсивный!
            "frequency_factor": 1.4,
        },
        {
            "name": "taxi_user",
            "multipliers": {"transport": (2.5, 4.0)},
            "expense_ratio": (0.65, 0.85),
            "weekend_bias": 0.45,
            "impulse_factor": 1.2,
            "frequency_factor": 1.5,     # Много транзакций (каждая поездка)
        },
        {
            "name": "entertainment_fan",
            "multipliers": {"entertainment": (2.5, 4.0), "restaurants": (1.2, 1.8)},
            "expense_ratio": (0.70, 0.88),
            "weekend_bias": 0.60,        # Развлечения в выходные
            "impulse_factor": 1.8,
            "frequency_factor": 1.3,
        },
        {
            "name": "foodie",
            "multipliers": {"groceries": (1.6, 2.3), "restaurants": (1.4, 2.2)},
            "expense_ratio": (0.68, 0.85),
            "weekend_bias": 0.40,
            "impulse_factor": 1.1,
            "frequency_factor": 1.2,
        },
        {
            "name": "minimalist",
            "multipliers": {"shopping": (0.3, 0.5), "entertainment": (0.3, 0.6), "restaurants": (0.3, 0.6)},
            "expense_ratio": (0.40, 0.60),
            "weekend_bias": 0.25,
            "impulse_factor": 0.5,       # Не импульсивный
            "frequency_factor": 0.7,
        },
        {
            "name": "big_spender",
            "multipliers": {"shopping": (1.5, 2.0), "entertainment": (1.5, 2.0), "restaurants": (1.5, 2.0)},
            "expense_ratio": (0.88, 0.98),
            "weekend_bias": 0.50,
            "impulse_factor": 2.0,
            "frequency_factor": 1.3,
        },
        {
            "name": "saver",
            "multipliers": {cat: (0.5, 0.75) for cat in EXPENSE_CATEGORIES},
            "expense_ratio": (0.35, 0.55),
            "weekend_bias": 0.20,
            "impulse_factor": 0.4,
            "frequency_factor": 0.6,
        },
    ]
    
    def generate_monthly(self, profile: Dict, salary: float) -> Tuple[List[Dict], Dict[str, float], Dict[str, int]]:
        """Генерирует транзакции с поведенческими паттернами"""
        
        # 1. Общий бюджет
        expense_ratio = random.uniform(*profile.get("expense_ratio", (0.65, 0.85)))
        total_budget = salary * expense_ratio
        
        # 2. Доли по категориям
        shares = {}
        for cat in EXPENSE_CATEGORIES:
            base = BASE_SHARES[cat]
            mult_range = profile.get("multipliers", {}).get(cat, (0.85, 1.15))
            shares[cat] = base * random.uniform(*mult_range)
        
        total_share = sum(shares.values())
        shares = {cat: s / total_share for cat, s in shares.items()}
        
        # 3. Поведенческие параметры
        weekend_bias = profile.get("weekend_bias", 0.35)
        impulse_factor = profile.get("impulse_factor", 1.0)
        frequency_factor = profile.get("frequency_factor", 1.0)
        
        # 4. Генерация транзакций
        transactions = []
        category_stats = defaultdict(lambda: {"count": 0, "total": 0, "max": 0, "weekend_total": 0})
        
        for cat in EXPENSE_CATEGORIES:
            cat_budget = total_budget * shares[cat]
            
            # Количество транзакций с учётом frequency_factor
            base_count = random.randint(*self.TRANSACTION_COUNTS[cat])
            num_tx = max(0, int(base_count * frequency_factor * random.uniform(0.8, 1.2)))
            
            if num_tx == 0 or cat_budget < 100:
                continue
            
            # Распределение сумм с учётом impulse_factor
            if num_tx == 1:
                amounts = [cat_budget]
            else:
                # Высокий impulse_factor = больше разброс (одна большая + много мелких)
                alpha = [1.0 / impulse_factor] * num_tx
                # Делаем одну транзакцию "импульсной"
                if impulse_factor > 1.5 and num_tx > 2:
                    alpha[0] = impulse_factor
                
                proportions = np.random.dirichlet(alpha)
                amounts = [cat_budget * p for p in proportions]
            
            merchants = self.MERCHANTS.get(cat, ["Unknown"])
            
            for amount in amounts:
                amount = max(30, amount * random.uniform(0.85, 1.15))
                
                # Weekend с учётом weekend_bias
                is_weekend = random.random() < weekend_bias
                
                transactions.append({
                    "amount": round(amount, 2),
                    "category": cat,
                    "type": "expense",
                    "weekend": int(is_weekend),
                    "merchant": random.choice(merchants),
                })
                
                # Статистика
                category_stats[cat]["count"] += 1
                category_stats[cat]["total"] += amount
                category_stats[cat]["max"] = max(category_stats[cat]["max"], amount)
                if is_weekend:
                    category_stats[cat]["weekend_total"] += amount
        
        # 5. Доход
        transactions.append({
            "amount": round(salary * 0.4),
            "category": "income",
            "type": "income",
            "weekend": 0,
            "merchant": "Работодатель",
        })
        transactions.append({
            "amount": round(salary * 0.6),
            "category": "income",
            "type": "income",
            "weekend": 0,
            "merchant": "Работодатель",
        })
        
        # 6. Извлекаем фичи
        features = self._extract_features(transactions, category_stats)
        
        # 7. Вычисляем метки на основе ПРОФИЛЯ (не фичей!)
        labels = self._compute_labels_from_profile(profile, features)
        
        return transactions, features, labels
    
    def _extract_features(self, transactions: List[Dict], category_stats: Dict) -> Dict[str, float]:
        """Извлекает фичи БЕЗ share_* (чтобы избежать утечки)"""
        df = pd.DataFrame(transactions)
        exp = df[df["type"] == "expense"]
        inc = df[df["type"] == "income"]
        
        total_income = inc["amount"].sum() if not inc.empty else 0
        total_expenses = exp["amount"].sum() if not exp.empty else 0
        
        features = {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "savings_rate": (total_income - total_expenses) / total_income if total_income > 0 else 0,
            "expense_to_income_ratio": total_expenses / total_income if total_income > 0 else 1,
        }
        
        # По категориям (total, count, avg, std, max) — НО НЕ share!
        for cat in EXPENSE_CATEGORIES:
            cat_exp = exp[exp["category"] == cat]
            cat_total = cat_exp["amount"].sum() if not cat_exp.empty else 0
            cat_count = len(cat_exp)
            cat_avg = cat_exp["amount"].mean() if not cat_exp.empty else 0
            cat_std = cat_exp["amount"].std() if len(cat_exp) > 1 else 0
            cat_max = cat_exp["amount"].max() if not cat_exp.empty else 0
            
            features[f"total_{cat}"] = cat_total
            features[f"count_{cat}"] = cat_count
            features[f"avg_{cat}"] = cat_avg
            features[f"std_{cat}"] = cat_std
            features[f"max_{cat}"] = cat_max
            
            # Относительные к доходу (а не к расходам)
            features[f"ratio_income_{cat}"] = cat_total / total_income if total_income > 0 else 0
        
        # Weekend
        weekend_exp = exp[exp["weekend"] == 1]["amount"].sum() if not exp.empty else 0
        features["weekend_total"] = weekend_exp
        features["weekend_ratio"] = weekend_exp / total_expenses if total_expenses > 0 else 0
        
        # Общие транзакционные метрики
        if not exp.empty:
            features["num_transactions"] = len(exp)
            features["avg_transaction"] = exp["amount"].mean()
            features["median_transaction"] = exp["amount"].median()
            features["max_transaction"] = exp["amount"].max()
            features["min_transaction"] = exp["amount"].min()
            features["std_transaction"] = exp["amount"].std() if len(exp) > 1 else 0
            
            # Импульсивность
            features["impulse_ratio"] = features["max_transaction"] / features["median_transaction"] if features["median_transaction"] > 0 else 0
            features["cv_transaction"] = features["std_transaction"] / features["avg_transaction"] if features["avg_transaction"] > 0 else 0
            
            # Уникальность
            features["unique_merchants"] = exp["merchant"].nunique()
            features["unique_categories"] = exp["category"].nunique()
            features["tx_per_category"] = features["num_transactions"] / features["unique_categories"] if features["unique_categories"] > 0 else 0
        else:
            for key in ["num_transactions", "avg_transaction", "median_transaction",
                       "max_transaction", "min_transaction", "std_transaction",
                       "impulse_ratio", "cv_transaction", "unique_merchants",
                       "unique_categories", "tx_per_category"]:
                features[key] = 0
        
        # Концентрация трат (топ-3 категории)
        cat_totals = [(cat, features.get(f"total_{cat}", 0)) for cat in EXPENSE_CATEGORIES]
        cat_totals.sort(key=lambda x: x[1], reverse=True)
        top3_total = sum(t[1] for t in cat_totals[:3])
        features["top3_concentration"] = top3_total / total_expenses if total_expenses > 0 else 0
        
        return features
    
    def _compute_labels_from_profile(self, profile: Dict, features: Dict) -> Dict[str, int]:
        """
        Вычисляет метки на основе ПРОФИЛЯ + реальных данных.
        Это создаёт сложную зависимость, которую модель должна выучить.
        """
        labels = {}
        total_expenses = features.get("total_expenses", 0)
        total_income = features.get("total_income", 0)
        
        # 1. Категориальные метки — на основе ПРОФИЛЯ + данных
        profile_name = profile["name"]
        multipliers = profile.get("multipliers", {})
        
        # high_restaurants: профиль restaurant_lover/foodie/entertainment_fan + реальные траты
        rest_mult = multipliers.get("restaurants", (1, 1))[0]
        rest_total = features.get("total_restaurants", 0)
        labels["high_restaurants"] = int(
            rest_mult >= 1.5 and 
            rest_total > 0 and
            rest_total / total_expenses > 0.10 if total_expenses > 0 else False
        )
        
        # high_subscriptions: профиль subscription_hoarder + много подписок
        sub_mult = multipliers.get("subscriptions", (1, 1))[0]
        sub_count = features.get("count_subscriptions", 0)
        labels["high_subscriptions"] = int(
            sub_mult >= 2.5 and 
            sub_count >= 4
        )
        
        # high_shopping: профиль shopaholic/big_spender + импульсивность
        shop_mult = multipliers.get("shopping", (1, 1))[0]
        shop_total = features.get("total_shopping", 0)
        impulse = features.get("impulse_ratio", 0)
        labels["high_shopping"] = int(
            shop_mult >= 1.8 and 
            shop_total > 0 and
            impulse > 3
        )
        
        # high_transport: профиль taxi_user + много транзакций
        trans_mult = multipliers.get("transport", (1, 1))[0]
        trans_count = features.get("count_transport", 0)
        labels["high_transport"] = int(
            trans_mult >= 2.0 and 
            trans_count >= 15
        )
        
        # high_entertainment: профиль entertainment_fan + weekend траты
        ent_mult = multipliers.get("entertainment", (1, 1))[0]
        weekend_ratio = features.get("weekend_ratio", 0)
        labels["high_entertainment"] = int(
            ent_mult >= 2.0 and 
            weekend_ratio > 0.35
        )
        
        # 2. Поведенческие метки
        
        # impulse_buyer: высокий impulse_factor профиля + CV транзакций
        impulse_factor = profile.get("impulse_factor", 1.0)
        cv = features.get("cv_transaction", 0)
        labels["impulse_buyer"] = int(
            impulse_factor >= 1.8 and 
            cv > 0.8
        )
        
        # low_savings: expense_ratio профиля > 80% + реальные данные
        exp_ratio_range = profile.get("expense_ratio", (0.5, 0.7))
        avg_exp_ratio = (exp_ratio_range[0] + exp_ratio_range[1]) / 2
        real_savings = features.get("savings_rate", 0)
        labels["low_savings"] = int(
            avg_exp_ratio > 0.80 and 
            real_savings < 0.15
        )
        
        # weekend_spender: высокий weekend_bias + реальные данные
        weekend_bias = profile.get("weekend_bias", 0.3)
        weekend_real = features.get("weekend_ratio", 0)
        labels["weekend_spender"] = int(
            weekend_bias >= 0.45 and 
            weekend_real > 0.38
        )
        
        return labels
    
    def generate_dataset(self, num_samples: int = 100000) -> List[Dict]:
        """Генерирует датасет"""
        dataset = []
        
        print(f"🚀 Генерация {num_samples} сэмплов...")
        
        for _ in tqdm(range(num_samples)):
            profile = random.choice(self.PROFILES)
            
            salary = int(np.random.lognormal(np.log(70000), 0.5))
            salary = max(25000, min(salary, 350000))
            
            transactions, features, labels = self.generate_monthly(profile, salary)
            
            dataset.append({
                "profile": profile["name"],
                "salary": salary,
                "transactions": transactions,
                "features": features,
                "labels": labels,
            })
        
        return dataset
    
    def print_statistics(self, dataset: List[Dict]):
        """Статистика датасета"""
        print("\n" + "=" * 60)
        print("📊 СТАТИСТИКА ДАТАСЕТА")
        print("=" * 60)
        
        print(f"\n   Всего сэмплов: {len(dataset):,}")
        
        # Профили
        from collections import Counter
        profiles = Counter(d["profile"] for d in dataset)
        print("\n   Профили:")
        for p, c in profiles.most_common():
            print(f"      {p:25}: {c:6} ({c/len(dataset)*100:.1f}%)")
        
        # Метки
        print("\n   Метки (% положительных):")
        label_names = list(dataset[0]["labels"].keys())
        for label in label_names:
            positive = sum(1 for d in dataset if d["labels"][label] == 1)
            pct = positive / len(dataset) * 100
            bar = "█" * int(pct / 2) + "░" * (25 - int(pct / 2))
            status = "✓" if 10 < pct < 40 else "⚠️" if 5 < pct < 50 else "❌"
            print(f"      {label:25}: {bar} {pct:5.1f}% {status}")
        
        # Корреляция меток с профилями
        print("\n   Связь профилей и меток:")
        for profile_name in ["restaurant_lover", "shopaholic", "saver"]:
            profile_data = [d for d in dataset if d["profile"] == profile_name]
            if profile_data:
                print(f"\n      {profile_name}:")
                for label in label_names:
                    pct = sum(1 for d in profile_data if d["labels"][label] == 1) / len(profile_data) * 100
                    if pct > 20:
                        print(f"         {label}: {pct:.0f}%")
        
        # Средние показатели
        print("\n   Средние показатели:")
        avg_salary = np.mean([d["salary"] for d in dataset])
        avg_expense_ratio = np.mean([d["features"]["expense_to_income_ratio"] for d in dataset])
        avg_savings = np.mean([d["features"]["savings_rate"] for d in dataset])
        avg_impulse = np.mean([d["features"]["impulse_ratio"] for d in dataset])
        
        print(f"      Зарплата:        {avg_salary:,.0f}₽")
        print(f"      Расходы/Доход:   {avg_expense_ratio*100:.1f}%")
        print(f"      Сбережения:      {avg_savings*100:.1f}%")
        print(f"      Impulse ratio:   {avg_impulse:.1f}")
        
        # Проверка реалистичности
        print("\n   Проверка:")
        checks = [
            (0.5 < avg_expense_ratio < 0.9, f"Расходы/Доход: {avg_expense_ratio*100:.0f}%"),
            (0.1 < avg_savings < 0.5, f"Сбережения: {avg_savings*100:.0f}%"),
            (avg_impulse > 2, f"Impulse ratio: {avg_impulse:.1f}"),
        ]
        for ok, msg in checks:
            print(f"      {'✓' if ok else '❌'} {msg}")
def main():
    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    
    generator = TransactionGenerator()
    dataset = generator.generate_dataset(100000)
    
    generator.print_statistics(dataset)
    
    # JSON
    output_path = os.path.join(output_dir, "dataset_v3.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False)
    print(f"\n✅ Dataset: {output_path}")
    
    # CSV
    features_df = pd.DataFrame([d["features"] for d in dataset])
    labels_df = pd.DataFrame([d["labels"] for d in dataset])
    
    features_df.to_csv(os.path.join(output_dir, "features.csv"), index=False)
    labels_df.to_csv(os.path.join(output_dir, "labels.csv"), index=False)
    
    print(f"✅ Features: {os.path.join(output_dir, 'features.csv')}")
    print(f"✅ Labels: {os.path.join(output_dir, 'labels.csv')}")
    
    # Список фичей
    print(f"\n📋 Фичи ({len(features_df.columns)}):")
    for col in sorted(features_df.columns):
        print(f"   - {col}")
if __name__ == "__main__":
    main()