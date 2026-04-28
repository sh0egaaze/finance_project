from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from app.database import get_db
from app.models import Transaction, Category, User
from app.routers.auth import get_current_user
from app.ml.model_loader import registry

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/smart-input")
async def smart_input(data: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 1. Парсим текст (Нейросеть #2)
    parsed = registry.nlp_parser.parse(data.get("text", ""))
    # 2. Определяем категорию (Нейросеть #1)
    cat_pred = registry.categorizer.predict(parsed["description"])
    
    db_cat = db.query(Category).filter(Category.code == cat_pred["category_code"]).first()
    
    return {
        "amount": parsed["amount"],
        "description": parsed["description"],
        "category_id": db_cat.id if db_cat else None,
        "is_income": parsed["is_income"]
    }

class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    category_manual: Optional[bool] = None

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

    db.commit()
    return {"status": "updated"}