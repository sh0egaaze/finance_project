"""Add CASCADE to categories

Revision ID: 34b51cbc93ac
Revises: b38039afdb45
Create Date: 2026-05-14 11:18:51.336017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34b51cbc93ac'
down_revision: Union[str, None] = 'b38039afdb45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем старый foreign key без CASCADE
    op.drop_constraint('categories_user_id_fkey', 'categories', type_='foreignkey')

    # Создаём новый foreign key с CASCADE
    op.create_foreign_key(
        'categories_user_id_fkey',
        'categories',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Удаляем foreign key с CASCADE
    op.drop_constraint('categories_user_id_fkey', 'categories', type_='foreignkey')

    # Возвращаем старый foreign key без CASCADE
    op.create_foreign_key(
        'categories_user_id_fkey',
        'categories',
        'users',
        ['user_id'],
        ['id']
    )