"""Аутентификационные endpoints"""
from app.config import get_settings
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import User, Category

router = APIRouter(prefix="/auth", tags=["auth"])

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
    email: EmailStr
    password: str
    full_name: Optional[str] = None

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


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    email_notifications: bool
    tbank_connected: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

DEFAULT_CATEGORIES = [
    {"code": "food",      "name": "Еда",         "icon": "🍔", "color": "#ef4444", "is_expense": True},
    {"code": "transport",  "name": "Транспорт",     "icon": "🚗", "color": "#f97316", "is_expense": True},
    {"code": "housing",    "name": "Жильё",        "icon": "🏠", "color": "#8b5cf6", "is_expense": True},
    {"code": "health",     "name": "Здоровье",      "icon": "💊", "color": "#06b6d4", "is_expense": True},
    {"code": "salary",     "name": "Зарплата",      "icon": "💰", "color": "#22c55e", "is_income": True},
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
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Если этот email свободен, регистрация выполнена"
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


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Аутентификация пользователя и получение JWT-токена"""
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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        email_notifications=current_user.email_notifications,
        tbank_connected=bool(current_user.tbank_token_encrypted),
    )