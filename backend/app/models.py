"""
Модели базы данных
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Date,
    ForeignKey, Index, Numeric, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base


# ==================== ENUMS ====================
class TransactionSource(str, enum.Enum):
    tbank_api = 'tbank_api'
    manual = 'manual'


class ReminderFrequency(str, enum.Enum):
    once = 'once'
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'
    custom = 'custom'


# ==================== ТАБЛИЦА USERS ====================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255))
    email_verification_sent_at = Column(TIMESTAMP(timezone=True))
    
    tbank_token_encrypted = Column(String(500))
    tbank_token_salt = Column(String(32))
    email_notifications = Column(Boolean, default=True)
    notification_email = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True))
    last_login = Column(TIMESTAMP(timezone=True))

    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index('ix_users_email', 'email', unique=True),
        Index('ix_users_id', 'id'),
        Index('ix_users_verification_token', 'email_verification_token'),
    )


# ==================== ТАБЛИЦА CATEGORIES ====================
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100))
    icon = Column(String(50))
    color = Column(String(7))
    is_income = Column(Boolean, default=False)
    is_expense = Column(Boolean, default=True)
    keywords = Column(String(1000))
    mcc_codes = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    transactions = relationship("Transaction", back_populates="category")
    predictions = relationship("Prediction", back_populates="category")

    __table_args__ = (
        Index('ix_categories_user_code', 'user_id', 'code', unique=True),
        Index('ix_categories_id', 'id'),
    )


# ==================== ТАБЛИЦА CURRENCY_RATES ====================
class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id = Column(Integer, primary_key=True)
    base_currency = Column(String(3), nullable=False)
    target_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(18, 6), nullable=False)
    rate_date = Column(TIMESTAMP(timezone=True), nullable=False)
    source = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_currency_rates_id', 'id'),
        Index('ix_currency_rates_base_currency', 'base_currency'),
        Index('ix_currency_rates_target_currency', 'target_currency'),
        Index('ix_currency_rates_rate_date', 'rate_date'),
        Index('ix_currency_rates_currencies_date', 'base_currency', 'target_currency', 'rate_date'),
    )


# ==================== ТАБЛИЦА TRANSACTIONS ====================
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), default='RUB')
    description = Column(String(500))
    category_confidence = Column(Numeric(5, 4))
    category_manual = Column(Boolean, default=False)
    source = Column(SQLEnum(TransactionSource, name='transaction_source', create_type=True), default=TransactionSource.manual)
    external_id = Column(String(255))
    merchant_name = Column(String(255))
    merchant_category_code = Column(String(10))
    is_suspicious = Column(Boolean, default=False)
    suspicious_reason = Column(String(255))
    suspicious_dismissed = Column(Boolean, default=False)
    transaction_date = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    @property
    def is_income(self) -> bool:
        return self.amount is not None and self.amount >= 0

    __table_args__ = (
        Index('ix_transactions_id', 'id'),
        Index('ix_transactions_user_id', 'user_id'),
        Index('ix_transactions_category_id', 'category_id'),
        Index('ix_transactions_external_id', 'external_id'),
        Index('ix_transactions_transaction_date', 'transaction_date'),
        Index('ix_transactions_user_date', 'user_id', 'transaction_date'),
    )


# ==================== ТАБЛИЦА REMINDERS ====================
class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    amount = Column(Numeric(18, 2))
    currency = Column(String(3), default='RUB')
    frequency = Column(SQLEnum(ReminderFrequency, name='reminder_frequency', create_type=True), default=ReminderFrequency.once)
    interval_days = Column(Integer)
    repeat_count = Column(Integer)
    current_count = Column(Integer, default=0)
    next_reminder_date = Column(TIMESTAMP(timezone=True), nullable=False)
    last_sent_date = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    send_email = Column(Boolean, default=True)
    send_push = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    user = relationship("User", back_populates="reminders")
    notification_history = relationship("NotificationHistory", back_populates="reminder", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_reminders_id', 'id'),
        Index('ix_reminders_user_id', 'user_id'),
        Index('ix_reminders_next_date', 'next_reminder_date'),
        Index('ix_reminders_active', 'is_active', 'next_reminder_date'),
    )


# ==================== ТАБЛИЦА NOTIFICATION_HISTORY ====================
class NotificationHistory(Base):
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(String(20), nullable=False)
    error_message = Column(String(500))

    # Relationships
    reminder = relationship("Reminder", back_populates="notification_history")

    __table_args__ = (
        Index('ix_notification_history_reminder_id', 'reminder_id'),
        Index('ix_notification_history_sent_at', 'sent_at'),
    )


# ==================== ТАБЛИЦА PREDICTIONS ====================
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    prediction_month = Column(Date, nullable=False)
    predicted_amount = Column(Numeric(18, 2), nullable=False)
    confidence = Column(Numeric(5, 4))
    actual_amount = Column(Numeric(18, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="predictions")
    category = relationship("Category", back_populates="predictions")

    __table_args__ = (
        Index('ix_predictions_user_id', 'user_id'),
        Index('ix_predictions_month', 'prediction_month'),
        Index('ix_predictions_user_month', 'user_id', 'prediction_month'),
    )


# ==================== ТАБЛИЦА AUDIT_LOGS ====================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    description = Column(String(500))
    status = Column(String(20))
    error_message = Column(String(500))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index('ix_audit_logs_user_id', 'user_id'),
        Index('ix_audit_logs_created_at', 'created_at'),
        Index('ix_audit_logs_action', 'action'),
    )