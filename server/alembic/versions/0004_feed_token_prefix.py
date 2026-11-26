"""prefix stored feed tokens with "token/"

<channel-video feed-token> needs the "token/" prefix; tokens saved before the
review form normalized them were stored bare.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26 19:00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE submissions SET feed_token = 'token/' || feed_token "
        "WHERE feed_token IS NOT NULL AND feed_token NOT LIKE 'token/%'"
    )


def downgrade() -> None:
    # Tokens may have been entered with the prefix already; there is no way to
    # tell which ones this migration touched, so leave them as they are.
    pass
