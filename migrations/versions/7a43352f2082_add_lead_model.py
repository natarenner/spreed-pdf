"""add_lead_model

Revision ID: 7a43352f2082
Revises: fb5ab4c2c985
Create Date: 2026-01-28 18:38:51.712884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a43352f2082'
down_revision: Union[str, None] = 'fb5ab4c2c985'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('has_purchased', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_booked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )


def downgrade() -> None:
    op.drop_table('leads')
