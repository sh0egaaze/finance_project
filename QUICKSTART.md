# 🚀 Быстрый старт FinanceApp

## Вариант 1: Docker (самый простой)

```bash
# 1. Скопируй настройки
cp .env.example .env

# 2. Запусти всё одной командой
docker-compose up --build

# 3. Открой в браузере
# Фронтенд: http://localhost:3000
# API: http://localhost:8000/docs
```

---

## Вариант 2: Ручной запуск

### Терминал 1 - База данных

```bash
# Создай БД (выполни в psql)
CREATE USER finance_user WITH PASSWORD '1029384756Aa';
CREATE DATABASE finance_app OWNER finance_user;
```

### Терминал 2 - Бэкенд

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Терминал 3 - Фронтенд

```bash
npm install
npm run dev
```

### Открой в браузере

- **Приложение:** http://localhost:5173
- **API документация:** http://localhost:8000/docs

---

## 📋 Чек-лист

- [ ] PostgreSQL установлен и запущен
- [ ] База данных создана
- [ ] Файл `.env` заполнен
- [ ] Миграции применены (`alembic upgrade head`)
- [ ] Бэкенд запущен (порт 8000)
- [ ] Фронтенд запущен (порт 5173)

---

## 🔑 Тестовый вход

После первого запуска зарегистрируйся через API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "name": "Тест"}'
```

Или используй Swagger UI: http://localhost:8000/docs
