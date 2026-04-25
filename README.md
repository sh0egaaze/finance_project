# 💰 FinanceApp - Многофункциональное веб-приложение для управления финансами

## 📋 Содержание
1. [Требования](#требования)
2. [Быстрый старт с Docker](#быстрый-старт-с-docker)
3. [Ручная установка](#ручная-установка)
4. [Настройка Т-Банк API](#настройка-т-банк-api)
5. [Структура проекта](#структура-проекта)
6. [API документация](#api-документация)
7. [Частые проблемы](#частые-проблемы)

---

## 📌 Требования

### Минимальные требования:
- **Python** 3.10 или выше
- **Node.js** 18 или выше
- **PostgreSQL** 14 или выше
- **Git**

### Или для Docker:
- **Docker** 20.10+
- **Docker Compose** 2.0+

---

## 🚀 Быстрый старт с Docker (Рекомендуется)

Это самый простой способ запустить всё приложение.

### Шаг 1: Клонируй/скачай проект

```bash
# Если используешь Git
git clone <твой-репозиторий>
cd finance-app
```

### Шаг 2: Создай файл с переменными окружения

```bash
# Создай файл .env в корне проекта
cp .env.example .env
```

Или создай `.env` вручную:

```env
# База данных
DATABASE_URL=postgresql://finance_user:1029384756Aa@db:5432/finance_app
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=1029384756Aa
POSTGRES_DB=finance_app

# Безопасность
SECRET_KEY=your-super-secret-key-change-in-production-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Т-Банк API (получи на https://www.tbank.ru/api/)
TBANK_TOKEN=your_tbank_token_here

# Email для уведомлений (опционально)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# API курсов валют (бесплатный ключ на https://exchangeratesapi.io/)
EXCHANGE_RATES_API_KEY=your_api_key_here
```

### Шаг 3: Запусти через Docker Compose

```bash
# Собери и запусти все контейнеры
docker-compose up --build

# Или в фоновом режиме
docker-compose up --build -d
```

### Шаг 4: Открой приложение

- **Фронтенд:** http://localhost:3000
- **API документация:** http://localhost:8000/docs
- **Альтернативная документация:** http://localhost:8000/redoc

### Остановка приложения

```bash
# Остановить контейнеры
docker-compose down

# Остановить и удалить данные (включая БД)
docker-compose down -v
```

---

## 🔧 Ручная установка (без Docker)

### Часть 1: Установка PostgreSQL

#### Windows:
1. Скачай PostgreSQL с https://www.postgresql.org/download/windows/
2. Запусти установщик, запомни пароль для пользователя `postgres`
3. После установки открой **pgAdmin** или **psql**

#### macOS:
```bash
# Через Homebrew
brew install postgresql@14
brew services start postgresql@14
```

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Часть 2: Создание базы данных

```bash
# Войди в PostgreSQL
sudo -u postgres psql

# Или на Windows через psql
psql -U postgres
```

Выполни SQL команды:

```sql
-- Создай пользователя
CREATE USER finance_user WITH PASSWORD '1029384756Aa';

-- Создай базу данных
CREATE DATABASE finance_app OWNER finance_user;

-- Дай права
GRANT ALL PRIVILEGES ON DATABASE finance_app TO finance_user;

-- Выйди
\q
```

### Часть 3: Установка Python и зависимостей бэкенда

#### Шаг 1: Установи Python 3.10+

Скачай с https://www.python.org/downloads/

Проверь установку:
```bash
python --version  # или python3 --version
```

#### Шаг 2: Создай виртуальное окружение

```bash
# Перейди в папку backend
cd backend

# Создай виртуальное окружение
python -m venv venv

# Активируй его:
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

#### Шаг 3: Установи зависимости

```bash
pip install -r requirements.txt
```

#### Шаг 4: Создай файл .env в папке backend

```bash
# backend/.env
DATABASE_URL=postgresql://finance_user:1029384756Aa@localhost:5432/finance_app
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TBANK_TOKEN=your_tbank_token_here
```

#### Шаг 5: Примени миграции базы данных

```bash
# Находясь в папке backend с активированным venv
alembic upgrade head
```

#### Шаг 6: Запусти бэкенд

```bash
# Режим разработки с автоперезагрузкой
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или для продакшена
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

✅ Бэкенд доступен на http://localhost:8000
✅ Документация API на http://localhost:8000/docs

### Часть 4: Установка Node.js и запуск фронтенда

#### Шаг 1: Установи Node.js 18+

Скачай с https://nodejs.org/

Проверь установку:
```bash
node --version
npm --version
```

#### Шаг 2: Установи зависимости фронтенда

```bash
# Вернись в корневую папку проекта
cd ..

# Установи зависимости
npm install
```

#### Шаг 3: Настрой URL бэкенда

Отредактируй файл `src/api/client.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

#### Шаг 4: Запусти фронтенд

```bash
# Режим разработки
npm run dev

# Приложение будет доступно на http://localhost:5173
```

#### Шаг 5: Сборка для продакшена

```bash
npm run build

# Собранные файлы будут в папке dist/
```

---

## 🏦 Настройка Т-Банк API

### Шаг 1: Получи токен

1. Зайди на https://www.tbank.ru/api/
2. Зарегистрируйся как разработчик
3. Создай приложение
4. Получи токен доступа (sandbox для тестов или production)

### Шаг 2: Добавь токен в .env

```env
TBANK_TOKEN=your_actual_token_here
```

### Шаг 3: Настрой синхронизацию

В приложении перейди в **Настройки** → **Интеграции** → **Т-Банк** и включи автоматическую синхронизацию.

---

## 📁 Структура проекта

```
finance-app/
├── backend/                    # Бэкенд на FastAPI
│   ├── app/
│   │   ├── api/               # API роутеры
│   │   │   └── v1/
│   │   │       ├── auth.py    # Авторизация
│   │   │       ├── transactions.py
│   │   │       ├── categories.py
│   │   │       ├── reminders.py
│   │   │       ├── analytics.py
│   │   │       ├── currency.py
│   │   │       └── tbank.py   # Интеграция Т-Банк
│   │   ├── core/              # Конфигурация
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/            # SQLAlchemy модели
│   │   │   └── models.py
│   │   ├── schemas/           # Pydantic схемы
│   │   │   └── schemas.py
│   │   ├── services/          # Бизнес-логика
│   │   │   ├── categorizer.py # ИИ категоризация
│   │   │   ├── analytics.py
│   │   │   ├── predictions.py
│   │   │   └── tbank_client.py
│   │   ├── tasks/             # Фоновые задачи
│   │   │   └── scheduler.py
│   │   └── main.py            # Точка входа
│   ├── alembic/               # Миграции БД
│   ├── tests/                 # Тесты
│   ├── requirements.txt
│   └── Dockerfile
├── src/                       # Фронтенд на React
│   ├── api/                   # API клиент
│   ├── components/            # React компоненты
│   ├── types/                 # TypeScript типы
│   ├── data/                  # Моковые данные
│   └── App.tsx
├── docker-compose.yml
├── Dockerfile.frontend
└── README.md
```

---

## 📚 API документация

После запуска бэкенда, документация доступна:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Основные эндпоинты:

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Авторизация |
| GET | `/api/v1/transactions/` | Список транзакций |
| POST | `/api/v1/transactions/` | Добавить транзакцию |
| POST | `/api/v1/transactions/categorize` | ИИ категоризация |
| GET | `/api/v1/analytics/summary` | Сводка по финансам |
| GET | `/api/v1/analytics/predictions` | Прогнозы |
| GET | `/api/v1/reminders/` | Напоминания |
| POST | `/api/v1/reminders/` | Создать напоминание |
| GET | `/api/v1/currency/rates` | Курсы валют |
| POST | `/api/v1/tbank/sync` | Синхронизация с Т-Банк |

---

## ❓ Частые проблемы

### 1. Ошибка подключения к PostgreSQL

```
connection refused / could not connect to server
```

**Решение:**
- Проверь, что PostgreSQL запущен: `sudo systemctl status postgresql`
- Проверь порт: по умолчанию 5432
- Проверь данные в `.env`

### 2. Ошибка миграций Alembic

```
alembic.util.exc.CommandError: Can't locate revision
```

**Решение:**
```bash
# Удали папку alembic/versions и создай заново
rm -rf alembic/versions/*
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

### 3. CORS ошибки в браузере

```
Access-Control-Allow-Origin error
```

**Решение:**
В `backend/app/main.py` проверь настройки CORS:
```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]
```

### 4. Порт уже занят

```
Address already in use
```

**Решение:**
```bash
# Найди процесс
lsof -i :8000  # или :5173

# Убей процесс
kill -9 <PID>

# Или используй другой порт
uvicorn app.main:app --port 8001
```

### 5. Ошибки при установке пакетов Python

```
error: Microsoft Visual C++ 14.0 is required
```

**Решение (Windows):**
Установи Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/

### 6. Node.js ошибки

```
ENOENT: no such file or directory
```

**Решение:**
```bash
# Удали node_modules и переустанови
rm -rf node_modules package-lock.json
npm install
```

---

## 🔐 Безопасность (важно для продакшена!)

1. **Измени SECRET_KEY** на длинный случайный ключ:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

2. **Используй HTTPS** в продакшене

3. **Настрой firewall** - закрой порты БД извне

4. **Регулярно обновляй** зависимости:
```bash
pip install --upgrade -r requirements.txt
npm update
```

---

## 📞 Поддержка

Если возникли вопросы:
1. Проверь раздел [Частые проблемы](#частые-проблемы)
2. Посмотри логи: `docker-compose logs -f`
3. Создай Issue в репозитории

---

## 📄 Лицензия

MIT License - используй как хочешь! 🎓

Удачи с дипломом! 🚀
#   f i n a n c e _ p r o j e c t  
 