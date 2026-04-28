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
async def get_categories(db: Session = Depends(get_db)):
    """Получить все категории"""
    # Создаём дефолтные категории если их нет
    existing = db.query(Category).count()
    if existing == 0:
        default_categories = [
            {"code": "food", "name": "Еда", "name_en": "Food", "icon": "🍔", "color": "#FF6B6B", "is_expense": True, "keywords": "еда,продукты,кафе,ресторан,кофе,обед,завтрак,ужин,магазин"},
            {"code": "transport", "name": "Транспорт", "name_en": "Transport", "icon": "🚗", "color": "#4ECDC4", "is_expense": True, "keywords": "такси,метро,автобус,бензин,транспорт"},
            {"code": "entertainment", "name": "Развлечения", "name_en": "Entertainment", "icon": "🎬", "color": "#45B7D1", "is_expense": True, "keywords": "кино,театр,концерт,развлечения"},
            {"code": "shopping", "name": "Покупки", "name_en": "Shopping", "icon": "🛍️", "color": "#96CEB4", "is_expense": True, "keywords": "покупки,одежда,магазин"},
            {"code": "utilities", "name": "ЖКХ", "name_en": "Utilities", "icon": "🏠", "color": "#FFEAA7", "is_expense": True, "keywords": "жкх,коммуналка,квартира"},
            {"code": "health", "name": "Здоровье", "name_en": "Health", "icon": "💊", "color": "#DDA0DD", "is_expense": True, "keywords": "аптека,врач,больница,здоровье"},
            {"code": "education", "name": "Образование", "name_en": "Education", "icon": "📚", "color": "#87CEEB", "is_expense": True, "keywords": "образование,курсы,книги"},
            {"code": "subscriptions", "name": "Подписки", "name_en": "Subscriptions", "icon": "📱", "color": "#98D8C8", "is_expense": True, "keywords": "подписка,netflix,spotify"},
            {"code": "salary", "name": "Зарплата", "name_en": "Salary", "icon": "💰", "color": "#2ECC71", "is_income": True, "keywords": "зарплата,аванс,премия"},
            {"code": "other_income", "name": "Другой доход", "name_en": "Other Income", "icon": "💵", "color": "#27AE60", "is_income": True, "keywords": "доход,перевод"},
            {"code": "other", "name": "Другое", "name_en": "Other", "icon": "📦", "color": "#95A5A6", "is_expense": True, "keywords": ""},
        ]
        for cat_data in default_categories:
            cat = Category(**cat_data, is_system=True, is_active=True)
            db.add(cat)
        db.commit()
    
    categories = db.query(Category).filter(Category.is_active == True).all()
    return categories


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