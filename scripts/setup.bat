@echo off
REM =====================================================
REM Скрипт быстрой установки FinanceApp для Windows
REM =====================================================

echo.
echo ========================================
echo   FinanceApp - Быстрая установка
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python не найден! Установи Python 3.10+
    echo     Скачай: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python установлен

REM Проверка Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Node.js не найден! Установи Node.js 18+
    echo     Скачай: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js установлен

echo.
echo [*] Установка зависимостей бэкенда...
echo.

cd backend

REM Создание виртуального окружения
if not exist "venv" (
    python -m venv venv
    echo [OK] Создано виртуальное окружение
) else (
    echo [OK] Виртуальное окружение уже существует
)

REM Активация и установка зависимостей
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo [OK] Зависимости Python установлены

cd ..

echo.
echo [*] Установка зависимостей фронтенда...
echo.

call npm install
echo [OK] Зависимости Node.js установлены

echo.
echo [*] Настройка конфигурации...
echo.

REM Создание .env файла
if not exist ".env" (
    copy .env.example .env >nul
    echo [OK] Создан файл .env
) else (
    echo [OK] Файл .env уже существует
)

if not exist "backend\.env" (
    copy .env.example backend\.env >nul
    echo [OK] Создан файл backend\.env
)

echo.
echo ========================================
echo   УСТАНОВКА ЗАВЕРШЕНА!
echo ========================================
echo.
echo Следующие шаги:
echo.
echo 1. Отредактируй файл .env
echo.
echo 2. Создай базу данных PostgreSQL:
echo    - Открой pgAdmin или psql
echo    - CREATE USER finance_user WITH PASSWORD '1029384756Aa';
echo    - CREATE DATABASE finance_app OWNER finance_user;
echo.
echo 3. Примени миграции:
echo    cd backend
echo    venv\Scripts\activate
echo    alembic upgrade head
echo.
echo 4. Запусти бэкенд:
echo    uvicorn app.main:app --reload
echo.
echo 5. В новом терминале запусти фронтенд:
echo    npm run dev
echo.
echo Приложение будет доступно:
echo    Фронтенд: http://localhost:5173
echo    API docs: http://localhost:8000/docs
echo.
pause
