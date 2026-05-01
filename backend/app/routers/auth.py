"""
Роутер аутентификации
"""
from app.config import get_settings
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Настройки
_settings = get_settings()
SECRET_KEY = _settings.SECRET_KEY          
ALGORITHM = _settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# ===== Pydantic схемы =====
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Пароль должен быть не менее 12 символов")
        if not any(char.isdigit() for char in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(char.isupper() for char in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(char in "!@#$%^&*()-_+=" for char in v):
            raise ValueError("Пароль должен содержать спецсимвол (!@#$%^&*...)")
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
    {"code": "food",      "name": "Еда",       "icon": "🍕", "color": "#ef4444", "is_expense": True},
    {"code": "transport", "name": "Транспорт", "icon": "🚗", "color": "#f97316", "is_expense": True},
    {"code": "housing",   "name": "Жильё",     "icon": "🏠", "color": "#8b5cf6", "is_expense": True},
    {"code": "health",    "name": "Здоровье",  "icon": "💊", "color": "#06b6d4", "is_expense": True},
    {"code": "salary",    "name": "Зарплата",  "icon": "💰", "color": "#22c55e", "is_income": True},
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


# ===== Вспомогательные функции =====
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный токен",
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
    
    return user


# ===== Эндпоинты =====
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Регистрация невозможна. "
                   "Если у вас уже есть аккаунт, войдите."
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
        raise HTTPException(
            status_code=409,
            detail="Пользователь с таким email уже существует"
    )
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "email_notifications": user.email_notifications,
        "tbank_connected": bool(user.tbank_token_encrypted),
    }


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Вход в систему"""
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Аккаунт деактивирован")
    
    # Обновляем last_login
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
async def login_for_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 endpoint для получения токена"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить текущего пользователя"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "email_notifications": current_user.email_notifications,
        "tbank_connected": bool(current_user.tbank_token_encrypted),
    }


@router.put("/me", response_model=UserResponse)
async def update_me(
    full_name: Optional[str] = None,
    email_notifications: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить профиль"""
    if full_name is not None:
        current_user.full_name = full_name
    if email_notifications is not None:
        current_user.email_notifications = email_notifications
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "email_notifications": current_user.email_notifications,
        "tbank_connected": bool(current_user.tbank_token_encrypted),
    }
