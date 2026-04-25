#!/bin/bash

# =====================================================
# Скрипт быстрой установки FinanceApp
# =====================================================

set -e

echo "🚀 FinanceApp - Быстрая установка"
echo "=================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода статуса
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Проверка наличия команды
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo ""
echo "📋 Проверка зависимостей..."
echo ""

# Проверка Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_status "Python $PYTHON_VERSION установлен"
else
    print_error "Python не найден! Установи Python 3.10+"
    exit 1
fi

# Проверка Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_status "Node.js $NODE_VERSION установлен"
else
    print_error "Node.js не найден! Установи Node.js 18+"
    exit 1
fi

# Проверка PostgreSQL
if command_exists psql; then
    print_status "PostgreSQL установлен"
else
    print_warning "PostgreSQL CLI не найден. Убедись, что PostgreSQL установлен и запущен."
fi

# Проверка Docker (опционально)
if command_exists docker; then
    print_status "Docker установлен (можно использовать docker-compose)"
else
    print_warning "Docker не установлен (опционально)"
fi

echo ""
echo "📦 Установка зависимостей бэкенда..."
echo ""

# Переход в папку backend
cd backend

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Создано виртуальное окружение"
else
    print_status "Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip -q
pip install -r requirements.txt -q
print_status "Зависимости Python установлены"

cd ..

echo ""
echo "📦 Установка зависимостей фронтенда..."
echo ""

# Установка npm зависимостей
npm install -q
print_status "Зависимости Node.js установлены"

echo ""
echo "⚙️ Настройка конфигурации..."
echo ""

# Создание .env файла если не существует
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_status "Создан файл .env (не забудь заполнить!)"
else
    print_status "Файл .env уже существует"
fi

if [ ! -f "backend/.env" ]; then
    cp .env.example backend/.env
    print_status "Создан файл backend/.env"
fi

echo ""
echo "=================================="
echo -e "${GREEN}✅ Установка завершена!${NC}"
echo "=================================="
echo ""
echo "📝 Следующие шаги:"
echo ""
echo "1. Отредактируй файл .env и добавь свои данные:"
echo "   - DATABASE_URL (подключение к PostgreSQL)"
echo "   - SECRET_KEY (секретный ключ)"
echo "   - TBANK_TOKEN (токен Т-Банка)"
echo ""
echo "2. Создай базу данных PostgreSQL:"
echo "   psql -U postgres"
echo "   CREATE USER finance_user WITH PASSWORD '1029384756Aa';"
echo "   CREATE DATABASE finance_app OWNER finance_user;"
echo ""
echo "3. Примени миграции:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   alembic upgrade head"
echo ""
echo "4. Запусти бэкенд:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "5. В новом терминале запусти фронтенд:"
echo "   npm run dev"
echo ""
echo "🌐 Приложение будет доступно:"
echo "   Фронтенд: http://localhost:5173"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "💡 Или используй Docker:"
echo "   docker-compose up --build"
echo ""
