"""
Роутер для категорий
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Category, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/categories", tags=["Категории"])


# ===== Pydantic схемы =====
class CategoryResponse(BaseModel):
    """Схема ответа с данными категории"""
    id: int = Field(..., description="Уникальный идентификатор категории", examples=[1])
    code: str = Field(..., description="Уникальный код категории", examples=["food"])
    name: str = Field(..., description="Название категории на русском", examples=["Еда и продукты"])
    name_en: Optional[str] = Field(None, description="Название категории на английском", examples=["Food & Groceries"])
    icon: Optional[str] = Field(None, description="Эмодзи-иконка категории", examples=["🍔"])
    color: Optional[str] = Field(None, description="HEX-цвет категории", examples=["#ef4444"])
    is_income: bool = Field(..., description="Категория для доходов", examples=[False])
    is_expense: bool = Field(..., description="Категория для расходов", examples=[True])
    is_active: bool = Field(..., description="Активна ли категория", examples=[True])

    class Config:
        from_attributes = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "code": "food",
                    "name": "Еда и продукты",
                    "name_en": "Food & Groceries",
                    "icon": "🍔",
                    "color": "#ef4444",
                    "is_income": False,
                    "is_expense": True,
                    "is_active": True
                }
            ]
        }
    }


class CategoryCreate(BaseModel):
    """Схема для создания новой категории"""
    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Уникальный код категории (латиница, snake_case)",
        examples=["custom_category"]
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название категории на русском",
        examples=["Моя категория"]
    )
    name_en: Optional[str] = Field(
        None,
        max_length=100,
        description="Название категории на английском",
        examples=["My Category"]
    )
    icon: Optional[str] = Field(
        None,
        max_length=10,
        description="Эмодзи-иконка категории",
        examples=["📦"]
    )
    color: Optional[str] = Field(
        None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="HEX-цвет категории (формат #RRGGBB)",
        examples=["#3b82f6"]
    )
    is_income: bool = Field(
        False,
        description="Использовать для доходов",
        examples=[False]
    )
    is_expense: bool = Field(
        True,
        description="Использовать для расходов",
        examples=[True]
    )
    keywords: Optional[str] = Field(
        None,
        max_length=500,
        description="Ключевые слова для автокатегоризации (через запятую)",
        examples=["магазин, супермаркет, продукты"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "custom_category",
                    "name": "Моя категория",
                    "name_en": "My Category",
                    "icon": "📦",
                    "color": "#3b82f6",
                    "is_income": False,
                    "is_expense": True,
                    "keywords": "ключ1, ключ2"
                }
            ]
        }
    }


# ===== Эндпоинты =====
@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="Получить список категорий",
    description="""
Возвращает все активные категории, доступные пользователю.

**Требуется авторизация.**

Включает:
- **Системные категории** — созданные по умолчанию при регистрации
- **Пользовательские категории** — созданные самим пользователем

При наличии дубликатов по коду приоритет отдаётся пользовательским категориям.
    """,
    response_description="Список категорий пользователя",
    responses={
        200: {
            "description": "Успешный ответ со списком категорий",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "code": "food",
                            "name": "Еда и продукты",
                            "name_en": None,
                            "icon": "🍔",
                            "color": "#ef4444",
                            "is_income": False,
                            "is_expense": True,
                            "is_active": True
                        },
                        {
                            "id": 2,
                            "code": "salary",
                            "name": "Зарплата и доход",
                            "name_en": None,
                            "icon": "💰",
                            "color": "#16a34a",
                            "is_income": True,
                            "is_expense": False,
                            "is_active": True
                        }
                    ]
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
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить категории пользователя.
    
    Возвращает объединённый список системных и пользовательских категорий.
    При дубликатах по коду приоритет имеют пользовательские категории.
    """
    # Получаем категории пользователя
    categories = db.query(Category).filter(
        Category.is_active == True,
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()
    
    # Убираем дубликаты по коду (приоритет у пользовательских)
    seen_codes = {}
    for cat in categories:
        if cat.code not in seen_codes:
            seen_codes[cat.code] = cat
        elif cat.user_id == current_user.id:
            # Пользовательская категория имеет приоритет
            seen_codes[cat.code] = cat
    
    return list(seen_codes.values())


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Получить категорию по ID",
    description="""
Возвращает информацию о конкретной категории по её идентификатору.

Можно получить как системную, так и пользовательскую категорию.
    """,
    response_description="Данные категории",
    responses={
        200: {
            "description": "Категория найдена",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "code": "food",
                        "name": "Еда и продукты",
                        "name_en": None,
                        "icon": "🍔",
                        "color": "#ef4444",
                        "is_income": False,
                        "is_expense": True,
                        "is_active": True
                    }
                }
            }
        },
        404: {
            "description": "Категория не найдена",
            "content": {
                "application/json": {
                    "example": {"detail": "Категория не найдена"}
                }
            }
        }
    }
)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить категорию по ID.
    
    Возвращает полную информацию о категории включая иконку, цвет и тип.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую категорию",
    description="""
Создаёт новую пользовательскую категорию.

**Требуется авторизация.**

**Обязательные поля:**
- `code` — уникальный код (латиница, snake_case)
- `name` — название на русском

**Опциональные поля:**
- `icon` — эмодзи для отображения
- `color` — HEX-цвет (#RRGGBB)
- `is_income` / `is_expense` — тип категории
- `keywords` — ключевые слова для автокатегоризации

Созданная категория будет доступна только текущему пользователю.
    """,
    response_description="Созданная категория",
    responses={
        201: {
            "description": "Категория успешно создана",
            "content": {
                "application/json": {
                    "example": {
                        "id": 25,
                        "code": "custom_category",
                        "name": "Моя категория",
                        "name_en": None,
                        "icon": "📦",
                        "color": "#3b82f6",
                        "is_income": False,
                        "is_expense": True,
                        "is_active": True
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
        409: {
            "description": "Категория с таким кодом уже существует",
            "content": {
                "application/json": {
                    "example": {"detail": "Категория с таким кодом уже существует"}
                }
            }
        },
        422: {
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "code"],
                                "msg": "String should have at least 2 characters",
                                "type": "string_too_short"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Внутренняя ошибка сервера",
            "content": {
                "application/json": {
                    "example": {"detail": "Внутренняя ошибка сервера"}
                }
            }
        }
    }
)
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  
):
    """
    Создать новую категорию.
    
    Создаёт пользовательскую категорию с указанными параметрами.
    Код категории должен быть уникальным в рамках системы.
    """
    existing = db.query(Category).filter(Category.code == data.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Категория с таким кодом уже существует")
    
    category = Category(
        code=data.code,
        name=data.name,
        name_en=data.name_en,
        icon=data.icon,
        color=data.color,
        is_income=data.is_income,
        is_expense=data.is_expense,
        keywords=data.keywords,
        is_active=True,
        is_system=False,
    )
    db.add(category)

    try:
        db.commit()
        db.refresh(category)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Ошибка целостности данных: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    return category