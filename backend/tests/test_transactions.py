"""
Тесты транзакций
"""
import pytest
from datetime import datetime


def test_create_transaction(client, auth_headers):
    """Тест создания транзакции"""
    response = client.post(
        "/api/transactions",
        json={
            "amount": 500,
            "description": "Обед в кафе",
            "source": "cash"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == -500  # Расходы отрицательные
    assert data["description"] == "Обед в кафе"
    assert data["category"] == "food"  # Автокатегоризация


def test_create_transaction_with_category(client, auth_headers):
    """Тест создания транзакции с указанной категорией"""
    response = client.post(
        "/api/transactions",
        json={
            "amount": 1000,
            "description": "Какая-то покупка",
            "source": "manual",
            "category": "shopping"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "shopping"
    assert data["category_manual"] == True


def test_get_transactions(client, auth_headers):
    """Тест получения списка транзакций"""
    # Создаём несколько транзакций
    for i in range(3):
        client.post(
            "/api/transactions",
            json={
                "amount": 100 * (i + 1),
                "description": f"Транзакция {i + 1}",
                "source": "manual"
            },
            headers=auth_headers
        )
    
    response = client.get("/api/transactions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_get_transactions_with_filter(client, auth_headers):
    """Тест фильтрации транзакций"""
    # Создаём транзакции разных категорий
    client.post(
        "/api/transactions",
        json={"amount": 100, "description": "Такси", "source": "cash"},
        headers=auth_headers
    )
    client.post(
        "/api/transactions",
        json={"amount": 200, "description": "Продукты в пятерочке", "source": "cash"},
        headers=auth_headers
    )
    
    # Фильтр по категории
    response = client.get(
        "/api/transactions?category=food",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["category"] == "food" for item in data["items"])


def test_get_transaction_by_id(client, auth_headers):
    """Тест получения транзакции по ID"""
    # Создаём транзакцию
    create_response = client.post(
        "/api/transactions",
        json={"amount": 500, "description": "Тестовая транзакция", "source": "manual"},
        headers=auth_headers
    )
    transaction_id = create_response.json()["id"]
    
    # Получаем по ID
    response = client.get(f"/api/transactions/{transaction_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == transaction_id


def test_update_transaction(client, auth_headers):
    """Тест обновления транзакции"""
    # Создаём транзакцию
    create_response = client.post(
        "/api/transactions",
        json={"amount": 500, "description": "Старое описание", "source": "manual"},
        headers=auth_headers
    )
    transaction_id = create_response.json()["id"]
    
    # Обновляем
    response = client.put(
        f"/api/transactions/{transaction_id}",
        json={"description": "Новое описание", "category": "entertainment"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Новое описание"
    assert response.json()["category"] == "entertainment"


def test_delete_transaction(client, auth_headers):
    """Тест удаления транзакции"""
    # Создаём транзакцию
    create_response = client.post(
        "/api/transactions",
        json={"amount": 500, "description": "Для удаления", "source": "manual"},
        headers=auth_headers
    )
    transaction_id = create_response.json()["id"]
    
    # Удаляем
    response = client.delete(f"/api/transactions/{transaction_id}", headers=auth_headers)
    assert response.status_code == 204
    
    # Проверяем, что удалена
    response = client.get(f"/api/transactions/{transaction_id}", headers=auth_headers)
    assert response.status_code == 404


def test_get_stats(client, auth_headers):
    """Тест получения статистики"""
    response = client.get("/api/transactions/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_income" in data
    assert "total_expense" in data
    assert "balance" in data
