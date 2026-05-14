"""Аутентификационные endpoints"""
from app.config import get_settings
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.database import get_db
from app.models import User, Category, AuditLog
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["Авторизация"])

limiter = Limiter(key_func=get_remote_address)

# Настройки
_settings = get_settings()
SECRET_KEY = _settings.SECRET_KEY
ALGORITHM = _settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Время жизни токена верификации email (24 часа)
EMAIL_VERIFICATION_EXPIRE_HOURS = 24

# Account lockout: трекинг неудачных попыток входа
LOGIN_ATTEMPTS: dict[str, int] = {}
LOGIN_LOCKOUT_UNTIL: dict[str, datetime] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# ======== Pydantic модели ========
class UserCreate(BaseModel):
    """Схема для регистрации нового пользователя"""
    email: EmailStr = Field(
        ...,
        description="Email пользователя (используется для входа)",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=12,
        description="Пароль (мин. 12 символов, цифра, заглавная буква, спецсимвол)",
        examples=["SecurePass123!"]
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Полное имя пользователя",
        examples=["Иван Иванов"]
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Пароль должен содержать не менее 12 символов")
        if not any(char.isdigit() for char in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(char.isupper() for char in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(char in "!@#$%^&*()-_+=" for char in v):
            raise ValueError("Пароль должен содержать спецсимволы (!@#$%^*...)")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!",
                    "full_name": "Иван Иванов"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: int = Field(..., description="Уникальный идентификатор пользователя", examples=[1])
    email: str = Field(..., description="Email пользователя", examples=["user@example.com"])
    full_name: Optional[str] = Field(None, description="Полное имя", examples=["Иван Иванов"])
    is_active: bool = Field(..., description="Активен ли аккаунт", examples=[True])
    is_superuser: bool = Field(False, description="Является ли администратором", examples=[False])
    email_verified: bool = Field(False, description="Подтверждён ли email", examples=[False])
    email_notifications: bool = Field(..., description="Включены ли email-уведомления", examples=[True])
    tbank_connected: bool = Field(False, description="Подключён ли Т-Банк", examples=[False])

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    """Схема JWT токена"""
    access_token: str = Field(
        ...,
        description="JWT access токен для авторизации",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    token_type: str = Field(
        ...,
        description="Тип токена",
        examples=["bearer"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjk5OTk5OTk5fQ.abc123",
                    "token_type": "bearer"
                }
            ]
        }
    }


class LoginRequest(BaseModel):
    """Схема для входа в систему"""
    email: EmailStr = Field(..., description="Email пользователя", examples=["user@example.com"])
    password: str = Field(..., description="Пароль пользователя", examples=["SecurePass123!"])


class ResendVerificationRequest(BaseModel):
    """Схема для повторной отправки верификации"""
    email: EmailStr = Field(..., description="Email для повторной отправки", examples=["user@example.com"])


class MessageResponse(BaseModel):
    """Схема ответа с сообщением"""
    message: str = Field(..., description="Сообщение", examples=["Операция выполнена"])


DEFAULT_CATEGORIES = [
    {"code": "food",           "name": "Еда и продукты",       "icon": "🍔", "color": "#ef4444", "is_expense": True},
    {"code": "restaurants",    "name": "Рестораны и кафе",      "icon": "🍽️", "color": "#f97316", "is_expense": True},
    {"code": "transport",      "name": "Транспорт",             "icon": "🚗", "color": "#3b82f6", "is_expense": True},
    {"code": "housing",        "name": "Жильё и ЖКХ",          "icon": "🏠", "color": "#8b5cf6", "is_expense": True},
    {"code": "shopping",       "name": "Покупки и товары",      "icon": "🛍️", "color": "#ec4899", "is_expense": True},
    {"code": "health",         "name": "Здоровье и медицина",   "icon": "💊", "color": "#06b6d4", "is_expense": True},
    {"code": "entertainment",  "name": "Развлечения",           "icon": "🎬", "color": "#a855f7", "is_expense": True},
    {"code": "education",      "name": "Образование",           "icon": "📚", "color": "#0ea5e9", "is_expense": True},
    {"code": "subscriptions",  "name": "Подписки и сервисы",    "icon": "📱", "color": "#14b8a6", "is_expense": True},
    {"code": "beauty",         "name": "Красота и уход",        "icon": "💅", "color": "#f472b6", "is_expense": True},
    {"code": "sports",         "name": "Спорт и фитнес",        "icon": "🏋️", "color": "#22c55e", "is_expense": True},
    {"code": "telecom",        "name": "Связь и телеком",       "icon": "📞", "color": "#6366f1", "is_expense": True},
    {"code": "insurance",      "name": "Страхование",           "icon": "🛡️", "color": "#64748b", "is_expense": True},
    {"code": "taxes",          "name": "Налоги и штрафы",       "icon": "🏛️", "color": "#dc2626", "is_expense": True},
    {"code": "travel",         "name": "Путешествия",           "icon": "✈️", "color": "#0891b2", "is_expense": True},
    {"code": "pets",           "name": "Домашние животные",     "icon": "🐾", "color": "#a3e635", "is_expense": True},
    {"code": "charity",        "name": "Благотворительность",   "icon": "❤️", "color": "#e11d48", "is_expense": True},
    {"code": "cash",           "name": "Наличные",              "icon": "💵", "color": "#84cc16", "is_income": True, "is_expense": False},
    {"code": "other",          "name": "Другое",                "icon": "📦", "color": "#6b7280", "is_expense": True},
    {"code": "salary",         "name": "Зарплата и доход",      "icon": "💰", "color": "#16a34a", "is_income": True, "is_expense": False},
    {"code": "transfers",      "name": "Переводы",              "icon": "🔄", "color": "#2563eb", "is_income": True, "is_expense": True},
]


def create_default_categories(user_id: int, db: Session):
    for cat_data in DEFAULT_CATEGORIES:
        cat = Category(
            user_id=user_id,
            is_system=True,
            **cat_data,
        )
        db.add(cat)
    db.commit()


# ======== Вспомогательные функции ========
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_verification_token() -> str:
    """Генерация безопасного токена верификации email"""
    return secrets.token_urlsafe(32)


def check_login_attempts(email: str) -> None:
    lockout_until = LOGIN_LOCKOUT_UNTIL.get(email)
    if lockout_until and datetime.now(timezone.utc) < lockout_until:
        remaining = lockout_until - datetime.now(timezone.utc)
        raise HTTPException(
            status_code=429,
            detail=f"Аккаунт временно заблокирован. Попробуйте через {int(remaining.total_seconds() // 60)} минут."
        )
    if lockout_until and datetime.now(timezone.utc) >= lockout_until:
        LOGIN_ATTEMPTS.pop(email, None)
        LOGIN_LOCKOUT_UNTIL.pop(email, None)


def record_failed_login(email: str) -> None:
    attempts = LOGIN_ATTEMPTS.get(email, 0) + 1
    LOGIN_ATTEMPTS[email] = attempts
    if attempts >= MAX_LOGIN_ATTEMPTS:
        LOGIN_LOCKOUT_UNTIL[email] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


def reset_login_attempts(email: str) -> None:
    LOGIN_ATTEMPTS.pop(email, None)
    LOGIN_LOCKOUT_UNTIL.pop(email, None)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id_int = int(user_id)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id_int).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(403, "Аккаунт деактивирован")
    return user


def require_verified_email(current_user: User = Depends(get_current_user)) -> User:
    """Зависимость: требуется подтверждённый email.
    Используется в эндпоинтах, где нужна верификация (напоминания и т.д.)."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Для этого действия необходимо подтвердить email. Проверьте почту или запросите повторную отправку через /auth/resend-verification"
        )
    return current_user

def get_public_base_url(request: Request) -> str:
    """
    Определяет публичный URL приложения для ссылок в письмах.
    Приоритет:
    1. PUBLIC_BASE_URL из настроек (если задан)
    2. X-Forwarded-Host + X-Forwarded-Proto (от nginx/tunnel)
    3. Origin заголовок
    4. request.base_url (fallback)
    """
    settings = get_settings()
    
    # 1. Явно заданный URL (для туннелей)
    if settings.PUBLIC_BASE_URL:
        return settings.PUBLIC_BASE_URL.rstrip("/")
    
    # 2. Заголовки от прокси
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    
    # 3. Origin (откуда пришёл запрос)
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    
    # 4. Fallback
    return str(request.base_url).rstrip("/")

# ======== Эндпоинты ========
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="""
Создаёт нового пользователя в системе.

**После регистрации:**
- На указанный email отправляется письмо для подтверждения
- До подтверждения email некоторые функции недоступны (напоминания)
- Вход в систему возможен сразу после регистрации

**Требования к паролю:**
- Минимум 12 символов
- Хотя бы одна цифра
- Хотя бы одна заглавная буква
- Хотя бы один спецсимвол (!@#$%^&*()-_+=)

**Лимит:** 5 запросов в час на IP-адрес.
    """,
    response_description="Данные созданного пользователя",
    responses={
        201: {
            "description": "Пользователь успешно создан, письмо подтверждения отправлено",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "full_name": "Иван Иванов",
                        "is_active": True,
                        "email_verified": False,
                        "email_notifications": True,
                        "tbank_connected": False
                    }
                }
            }
        },
        400: {
            "description": "Пользователь уже существует или ошибка валидации",
            "content": {
                "application/json": {
                    "examples": {
                        "user_exists": {
                            "summary": "Пользователь существует",
                            "value": {"detail": "Пользователь с таким email уже зарегистрирован"}
                        },
                        "weak_password": {
                            "summary": "Слабый пароль",
                            "value": {"detail": [{"loc": ["body", "password"], "msg": "Пароль должен содержать не менее 12 символов"}]}
                        }
                    }
                }
            }
        },
        429: {
            "description": "Превышен лимит запросов",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 5 per 1 hour"}
                }
            }
        }
    }
)
@limiter.limit("5/hour")
async def register(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    
    Создаёт учётную запись и отправляет письмо для подтверждения email.
    Стандартные категории создаются автоматически.
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже зарегистрирован"
        )

    verification_token = generate_verification_token()

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        is_active=True,
        email_verified=False,
        email_verification_token=verification_token,
        email_verification_sent_at=datetime.now(timezone.utc),
        email_notifications=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        create_default_categories(user.id, db)
        
        # Логируем регистрацию
        audit_log = AuditLog(
            user_id=user.id,
            action="user_registered",
            entity_type="user",
            entity_id=user.id,
            description=f"Зарегистрирован новый пользователь: {user.email}",
            status="success"
        )
        db.add(audit_log)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при создании пользователя")

    # Отправляем письмо подтверждения (асинхронно, не блокируем регистрацию при ошибке)
    try:
        base_url = get_public_base_url(request)
        await email_service.send_verification_email(user.email, verification_token, base_url)
    except Exception as e:
        logger.error(f"Не удалось отправить email верификации: {e}")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified or False,
        email_notifications=user.email_notifications,
        tbank_connected=bool(user.tbank_token_encrypted),
    )


@router.get(
    "/verify-email/{token}",
    response_class=HTMLResponse,
    summary="Подтверждение email по ссылке",
    description="""
Подтверждает email пользователя по токену из письма.

**Токен действителен 24 часа.**

Возвращает HTML-страницу с результатом подтверждения.
    """,
    responses={
        200: {"description": "Email успешно подтверждён (HTML-страница)"},
        400: {"description": "Токен недействителен или истёк (HTML-страница)"},
    }
)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Подтверждение email по токену из письма."""
    user = db.query(User).filter(User.email_verification_token == token).first()

    if not user:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>Ошибка</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f3f4f6; }
                .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; max-width: 420px; }
                .icon { font-size: 48px; margin-bottom: 16px; }
                h1 { color: #dc2626; margin: 0 0 12px; font-size: 22px; }
                p { color: #6b7280; margin: 8px 0; }
            </style></head>
            <body><div class="card">
                <div class="icon">❌</div>
                <h1>Ссылка недействительна</h1>
                <p>Токен подтверждения не найден или уже был использован.</p>
                <p>Запросите новое письмо в приложении.</p>
            </div></body></html>
            """,
            status_code=400
        )

    # Проверяем срок действия
    if user.email_verification_sent_at:
        sent_at = user.email_verification_sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        token_age = datetime.now(timezone.utc) - sent_at
        if token_age > timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS):
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html><head><meta charset="utf-8"><title>Ссылка устарела</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f3f4f6; }
                    .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; max-width: 420px; }
                    .icon { font-size: 48px; margin-bottom: 16px; }
                    h1 { color: #f59e0b; margin: 0 0 12px; font-size: 22px; }
                    p { color: #6b7280; margin: 8px 0; }
                </style></head>
                <body><div class="card">
                    <div class="icon">⏰</div>
                    <h1>Ссылка устарела</h1>
                    <p>Срок действия ссылки истёк (24 часа).</p>
                    <p>Запросите новое письмо в настройках приложения.</p>
                </div></body></html>
                """,
                status_code=400
            )

    # Подтверждаем email
    user.email_verified = True
    user.email_verification_token = None
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Email подтверждён: {user.email}")

    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>Email подтверждён!</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #3b82f6, #6366f1); }
            .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); text-align: center; max-width: 420px; }
            .icon { font-size: 48px; margin-bottom: 16px; }
            h1 { color: #16a34a; margin: 0 0 12px; font-size: 22px; }
            p { color: #6b7280; margin: 8px 0 20px; }
            .button { display: inline-block; background: #3b82f6; color: white; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; }
            .button:hover { background: #2563eb; }
        </style></head>
        <body><div class="card">
            <div class="icon">✅</div>
            <h1>Email подтверждён!</h1>
            <p>Теперь вам доступны все функции FinanceApp, включая напоминания.</p>
            <a href="/" class="button">Перейти в приложение</a>
        </div></body></html>
        """
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Повторная отправка письма подтверждения",
    description="""
Повторно отправляет письмо для подтверждения email.

**Лимит:** 3 запроса в час.

Используйте, если:
- Письмо не пришло
- Ссылка устарела (срок действия 24 часа)
    """,
    response_description="Подтверждение отправки",
    responses={
        200: {
            "description": "Письмо отправлено",
            "content": {
                "application/json": {
                    "example": {"message": "Письмо с подтверждением отправлено на ваш email"}
                }
            }
        },
        400: {
            "description": "Email уже подтверждён",
            "content": {
                "application/json": {
                    "example": {"detail": "Email уже подтверждён"}
                }
            }
        },
        404: {
            "description": "Пользователь не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "Пользователь с таким email не найден"}
                }
            }
        },
        429: {
            "description": "Слишком много запросов",
        }
    }
)
@limiter.limit("3/hour")
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """Повторная отправка письма подтверждения email."""
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь с таким email не найден")

    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email уже подтверждён")

    # Генерируем новый токен
    verification_token = generate_verification_token()
    user.email_verification_token = verification_token
    user.email_verification_sent_at = datetime.now(timezone.utc)
    db.commit()

    # Отправляем письмо
    try:
        base_url = get_public_base_url(request)
        await email_service.send_verification_email(user.email, verification_token, base_url)
    except Exception as e:
        logger.error(f"Не удалось отправить email верификации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка отправки письма. Попробуйте позже.")

    return {"message": "Письмо с подтверждением отправлено на ваш email"}


@router.post(
    "/token",
    response_model=Token,
    summary="Авторизация и получение токена",
    description="""
Аутентификация пользователя по email и паролю.

**Важно:** Вход возможен без подтверждения email, но некоторые функции будут недоступны.

**Формат запроса:** `application/x-www-form-urlencoded`
- `username` — email пользователя
- `password` — пароль

**Защита от брутфорса:**
- После 5 неудачных попыток аккаунт блокируется на 15 минут
- Лимит: 10 запросов в минуту на IP
    """,
    response_description="JWT токен для авторизации",
    responses={
        200: {
            "description": "Успешная авторизация",
            "content": {
                "application/json": {
                    "example": {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
                }
            }
        },
        401: {"description": "Неверные учётные данные"},
        403: {"description": "Аккаунт деактивирован"},
        429: {"description": "Слишком много попыток входа"},
    }
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Аутентификация пользователя и получение JWT-токена."""
    check_login_attempts(form_data.username)

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        record_failed_login(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    reset_login_attempts(form_data.username)

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение текущего пользователя",
    description="Возвращает информацию о текущем авторизованном пользователе, включая статус верификации email.",
    response_description="Данные текущего пользователя",
    responses={
        200: {
            "description": "Успешный ответ",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "full_name": "Иван Иванов",
                        "is_active": True,
                        "email_verified": True,
                        "email_notifications": True,
                        "tbank_connected": False
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        403: {"description": "Аккаунт деактивирован"},
    }
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        email_verified=current_user.email_verified or False,
        email_notifications=current_user.email_notifications,
        tbank_connected=bool(current_user.tbank_token_encrypted),
    )


class ProfileUpdate(BaseModel):
    """Схема для обновления профиля пользователя"""
    full_name: Optional[str] = Field(None, max_length=100, description="Полное имя", examples=["Иван Иванов"])
    email_notifications: Optional[bool] = Field(None, description="Email-уведомления", examples=[True])
    notification_email: Optional[str] = Field(None, description="Email для уведомлений", examples=["notify@example.com"])

    model_config = {
        "json_schema_extra": {
            "examples": [{"full_name": "Иван Петров", "email_notifications": True}]
        }
    }


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Обновление профиля",
    description="Обновляет данные профиля текущего пользователя. Передавайте только те поля, которые нужно изменить.",
    responses={
        200: {"description": "Профиль обновлён"},
        401: {"description": "Не авторизован"},
    }
)
async def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновление профиля пользователя."""
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        email_verified=current_user.email_verified or False,
        email_notifications=current_user.email_notifications,
        tbank_connected=bool(current_user.tbank_token_encrypted),
    )


class PasswordChange(BaseModel):
    """Схема для смены пароля"""
    current_password: str = Field(..., description="Текущий пароль", examples=["OldSecurePass123!"])
    new_password: str = Field(..., min_length=12, description="Новый пароль", examples=["NewSecurePass456!"])

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Пароль должен содержать не менее 12 символов")
        if not any(char.isdigit() for char in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(char.isupper() for char in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(char in "!@#$%^&*()-_+=" for char in v):
            raise ValueError("Пароль должен содержать спецсимволы (!@#$%^*...)")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{"current_password": "OldSecurePass123!", "new_password": "NewSecurePass456!"}]
        }
    }


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Смена пароля",
    description="""
Изменяет пароль текущего пользователя.

**Требуется авторизация.**

**Требования к новому паролю:**
- Минимум 12 символов, цифра, заглавная буква, спецсимвол
    """,
    responses={
        200: {"description": "Пароль изменён", "content": {"application/json": {"example": {"message": "Пароль успешно изменён"}}}},
        400: {"description": "Неверный текущий пароль"},
        401: {"description": "Не авторизован"},
    }
)
async def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Смена пароля пользователя."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Пароль успешно изменён"}