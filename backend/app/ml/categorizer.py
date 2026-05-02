"""
Категоризатор транзакций на RuBERT.

Использование в роутерах:
    from app.ml.categorizer import categorize, categorize_batch

    result = categorize("ПЯТЕРОЧКА №42")
    print(result.category_code)   # "food"
    print(result.category_name)   # "Еда и продукты"
    print(result.confidence)      # 0.9823
    print(result.method)          # "rubert"

    results = categorize_batch(["ПЯТЕРОЧКА", "ЯНДЕКС ТАКСИ"])
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Результат предсказания
# ----------------------------------------------------------

@dataclass
class CategoryPrediction:
    category_code: str
    category_name: str
    confidence: float
    method: str             # "rubert" | "fallback" | "fallback_no_match" | "empty_input"
    top_3: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category_code": self.category_code,
            "category_name": self.category_name,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "top_3": self.top_3,
        }


# ----------------------------------------------------------
# Fallback по ключевым словам
# Работает когда модель ещё не обучена или не загрузилась
# ----------------------------------------------------------

KEYWORD_RULES = [
    ("food", "Еда и продукты", [
        "пятёрочка", "пятерочка", "магнит", "перекрёсток", "перекресток",
        "лента", "ашан", "дикси", "вкусвилл", "окей", "спар", "spar",
        "глобус", "светофор", "чижик", "верный", "самокат", "лавка",
        "продукт", "гастроном", "универсам", "fixprice", "фиксп",
        "sbermarket", "купер маркет", "монетка", "командор",
        "булочная", "хлебный", "кондитерская", "бакалея", "дикси",
    ]),
    ("restaurants", "Рестораны и кафе", [
        "макдоналдс", "mcdonald", "kfc", "бургер кинг", "burger king",
        "subway", "додо", "dodo", "папа джонс", "dominos", "domino",
        "якитория", "тануки", "шоколадница", "starbucks", "старбакс",
        "ресторан", "кафе", "столовая", "пиццерия", "суши", "бар", "паб",
        "яндекс еда", "delivery club", "теремок", "крошка картошка",
        "фастфуд", "бистро", "шаурма", "пекарня", "кофейня", "блинная",
        "coffee like", "cofix", "surf coffee",
    ]),
    ("transport", "Транспорт", [
        "яндекс такси", "uber", "ситимобил", "gett", "такси", "ржд",
        "аэрофлот", "s7", "победа", "авиабилет", "метро", "тройка",
        "подорожник", "электричка", "автобус", "делимобиль", "яндекс драйв",
        "ситидрайв", "belkacar", "whoosh", "urent", "юрент", "каршеринг",
        "азс", "лукойл", "газпромнефть", "роснефть", "бензин", "заправка",
        "парковка", "шиномонтаж", "аэроэкспресс", "маршрутка",
    ]),
    ("housing", "Жильё и ЖКХ", [
        "жкх", "квартплата", "коммунал", "мосэнерго", "мосводоканал",
        "мосгаз", "электроэнерг", "водоснабж", "газоснабж", "отопление",
        "капремонт", "управляющая компани", "тсж", "аренда квартир",
        "аренда жиль", "съём квартир", "ипотека", "домофон",
        "ростелеком", "мгтс", "триколор", "вывоз мусора",
    ]),
    ("shopping", "Покупки и товары", [
        "ozon", "озон", "wildberries", "вайлдберри", "яндекс маркет",
        "aliexpress", "amazon", "сбермегамаркет", "megamarket",
        "dns", "днс", "м.видео", "мвидео", "эльдорадо", "ситилинк",
        "zara", "h&m", "uniqlo", "gloria jeans", "спортмастер",
        "декатлон", "decathlon", "leroy merlin", "леруа", "ikea", "икеа",
        "hoff", "лэтуаль", "ривгош", "детский мир", "золотое яблоко",
        "lamoda", "avito", "авито",
    ]),
    ("health", "Здоровье и медицина", [
        "аптека", "горздрав", "36.6", "столичка", "еаптека", "ригла",
        "поликлиника", "больниц", "медицин", "инвитро", "гемотест",
        "helix", "стоматолог", "анализ", "мрт", "узи", "лекарств",
        "витамин", "дмс", "клиника", "медси", "оптика",
    ]),
    ("entertainment", "Развлечения", [
        "кинотеатр", "каро", "синема", "кинопоиск", "netflix", "ivi",
        "okko", "premier", "spotify", "яндекс музыка", "apple music",
        "steam", "playstation", "xbox", "театр", "концерт", "музей",
        "боулинг", "картинг", "квест", "билет на", "wink",
    ]),
    ("education", "Образование", [
        "skillbox", "нетология", "geekbrains", "coursera", "udemy",
        "яндекс практикум", "skillfactory", "stepik", "hexlet", "otus",
        "skyeng", "курс", "репетитор", "университет", "колледж",
        "автошкол", "литрес", "duolingo", "lingualeo",
    ]),
    ("transfers", "Переводы", [
        "перевод на карту", "перевод сбп", "p2p перевод",
        "перевод между счет", "алимент", "быстрый перевод",
    ]),
    ("salary", "Зарплата и доход", [
        "зарплата", "аванс", "заработная плата", "премия", "гонорар",
        "дивиденд", "возврат налог", "налоговый вычет", "кэшбэк",
        "стипендия", "пенсия", "пособие", "начисление процент",
        "доход по вкладу",
    ]),
    ("beauty", "Красота и уход", [
        "парикмахер", "барбершоп", "салон красот", "маникюр", "педикюр",
        "массаж", "spa", "спа", "косметолог", "эпиляция", "стрижк",
        "шугаринг", "татуаж", "брови", "ресниц", "окрашивание",
    ]),
    ("sports", "Спорт и фитнес", [
        "фитнес", "world class", "x-fit", "ddx", "alex fitness",
        "бассейн", "тренажёр", "тренажер", "йога", "пилатес", "бокс",
        "каток", "абонемент фитнес", "кроссфит", "crossfit",
    ]),
    ("telecom", "Связь и телеком", [
        "мтс оплата", "билайн оплата", "мегафон оплата", "теле2",
        "tele2", "yota", "тинькофф мобайл", "сбермобайл",
        "мобильная связь", "пополнение баланса телефон", "роуминг",
    ]),
    ("insurance", "Страхование", [
        "осаго", "каско", "страховани", "ингосстрах", "ресо гарантия",
        "согаз", "росгосстрах", "страховой полис", "дмс оплата",
        "туристическая страховк",
    ]),
    ("taxes", "Налоги и штрафы", [
        "налог на имущество", "транспортный налог", "ндфл",
        "штраф гибдд", "штраф за парковку", "госпошлина",
        "фнс оплата", "судебный пристав", "налог самозанятого",
        "пени по налог",
    ]),
    ("travel", "Путешествия", [
        "отель", "гостиниц", "хостел", "booking", "ostrovok",
        "aviasales", "турагентство", "tui", "anex", "coral",
        "санатори", "airbnb", "суточно", "виза оплат", "onetwottrip",
    ]),
    ("pets", "Домашние животные", [
        "ветеринар", "ветаптек", "зоомагазин", "четыре лапы",
        "petshop", "бетховен", "корм для", "груминг зоо",
        "зоотовар", "прививки животн",
    ]),
    ("subscriptions", "Подписки и сервисы", [
        "яндекс плюс", "яндекс+", "сберпрайм", "icloud",
        "google one", "microsoft 365", "adobe", "telegram premium",
        "vpn подписк", "антивирус касперский", "chatgpt", "midjourney",
        "подписка", "автопродление",
    ]),
    ("cash", "Наличные", [
        "снятие наличных", "банкомат", "atm снятие",
        "выдача наличных", "внесение наличных",
    ]),
]


def _fallback_predict(text: str) -> "CategoryPrediction":
    text_lower = text.lower()

    for category_code, category_name, keywords in KEYWORD_RULES:
        for keyword in keywords:
            if keyword in text_lower:
                return CategoryPrediction(
                    category_code=category_code,
                    category_name=category_name,
                    confidence=0.6,
                    method="fallback",
                    top_3=[{
                        "category_code": category_code,
                        "category_name": category_name,
                        "confidence": 0.6,
                    }],
                )

    logger.info(
        "Текст не распознан fallback-категоризатором: '%s' — "
        "отправлено в очередь для дообучения",
        text,
    )

    return CategoryPrediction(
        category_code="other",
        category_name="Другое",
        confidence=0.0,
        method="fallback_no_match",
        top_3=[],
    )


# ----------------------------------------------------------
# Предобработка текста
# ----------------------------------------------------------

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b\d{4,}\b", "", text)
    text = re.sub(r"[^\w\s\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------------------------------------------
# Публичный API
# ----------------------------------------------------------

def categorize(description: str) -> CategoryPrediction:
    """
    Категоризировать одну транзакцию.
    """
    if not description or not isinstance(description, str) or not description.strip():
        return CategoryPrediction(
            category_code="other",
            category_name="Другое",
            confidence=0.0,
            method="empty_input",
            top_3=[],
        )

    from .model_loader import registry

    model_data = registry.get("categorizer")

    if model_data is None:
        logger.debug("Модель не загружена, используется fallback")
        return _fallback_predict(description)

    try:
        processed = preprocess_text(description)
        if not processed:
            return CategoryPrediction(
                category_code="other",
                category_name="Другое",
                confidence=0.0,
                method="empty_input",
                top_3=[],
            )
        return _predict_rubert(processed, model_data)

    except Exception as e:
        logger.error("Ошибка категоризации '%s': %s", description, e)
        return _fallback_predict(description)


def categorize_batch(descriptions: List[str]) -> List[CategoryPrediction]:
    """
    Категоризировать список транзакций.
    """
    return [categorize(desc) for desc in descriptions]


# ----------------------------------------------------------
# Внутренняя функция предсказания
# ----------------------------------------------------------

def _predict_rubert(text: str, model_data: dict) -> CategoryPrediction:
    import torch

    model = model_data["model"]
    tokenizer = model_data["tokenizer"]
    id2cat = model_data["id2cat"]
    category_names = model_data["category_names"]
    device = model_data["device"]

    encoding = tokenizer(
        text,
        max_length=64,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        outputs = model(**encoding)
        probs = torch.softmax(outputs.logits, dim=-1)[0]

    pred_id = torch.argmax(probs).item()
    confidence = probs[pred_id].item()
    pred_cat = id2cat[pred_id]

    top_indices = torch.argsort(probs, descending=True)[:3]
    top_3 = [
        {
            "category_code": id2cat[idx.item()],
            "category_name": category_names.get(
                id2cat[idx.item()], id2cat[idx.item()]
            ),
            "confidence": round(probs[idx].item(), 4),
        }
        for idx in top_indices
    ]

    return CategoryPrediction(
        category_code=pred_cat,
        category_name=category_names.get(pred_cat, pred_cat),
        confidence=confidence,
        method="rubert",
        top_3=top_3,
    )