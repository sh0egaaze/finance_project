import json
import random
import os
import sys
from dataclasses import dataclass, field

# ============================================================
# КОНФИГУРАЦИЯ (Твой файл 1)
# ============================================================
@dataclass
class Config:
    project_dir: str = os.path.dirname(os.path.abspath(__file__))
    data_dir: str = ""
    train_dataset_size: int = 50000
    val_dataset_size: int = 5000
    
    expense_categories: dict = field(default_factory=lambda: {
        "продукты": [
            "хлеб", "молоко", "яйца", "сыр", "масло", "курица", "свинина",
            "говядина", "рыба", "рис", "гречка", "макароны", "картошка",
            "помидоры", "огурцы", "лук", "морковь", "капуста", "яблоки",
            "бананы", "апельсины", "сахар", "соль", "мука", "кефир",
            "сметана", "творог", "колбаса", "сосиски", "пельмени",
            "чай", "кофе", "сок", "вода", "печенье", "шоколад",
            "конфеты", "торт", "мороженое", "чипсы", "орехи",
        ],
        "напитки": [
            "кола", "пепси", "фанта", "спрайт", "пиво", "вино",
            "водка", "виски", "коньяк", "ром", "джин", "текила",
            "энергетик", "квас", "лимонад", "минералка", "компот",
        ],
        "фастфуд": [
            "бургер", "пицца", "шаурма", "хот-дог", "наггетсы",
            "картошка фри", "ролл", "суши", "лапша", "донер",
            "шашлык", "чебурек", "пирожок", "блины", "самса",
        ],
        "кафе_рестораны": [
            "обед в кафе", "ужин в ресторане", "завтрак в кофейне",
            "бизнес-ланч", "кофе в старбаксе", "латте", "капучино",
            "американо", "эспрессо", "чизкейк", "круассан",
        ],
        "транспорт": [
            "бензин", "дизель", "газ", "метро", "автобус", "трамвай",
            "троллейбус", "такси", "убер", "яндекс такси", "каршеринг",
            "парковка", "мойка машины", "техосмотр", "страховка осаго",
            "штраф гибдд", "проездной",
        ],
        "жильё": [
            "аренда квартиры", "ипотека", "коммуналка", "электричество",
            "газ за квартиру", "вода", "интернет", "ремонт", "мебель",
            "шторы", "лампочки", "краска", "обои",
        ],
        "одежда": [
            "футболка", "джинсы", "куртка", "пальто", "свитер",
            "рубашка", "платье", "юбка", "брюки", "шорты",
            "кроссовки", "ботинки", "туфли", "сапоги", "шапка",
            "шарф", "перчатки", "носки", "трусы", "бельё",
        ],
        "здоровье": [
            "таблетки", "лекарства", "витамины", "антибиотики",
            "визит к врачу", "стоматолог", "анализы", "узи",
            "прививка", "мазь", "капли", "пластырь", "бинт",
        ],
        "развлечения": [
            "кино", "театр", "концерт", "музей", "выставка",
            "боулинг", "бильярд", "караоке", "квест", "аквапарк",
            "зоопарк", "цирк", "парк аттракционов", "netflix",
            "spotify", "youtube premium", "подписка",
        ],
        "электроника": [
            "телефон", "смартфон", "айфон", "наушники", "зарядка",
            "чехол", "ноутбук", "планшет", "мышка", "клавиатура",
            "монитор", "флешка", "жёсткий диск", "видеокарта",
            "процессор", "оперативка", "принтер",
        ],
        "красота": [
            "шампунь", "гель для душа", "мыло", "крем", "дезодорант",
            "парфюм", "тушь", "помада", "лак для ногтей", "маска для лица",
            "стрижка", "маникюр", "педикюр", "массаж", "спа",
        ],
        "образование": [
            "курсы", "учебник", "книга", "репетитор", "онлайн курс",
            "udemy", "skillbox", "вебинар", "тетрадь", "ручка",
            "канцтовары",
        ],
        "домашние_животные": [
            "корм для кота", "корм для собаки", "наполнитель",
            "ветеринар", "поводок", "ошейник", "игрушка для кота",
            "клетка", "аквариум", "корм для рыбок",
        ],
        "спорт": [
            "абонемент в зал", "гантели", "коврик для йоги",
            "кроссовки для бега", "спортивная форма", "протеин",
            "бассейн", "велосипед", "самокат", "лыжи",
        ],
        "подарки": [
            "подарок", "цветы", "букет", "открытка", "сувенир",
            "игрушка", "конструктор лего",
        ],
        "прочее": [
            "сигареты", "зажигалка", "батарейки", "пакет",
            "доставка", "почта", "посылка", "химчистка", "прачечная",
            "ключи", "замок",
        ],
    })
    
    income_sources: dict = field(default_factory=lambda: {
        "зарплата": ["зарплата", "зп", "аванс", "получка", "оклад"],
        "фриланс": ["фриланс", "заказ", "проект", "халтура", "подработка", "работа на фрилансе"],
        "переводы": ["перевод от мамы", "перевод от папы", "перевод от друга", "перевод от бабушки", "перевод от дедушки", "возврат долга", "вернули долг"],
        "продажи": ["продал телефон", "продал ноутбук", "продал велик", "продал игру", "продал вещи на авито", "продал одежду", "продал мебель"],
        "кэшбэк": ["кэшбэк", "кешбек", "возврат", "cashback"],
        "стипендия": ["стипендия", "стипуха"],
        "прочий_доход": ["дивиденды", "проценты по вкладу", "процент", "выигрыш", "приз", "бонус", "премия"],
    })
    
    expense_templates: list = field(default_factory=lambda: [
        "купил {item} за {amount}{currency}", "купила {item} за {amount}{currency}",
        "взял {item} за {amount}{currency}", "взяла {item} за {amount}{currency}",
        "заплатил за {item} {amount}{currency}", "заплатила за {item} {amount}{currency}",
        "потратил на {item} {amount}{currency}", "потратила на {item} {amount}{currency}",
        "отдал за {item} {amount}{currency}", "отдала за {item} {amount}{currency}",
        "{item} — {amount}{currency}", "{item} {amount}{currency}", "{item} за {amount}{currency}",
        "оплатил {item} {amount}{currency}", "оплатила {item} {amount}{currency}",
        "купил {item} {amount}{currency}", "купила {item} {amount}{currency}",
        "{amount}{currency} за {item}", "{amount}{currency} на {item}", "{amount}{currency} {item}",
        "заказал {item} за {amount}{currency}", "заказала {item} за {amount}{currency}",
        "потратился на {item} {amount}{currency}", "потратилась на {item} {amount}{currency}",
        "ушло на {item} {amount}{currency}", "ушло {amount}{currency} на {item}",
        "{item} обошёлся в {amount}{currency}", "{item} обошлась в {amount}{currency}",
        "купил себе {item} за {amount}{currency}", "взял себе {item} за {amount}{currency}",
        "в магазине купил {item} за {amount}{currency}", "в магазине взял {item} за {amount}{currency}",
        "сходил за {item} отдал {amount}{currency}", "брал {item} за {amount}{currency}",
        "набрал {item} на {amount}{currency}", "скинул {amount}{currency} за {item}",
        "минус {amount}{currency} за {item}", "минус {amount}{currency} {item}",
        "-{amount}{currency} {item}", "-{amount}{currency} за {item}",
    ])
    
    income_templates: list = field(default_factory=lambda: [
        "получил {item} {amount}{currency}", "получила {item} {amount}{currency}",
        "пришла {item} {amount}{currency}", "пришёл {item} {amount}{currency}",
        "начислили {item} {amount}{currency}", "{item} {amount}{currency}",
        "зачислили {amount}{currency} {item}", "+{amount}{currency} {item}",
        "плюс {amount}{currency} {item}", "пришло {amount}{currency} — {item}",
        "на карту пришло {amount}{currency} {item}", "на счёт поступило {amount}{currency} {item}",
        "доход {amount}{currency} {item}", "{item} — получил {amount}{currency}",
        "заработал {amount}{currency} на {item}", "заработала {amount}{currency} на {item}",
        "мне перевели {amount}{currency} {item}", "скинули {amount}{currency} {item}",
        "кинули {amount}{currency} {item}",
    ])
    
    currency_variants: list = field(default_factory=lambda: [
        "р", "руб", "рублей", "рубля", "рубль", "₽",
        " р", " руб", " рублей", " рубля", " рубль", " ₽",
        "р.", " р.", "руб.", " руб.",
    ])
    
    def __post_init__(self):
        self.data_dir = os.path.join(self.project_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)

