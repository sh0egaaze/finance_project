"""Аутентификационные endpoints"""
from app.config import get_settings
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import User, Category

router = APIRouter(prefix="/auth", tags=["Авторизация"])

limiter = Limiter(key_func=get_remote_address)

# Настройки
_settings = get_settings()
SECRET_KEY = _settings.SECRET_KEY
ALGORITHM = _settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.ACCESS_TOKEN_EXPIRE_MINUTES

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
    email_notifications: bool = Field(..., description="Включены ли email-уведомления", examples=[True])
    tbank_connected: bool = Field(False, description="Подключён ли Т-Банк", examples=[False])

    class Config:
        from_attributes = True


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
    email: EmailStr = Field(
        ...,
        description="Email пользователя",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        description="Пароль пользователя",
        examples=["SecurePass123!"]
    )


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


def check_login_attempts(email: str) -> None:
    """Проверка лимита неудачных попыток входа.
    Выбрасывает HTTPException 429 если аккаунт временно заблокирован."""
    lockout_until = LOGIN_LOCKOUT_UNTIL.get(email)
    if lockout_until and datetime.now(timezone.utc) < lockout_until:
        remaining = lockout_until - datetime.now(timezone.utc)
        raise HTTPException(
            status_code=429,
            detail=f"Аккаунт временно заблокирован. Попробуйте через {int(remaining.total_seconds() // 60)} минут."
        )
    if lockout_until and datetime.now(timezone.utc) >= lockout_until:
        # Блокировка истекла — сбрасываем счётчик
        LOGIN_ATTEMPTS.pop(email, None)
        LOGIN_LOCKOUT_UNTIL.pop(email, None)


def record_failed_login(email: str) -> None:
    """Фиксация неудачной попытки входа.
    После MAX_LOGIN_ATTEMPTS неудачных попыток — блокировка на LOCKOUT_DURATION_MINUTES."""
    attempts = LOGIN_ATTEMPTS.get(email, 0) + 1
    LOGIN_ATTEMPTS[email] = attempts
    if attempts >= MAX_LOGIN_ATTEMPTS:
        LOGIN_LOCKOUT_UNTIL[email] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


def reset_login_attempts(email: str) -> None:
    """Сброс счётчика неудачных попыток после успешного входа."""
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


# ======== Эндпоинты ========
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="""
Создаёт нового пользователя в системе.

**Требования к паролю:**
- Минимум 12 символов
- Хотя бы одна цифра
- Хотя бы одна заглавная буква
- Хотя бы один спецсимвол (!@#$%^&*()-_+=)

**Лимит:** 5 запросов в час на IP-адрес.

При успешной регистрации автоматически создаются стандартные категории расходов/доходов.
    """,
    response_description="Данные созданного пользователя",
    responses={
        201: {
            "description": "Пользователь успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "full_name": "Иван Иванов",
                        "is_active": True,
                        "email_notifications": True,
                        "tbank_connected": False
                    }
                }
            }
        },
        400: {
            "description": "Ошибка валидации или пользователь уже существует",
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
    
    Создаёт учётную запись с указанным email и паролем.
    После регистрации пользователю автоматически создаются
    стандартные категории для учёта расходов и доходов.
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже зарегистрирован"
        )

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        is_active=True,
        email_notifications=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        create_default_categories(user.id, db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при создании пользователя")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        email_notifications=user.email_notifications,
        tbank_connected=bool(user.tbank_token_encrypted),
    )


