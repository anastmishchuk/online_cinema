"""Add initial user groups

Revision ID: 5e0beadc5bb2
Revises: 81ff8cc67aff
Create Date: 2025-05-31 23:11:19.219698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e0beadc5bb2'
down_revision: Union[str, None] = '81ff8cc67aff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("INSERT INTO user_groups (id, name) VALUES (1, 'USER')")
    op.execute("INSERT INTO user_groups (id, name) VALUES (2, 'MODERATOR')")
    op.execute("INSERT INTO user_groups (id, name) VALUES (3, 'ADMIN')")


def downgrade():
    op.execute("DELETE FROM user_groups WHERE id IN (1, 2, 3)")

