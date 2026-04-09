"""update default language to en

Revision ID: 678d31913e7a
Revises: 2de405b771ec
Create Date: 2026-04-09 10:26:39.555155

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '678d31913e7a'
down_revision: Union[str, Sequence[str], None] = '2de405b771ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE users SET language = 'en' WHERE language = 'uk'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE users SET language = 'uk' WHERE language = 'en'")