config = Config()

# ============================================================
# ГЕНЕРАТОР (Твой файл 2)
# ============================================================
def generate_amount():
    rand = random.random()
    if rand < 0.3: amount = random.randint(10, 200)
    elif rand < 0.6: amount = random.randint(200, 1000)
    elif rand < 0.8: amount = random.randint(1, 50) * 100
    elif rand < 0.95: amount = random.randint(5, 500) * 100
    else: amount = random.randint(500, 5000) * 100
    if random.random() < 0.15: amount = round(amount + random.random() * 0.99, 2)
    return amount

def format_amount(amount):
    if isinstance(amount, float) and amount != int(amount):
        return random.choice([f"{amount}", f"{amount:.2f}"])
    amount = int(amount)
    if amount >= 1000 and random.random() < 0.1 and amount % 1000 == 0:
        return f"{amount // 1000}к"
    if amount >= 1000 and random.random() < 0.15:
        return f"{amount:,}".replace(",", " ")
    return str(amount)

def add_noise(text):
    rand = random.random()
    if rand < 0.3: text = text.lower()
    elif rand < 0.35: text = text.upper()
    elif rand < 0.4: text = text.capitalize()
    if random.random() < 0.1: text = text.replace(" — ", " - ")
    if random.random() < 0.05:
        words = text.split()
        if len(words) > 2:
            idx = random.randint(0, len(words) - 2)
            words[idx] = words[idx] + "  "
            text = " ".join(words)
    return text.strip()

