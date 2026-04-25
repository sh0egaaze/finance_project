# Finance App Backend

## 🏦 API для управления личными финансами

Backend часть дипломного проекта "Многофункциональное веб-приложение для управления финансами".

### Технологии

- **Python 3.11+**
- **FastAPI** - современный веб-фреймворк
- **SQLAlchemy 2.0** - ORM для работы с БД
- **PostgreSQL** - база данных
- **Alembic** - миграции БД
- **scikit-learn** - ML для категоризации
- **APScheduler** - планировщик задач
- **JWT** - аутентификация

### Установка и запуск

#### 1. Создание виртуального окружения

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

#### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 3. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env файл
```

#### 4. Создание базы данных

```bash
# PostgreSQL
createdb finance_app

# Применение миграций
alembic upgrade head
```

#### 5. Запуск сервера

```bash
# Development
python run.py

# или
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Документация

После запуска сервера:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входа FastAPI
│   ├── config.py            # Конфигурация
│   ├── database.py          # Подключение к БД
│   ├── scheduler.py         # Планировщик задач
│   ├── models/              # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── reminder.py
│   │   ├── category.py
│   │   ├── currency_rate.py
│   │   └── audit_log.py
│   ├── schemas/             # Pydantic схемы
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── reminder.py
│   │   ├── category.py
│   │   ├── currency.py
│   │   └── analytics.py
│   ├── routers/             # API endpoints
│   │   ├── auth.py
│   │   ├── transactions.py
│   │   ├── reminders.py
│   │   ├── analytics.py
│   │   ├── currency.py
│   │   └── tbank.py
│   └── services/            # Бизнес-логика
│       ├── auth_service.py
│       ├── transaction_service.py
│       ├── reminder_service.py
│       ├── currency_service.py
│       ├── analytics_service.py
│       ├── tbank_service.py
│       ├── email_service.py
│       └── categorization_service.py
├── alembic/                 # Миграции БД
├── tests/                   # Тесты
├── requirements.txt
├── .env.example
└── README.md
```

### API Endpoints

#### Аутентификация
- `POST /api/auth/register` - Регистрация
- `POST /api/auth/login` - Вход
- `GET /api/auth/me` - Текущий пользователь

#### Транзакции
- `GET /api/transactions` - Список транзакций
- `POST /api/transactions` - Добавить транзакцию
- `GET /api/transactions/{id}` - Получить транзакцию
- `PUT /api/transactions/{id}` - Обновить
- `DELETE /api/transactions/{id}` - Удалить
- `GET /api/transactions/stats` - Статистика
- `GET /api/transactions/suspicious` - Подозрительные

#### Напоминания
- `GET /api/reminders` - Список напоминаний
- `POST /api/reminders` - Создать напоминание
- `GET /api/reminders/upcoming` - Предстоящие
- `PUT /api/reminders/{id}` - Обновить
- `DELETE /api/reminders/{id}` - Удалить

#### Аналитика
- `GET /api/analytics/dashboard` - Данные для дашборда
- `GET /api/analytics/spending-by-category` - По категориям
- `GET /api/analytics/monthly-stats` - По месяцам
- `GET /api/analytics/predictions` - Прогноз
- `GET /api/analytics/saving-tips` - Советы по экономии

#### Курсы валют
- `GET /api/currency/rates` - Актуальные курсы
- `POST /api/currency/convert` - Конвертация

#### Т-Банк
- `POST /api/tbank/connect` - Подключить
- `POST /api/tbank/sync` - Синхронизация
- `GET /api/tbank/status` - Статус

### Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=app --cov-report=html
```

### Лицензия

MIT License © 2025 Соколов Арсений Юрьевич
