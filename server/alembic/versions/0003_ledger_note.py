"""ledger note for admin adjustments

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-26 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('flower_ledger', sa.Column('note', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('flower_ledger', 'note')
