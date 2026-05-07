from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, condecimal, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import Transaction, Category, User
from app.routers.auth import get_current_user
from app.ml.model_loader import registry
import logging
from app.ml.categorizer import categorize

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

limiter = Limiter(key_func=get_remote_address)

class TransactionCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500, description="Описание транзакции")
    amount: Decimal = Field(..., gt=0, description="Сумма > 0. Если указан флаг is_income")
    is_income: bool = Field(..., description="True = доход, False = расход")
    category_id: Optional[int] = Field(None, description="ID категории")
    transaction_date: Optional[str] = None

class TransactionUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    amount: Optional[Decimal] = Field(None, gt=0)
    is_income: Optional[bool] = None
    category_id: Optional[int] = None
    category_manual: Optional[bool] = None
    transaction_date: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    is_income: bool
    category_id: Optional[int]
    transaction_date: Optional[datetime]
    created_at: datetime
    source: Optional[str] = None
    
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
            detail="Транзакция не найдена или не принадлежит вам",
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
    
    new_amount = update_data.pop('amount', None)
    new_is_income = update_data.pop('is_income', None)
    
    if new_amount is not None:
        if new_is_income is not None:
            tx.amount = new_amount if new_is_income else -new_amount
        else:
            tx.amount = new_amount if tx.amount >= 0 else -new_amount
    elif new_is_income is not None and tx.amount is not None:
        tx.amount = abs(tx.amount) if new_is_income else -abs(tx.amount)
    
    new_date = update_data.pop('transaction_date', None)
    if new_date:
        try:
            from datetime import datetime
            tx.transaction_date = datetime.fromisoformat(new_date)
        except ValueError:
            pass
    
    for field, value in update_data.items():
        setattr(tx, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Недопустимые данные"
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
    limit: int = Query(20, ge=1, le=100, description="Макс. кол-во записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение списка транзакций с пагинацией"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(
        Transaction.transaction_date.desc()
    ).offset(offset).limit(limit).all()
    
    return transactions


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создание новой транзакции"""
    tx_date = datetime.now(timezone.utc)
    if data.transaction_date:
        try:
            tx_date = datetime.fromisoformat(data.transaction_date)
        except ValueError:
            pass
    
    tx = Transaction(
        user_id=user.id,
        description=data.description,
        amount=data.amount if data.is_income else -data.amount,
        category_id=data.category_id,
        transaction_date=tx_date,
    )
    
    try:
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ошибка при создании: категория не принадлежит вам"
        )
    return tx

@router.post("/smart-input")
@limiter.limit("30/minute")
async def smart_input(
    request: Request,
    data: SmartInputRequest,
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    # Подключаем ML-модуль через .get() с проверкой на None
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")
    
    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")
    
    # 1. Парсинг текста
    parsed = nlp_parser.parse(data.text)   
    
    # 2. Категоризация (умная модель загружена)
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

@router.post("/smart-input/confirm", response_model=TransactionResponse, status_code=201)
@limiter.limit("30/minute")
async def smart_input_confirm(
    request: Request,
    data: SmartInputRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Подтверждение быстрого ввода — парсит текст и создаёт транзакцию"""
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")

    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")

    # 1. Парсинг текста
    parsed = nlp_parser.parse(data.text)

    amount = parsed.get("amount")
    description = parsed.get("description", data.text)
    is_income = parsed.get("is_income", False)

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Не удалось определить сумму из текста")

    # 2. Категоризация
    category_id = None
    if categorizer and description:
        cat_pred = categorize(description)
        db_cat = db.query(Category).filter(
            Category.code == cat_pred.category_code,
        ).first()
        category_id = db_cat.id if db_cat else None

    # 3. Создание транзакции
    tx = Transaction(
        user_id=user.id,
        description=description,
        amount=amount if is_income else -amount,
        category_id=category_id,
        transaction_date=datetime.now(timezone.utc),
    )

    try:
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при создании транзакции")

    return tx