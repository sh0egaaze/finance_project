from fastapi import APIRouter, Depends, HTTPException, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, condecimal, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.database import get_db
from app.models import Transaction, Category, User
from app.routers.auth import get_current_user
from app.ml.model_loader import registry
import logging
from app.ml.model_loader import registry
from app.ml.categorizer import categorize

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

limiter = Limiter(key_func=get_remote_address)

@router.post("/smart-input")
@limiter.limit("30/minute")
async def smart_input(
    data: SmartInputRequest,
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    # Получаем ML-модели через .get() с проверкой
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")
    
    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")
    
    # 1. Парсинг текста
    parsed = registry.get("nlp_parser").parse(data.text)   
     
    # 2. Категоризация (если модель загружена)
    category_id = None
    if categorizer and parsed.get("description"):
        cat_pred = categorize(parsed["description"])
        db_cat = db.query(Category).filter(
            Category.code == cat_pred.category_code,
            Category.user_id == user.id
        ).first()
        category_id = db_cat.id if db_cat else None
        if not category_id:
            logger.warning(f"Category code {cat_pred.category_code} not found in DB")
    
    return {
        "amount": parsed["amount"],
        "description": parsed["description"],
        "category_id": category_id,
        "is_income": parsed["is_income"]
    }

class TransactionCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500, description="Описание транзакции")
    amount: Decimal = Field(..., gt=0, description="Сумма > 0. Знак определяется полем is_income")
    is_income: bool = Field(..., description="True = доход, False = расход")
    category_id: Optional[int] = Field(None, description="ID категории")
    transaction_date: Optional[str] = None

class TransactionUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    amount: Optional[Decimal] = Field(None, gt=0)
    category_id: Optional[int] = None
    category_manual: Optional[bool] = None

class TransactionResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    is_income: bool
    category_id: Optional[int]
    transaction_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

def get_own_transaction(
    tx_id: int,
    db: Session,
    user: User,
) -> Transaction:
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == user.id,   
    ).first()
    if not tx:
        raise HTTPException(
            status_code=404,
            detail="Транзакция не найдена или у вас нет доступа",
        )
    return tx

class SmartInputRequest(BaseModel):
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Текст для парсинга транзакции"
    )
    
    class Config:
        from_attributes = True

@router.put("/{tx_id}")
async def update_transaction(
    tx_id: int,
    data: TransactionUpdate,   
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Некорректные данные: категория не существует или нарушение ограничений БД"
        )
    return {"status": "updated"}

@router.get("/{tx_id}")
async def get_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return get_own_transaction(tx_id, db, user)

@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    tx = get_own_transaction(tx_id, db, user)
    try:
        db.delete(tx)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении транзакции"
        )

@router.get("", response_model=list[TransactionResponse])
async def get_transactions(
    limit: int = Query(default=50, ge=1, le=200, description="Кол-во записей на страницу"),
    offset: int = Query(default=0, ge=0, description="Смещение"),
    category_id: Optional[int] = Query(None),
    is_income: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == user.id)

    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if is_income is not None:
        query = query.filter(Transaction.amount > 0 if is_income else Transaction.amount < 0)

    total = query.count()
    transactions = query.order_by(Transaction.transaction_date.desc()) \
                        .offset(offset).limit(limit).all()

    return {
        "items": transactions,
        "total": total,
        "limit": limit,
        "offset": offset,
    }