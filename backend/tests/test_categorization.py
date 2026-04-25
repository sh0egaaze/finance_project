"""
Тесты ML категоризации
"""
import pytest
from app.services.categorization_service import CategorizationService, get_categorization_service
from app.models.transaction import TransactionCategory


@pytest.fixture
def categorizer():
    """Fixture для сервиса категоризации"""
    return get_categorization_service()


def test_categorize_food(categorizer):
    """Тест категоризации еды"""
    test_cases = [
        "Пятёрочка",
        "Обед в кафе",
        "Продукты",
        "Яндекс Еда",
        "Макдоналдс",
        "Купил булочку",
    ]
    
    for description in test_cases:
        category, confidence = categorizer.categorize(description)
        assert category == TransactionCategory.FOOD, f"Failed for: {description}"
        assert confidence > 0.5


def test_categorize_transport(categorizer):
    """Тест категоризации транспорта"""
    test_cases = [
        "Яндекс Такси",
        "Метро",
        "АЗС Лукойл",
        "Бензин",
    ]
    
    for description in test_cases:
        category, confidence = categorizer.categorize(description)
        assert category == TransactionCategory.TRANSPORT, f"Failed for: {description}"


def test_categorize_entertainment(categorizer):
    """Тест категоризации развлечений"""
    test_cases = [
        "Кинотеатр",
        "Netflix",
        "Steam",
        "Концерт",
    ]
    
    for description in test_cases:
        category, confidence = categorizer.categorize(description)
        assert category == TransactionCategory.ENTERTAINMENT, f"Failed for: {description}"


def test_categorize_by_mcc(categorizer):
    """Тест категоризации по MCC коду"""
    # MCC 5411 - Grocery Stores
    category, confidence = categorizer.categorize("Какой-то магазин", mcc_code="5411")
    assert category == TransactionCategory.FOOD
    assert confidence >= 0.95


def test_categorize_unknown(categorizer):
    """Тест категоризации неизвестного описания"""
    category, confidence = categorizer.categorize("xyzabc123")
    assert category == TransactionCategory.OTHER
    assert confidence < 0.9
