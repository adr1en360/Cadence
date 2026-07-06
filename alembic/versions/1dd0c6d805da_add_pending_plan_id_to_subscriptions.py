"""add pending_plan_id to subscriptions

Revision ID: 1dd0c6d805da
Revises: 3f70833ccebb
Create Date: 2026-07-06 19:42:48.591263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dd0c6d805da'
down_revision: Union[str, Sequence[str], None] = '3f70833ccebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('subscriptions', sa.Column('pending_plan_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_subscriptions_pending_plan',
        'subscriptions', 'plans',
        ['pending_plan_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_subscriptions_pending_plan', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'pending_plan_id')
