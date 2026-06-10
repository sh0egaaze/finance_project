"""Initial - create all tables

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM types
    transaction_source = postgresql.ENUM('tbank_api', 'manual', name='transaction_source', create_type=False)
    reminder_frequency = postgresql.ENUM('once', 'daily', 'weekly', 'monthly', 'custom', name='reminder_frequency', create_type=False)
    
    op.execute("CREATE TYPE transaction_source AS ENUM ('tbank_api', 'manual')")
    op.execute("CREATE TYPE reminder_frequency AS ENUM ('once', 'daily', 'weekly', 'monthly', 'custom')")

    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('email_verification_token', sa.String(255)),
        sa.Column('email_verification_sent_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('tbank_token_encrypted', sa.String(500)),
        sa.Column('tbank_token_salt', sa.String(32)),
        sa.Column('email_notifications', sa.Boolean(), default=True),
        sa.Column('notification_email', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_login', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_verification_token', 'users', ['email_verification_token'])

    # Categories table
    op.create_table('categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(100)),
        sa.Column('icon', sa.String(50)),
        sa.Column('color', sa.String(7)),
        sa.Column('is_income', sa.Boolean(), default=False),
        sa.Column('is_expense', sa.Boolean(), default=True),
        sa.Column('keywords', sa.String(1000)),
        sa.Column('mcc_codes', sa.String(500)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_system', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('ix_categories_user_code', 'categories', ['user_id', 'code'], unique=True)
    op.create_index('ix_categories_id', 'categories', ['id'])

    # Currency rates table
    op.create_table('currency_rates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('target_currency', sa.String(3), nullable=False),
        sa.Column('rate', sa.Numeric(18, 6), nullable=False),
        sa.Column('rate_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_currency_rates_id', 'currency_rates', ['id'])
    op.create_index('ix_currency_rates_base_currency', 'currency_rates', ['base_currency'])
    op.create_index('ix_currency_rates_target_currency', 'currency_rates', ['target_currency'])
    op.create_index('ix_currency_rates_rate_date', 'currency_rates', ['rate_date'])
    op.create_index('ix_currency_rates_currencies_date', 'currency_rates', ['base_currency', 'target_currency', 'rate_date'])

    # Transactions table
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id', ondelete='SET NULL')),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), default='RUB'),
        sa.Column('description', sa.String(500)),
        sa.Column('category_confidence', sa.Numeric(5, 4)),
        sa.Column('category_manual', sa.Boolean(), default=False),
        sa.Column('source', postgresql.ENUM('tbank_api', 'manual', name='transaction_source', create_type=False), default='manual'),
        sa.Column('external_id', sa.String(255)),
        sa.Column('merchant_name', sa.String(255)),
        sa.Column('merchant_category_code', sa.String(10)),
        sa.Column('is_suspicious', sa.Boolean(), default=False),
        sa.Column('suspicious_reason', sa.String(255)),
        sa.Column('transaction_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_category_id', 'transactions', ['category_id'])
    op.create_index('ix_transactions_external_id', 'transactions', ['external_id'])
    op.create_index('ix_transactions_transaction_date', 'transactions', ['transaction_date'])
    op.create_index('ix_transactions_user_date', 'transactions', ['user_id', 'transaction_date'])

    # Reminders table
    op.create_table('reminders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('amount', sa.Numeric(18, 2)),
        sa.Column('currency', sa.String(3), default='RUB'),
        sa.Column('frequency', postgresql.ENUM('once', 'daily', 'weekly', 'monthly', 'custom', name='reminder_frequency', create_type=False), default='once'),
        sa.Column('interval_days', sa.Integer()),
        sa.Column('repeat_count', sa.Integer()),
        sa.Column('current_count', sa.Integer(), default=0),
        sa.Column('next_reminder_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_sent_date', sa.TIMESTAMP(timezone=True)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('send_email', sa.Boolean(), default=True),
        sa.Column('send_push', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('ix_reminders_id', 'reminders', ['id'])
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])
    op.create_index('ix_reminders_next_date', 'reminders', ['next_reminder_date'])
    op.create_index('ix_reminders_active', 'reminders', ['is_active', 'next_reminder_date'])

    # Notification history table
    op.create_table('notification_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reminder_id', sa.Integer(), sa.ForeignKey('reminders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.String(500)),
    )
    op.create_index('ix_notification_history_reminder_id', 'notification_history', ['reminder_id'])
    op.create_index('ix_notification_history_sent_at', 'notification_history', ['sent_at'])

    # Predictions table
    op.create_table('predictions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id', ondelete='SET NULL')),
        sa.Column('prediction_month', sa.Date(), nullable=False),
        sa.Column('predicted_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('confidence', sa.Numeric(5, 4)),
        sa.Column('actual_amount', sa.Numeric(18, 2)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_predictions_user_id', 'predictions', ['user_id'])
    op.create_index('ix_predictions_month', 'predictions', ['prediction_month'])
    op.create_index('ix_predictions_user_month', 'predictions', ['user_id', 'prediction_month'])

    # Audit logs table (БЕЗ колонок old_value, new_value, ip_address, user_agent - их нет в модели)
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100)),
        sa.Column('entity_id', sa.Integer()),
        sa.Column('description', sa.String(500)),
        sa.Column('status', sa.String(20)),
        sa.Column('error_message', sa.String(500)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('predictions')
    op.drop_table('notification_history')
    op.drop_table('reminders')
    op.drop_table('transactions')
    op.drop_table('currency_rates')
    op.drop_table('categories')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS reminder_frequency')
    op.execute('DROP TYPE IF EXISTS transaction_source')