def generate_sample(is_income=False):
    if is_income:
        cat = random.choice(list(config.income_sources.keys()))
        item = random.choice(config.income_sources[cat])
        amount = generate_amount()
        if cat in ["зарплата", "фриланс"]: amount = random.randint(10, 300) * 1000
        elif cat == "стипендия": amount = random.randint(2, 20) * 1000
        template = random.choice(config.income_templates)
    else:
        cat = random.choice(list(config.expense_categories.keys()))
        item = random.choice(config.expense_categories[cat])
        amount = generate_amount()
        template = random.choice(config.expense_templates)
    
    amount_str = format_amount(amount)
    currency = random.choice(config.currency_variants)
    text = template.format(item=item, amount=amount_str, currency=currency)
    text = add_noise(text)
    return {"text": text, "amount": float(amount), "description": item.lower().strip(), "is_income": is_income}

def main():
    print("=" * 60)
    print("ГЕНЕРАЦИЯ СИНТЕТИЧЕСКОГО ДАТАСЕТА (ПОЛНАЯ ВЕРСИЯ)")
    print("=" * 60)
    random.seed(42)
    train_data = [generate_sample(random.random() < 0.25) for _ in range(config.train_dataset_size)]
    with open(os.path.join(config.data_dir, "dataset_train.json"), "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    
    random.seed(123)
    val_data = [generate_sample(random.random() < 0.25) for _ in range(config.val_dataset_size)]
    with open(os.path.join(config.data_dir, "dataset_val.json"), "w", encoding="utf-8") as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Готово: {len(train_data)} train, {len(val_data)} val.")

if __name__ == "__main__":
    main()
