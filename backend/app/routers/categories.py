"""
Роутер для категорий
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from app.database import get_db
from app.models import Category, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


# ===== Pydantic схемы =====
class CategoryResponse(BaseModel):
    id: int
    code: str
    name: str
    name_en: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_income: bool
    is_expense: bool
    is_active: bool

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    code: str
    name: str
    name_en: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_income: bool = False
    is_expense: bool = True
    keywords: Optional[str] = None


# ===== Эндпоинты =====
@router.get("", response_model=List[CategoryResponse])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить категории пользователя"""
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


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Получить категорию по ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.post("", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  
):
    """Создать новую категорию"""
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