@router.post(
    "/token",
    response_model=Token,
    summary="Авторизация и получение токена",
    description="""
Аутентификация пользователя по email и паролю.

**Формат запроса:** `application/x-www-form-urlencoded`
- `username` — email пользователя
- `password` — пароль

**Защита от брутфорса:**
- После 5 неудачных попыток аккаунт блокируется на 15 минут
- Лимит: 10 запросов в минуту на IP

**Использование токена:**
Authorization: Bearer <access_token>
    """,
    response_description="JWT токен для авторизации",
    responses={
        200: {
            "description": "Успешная авторизация",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {
            "description": "Неверные учётные данные",
            "content": {
                "application/json": {
                    "example": {"detail": "Неверный email или пароль"}
                }
            }
        },
        403: {
            "description": "Аккаунт деактивирован",
            "content": {
                "application/json": {
                    "example": {"detail": "Аккаунт деактивирован"}
                }
            }
        },
        429: {
            "description": "Слишком много попыток входа",
            "content": {
                "application/json": {
                    "example": {"detail": "Аккаунт временно заблокирован. Попробуйте через 15 минут."}
                }
            }
        }
    }
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Аутентификация пользователя и получение JWT-токена.
    
    Принимает email (в поле username) и пароль.
    Возвращает access_token для использования в защищённых эндпоинтах.
    """
    # Проверка лимита неудачных попыток
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

    # Успешный вход — сбрасываем счётчик
    reset_login_attempts(form_data.username)

    # Обновляем last_login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение текущего пользователя",
    description="""
Возвращает информацию о текущем авторизованном пользователе.

**Требуется авторизация** — передайте JWT токен в заголовке:
Authorization: Bearer <token>
    """,
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
                        "email_notifications": True,
                        "tbank_connected": False
                    }
                }
            }
        },
        401: {
            "description": "Не авторизован или токен недействителен",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        },
        403: {
            "description": "Аккаунт деактивирован",
            "content": {
                "application/json": {
                    "example": {"detail": "Аккаунт деактивирован"}
                }
            }
        }
    }
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    
    Возвращает профиль авторизованного пользователя,
    включая статус подключения к Т-Банку.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        email_notifications=current_user.email_notifications,
        tbank_connected=bool(current_user.tbank_token_encrypted),
    )


class ProfileUpdate(BaseModel):
    """Схема для обновления профиля пользователя"""
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Полное имя пользователя",
        examples=["Иван Иванов"]
    )
    email_notifications: Optional[bool] = Field(
        None,
        description="Включить/выключить email-уведомления",
        examples=[True]
    )
    notification_email: Optional[str] = Field(
        None,
        description="Email для уведомлений (если отличается от основного)",
        examples=["notifications@example.com"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "full_name": "Иван Петров",
                    "email_notifications": True
                }
            ]
        }
    }


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Обновление профиля",
    description="""
Обновляет данные профиля текущего пользователя.

**Требуется авторизация.**

Можно обновить:
- `full_name` — полное имя
- `email_notifications` — настройка email-уведомлений
- `notification_email` — альтернативный email для уведомлений

Передавайте только те поля, которые нужно изменить.
    """,
    response_description="Обновлённые данные пользователя",
    responses={
        200: {
            "description": "Профиль успешно обновлён",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "full_name": "Иван Петров",
                        "is_active": True,
                        "email_notifications": True,
                        "tbank_connected": False
                    }
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        },
        422: {
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {"detail": [{"loc": ["body", "full_name"], "msg": "String should have at most 100 characters"}]}
                }
            }
        }
    }
)
async def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновление профиля пользователя.
    
    Позволяет изменить имя и настройки уведомлений.
    Обновляются только переданные поля.
    """
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
        email_notifications=current_user.email_notifications,
        tbank_connected=bool(current_user.tbank_token_encrypted),
    )


class PasswordChange(BaseModel):
    """Схема для смены пароля"""
    current_password: str = Field(
        ...,
        description="Текущий пароль пользователя",
        examples=["OldSecurePass123!"]
    )
    new_password: str = Field(
        ...,
        min_length=12,
        description="Новый пароль (мин. 12 символов, цифра, заглавная буква, спецсимвол)",
        examples=["NewSecurePass456!"]
    )

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
            "examples": [
                {
                    "current_password": "OldSecurePass123!",
                    "new_password": "NewSecurePass456!"
                }
            ]
        }
    }


@router.post(
    "/change-password",
    summary="Смена пароля",
    description="""
Изменяет пароль текущего пользователя.

**Требуется авторизация.**

**Требования к новому паролю:**
- Минимум 12 символов
- Хотя бы одна цифра
- Хотя бы одна заглавная буква
- Хотя бы один спецсимвол (!@#$%^&*()-_+=)

Для смены пароля необходимо указать текущий пароль.
    """,
    response_description="Подтверждение смены пароля",
    responses={
        200: {
            "description": "Пароль успешно изменён",
            "content": {
                "application/json": {
                    "example": {"message": "Пароль успешно изменён"}
                }
            }
        },
        400: {
            "description": "Неверный текущий пароль или слабый новый пароль",
            "content": {
                "application/json": {
                    "examples": {
                        "wrong_password": {
                            "summary": "Неверный текущий пароль",
                            "value": {"detail": "Неверный текущий пароль"}
                        },
                        "weak_password": {
                            "summary": "Слабый новый пароль",
                            "value": {"detail": [{"loc": ["body", "new_password"], "msg": "Пароль должен содержать не менее 12 символов"}]}
                        }
                    }
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        }
    }
)
async def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Смена пароля пользователя.
    
    Проверяет текущий пароль и устанавливает новый.
    Новый пароль должен соответствовать требованиям безопасности.
    """
    # Проверяем текущий пароль
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Устанавливаем новый пароль
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Пароль успешно изменён"}