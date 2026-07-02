"""add_nomba_credentials_to_merchants

Revision ID: 8795a76d49a1
Revises: 9bfa8974ca0c
Create Date: 2026-07-02 07:28:46.907155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8795a76d49a1'
down_revision: Union[str, Sequence[str], None] = '9bfa8974ca0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('merchants', sa.Column('nomba_client_id', sa.String(), nullable=True))
    op.add_column('merchants', sa.Column('nomba_client_secret_encrypted', sa.String(), nullable=True))
    op.add_column('merchants', sa.Column('nomba_account_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('merchants', 'nomba_account_id')
    op.drop_column('merchants', 'nomba_client_secret_encrypted')
    op.drop_column('merchants', 'nomba_client_id')
