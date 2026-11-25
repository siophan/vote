"""one live submission per video; normalize city names

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-26 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LIVE = sa.text("status <> 'rejected'")


def upgrade() -> None:
    # Older duplicates would block the unique index: keep the earliest live
    # submission per video and reject the rest.
    op.execute(
        """
        UPDATE submissions SET status = 'rejected', reject_reason = '重复投稿'
        WHERE status <> 'rejected' AND id NOT IN (
            SELECT MIN(id) FROM submissions WHERE status <> 'rejected' GROUP BY video_url
        )
        """
    )
    op.create_index('uq_submissions_live_video', 'submissions', ['video_url'], unique=True,
                    postgresql_where=LIVE, sqlite_where=LIVE)
    # "杭州市" -> "杭州", matching app.rules.normalize_city.
    op.execute("UPDATE users SET city = SUBSTR(city, 1, LENGTH(city) - 1) WHERE city LIKE '%市' AND LENGTH(city) > 2")


def downgrade() -> None:
    op.drop_index('uq_submissions_live_video', table_name='submissions')
