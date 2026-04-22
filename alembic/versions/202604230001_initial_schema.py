"""Initial schema

Revision ID: 202604230001
Revises:
Create Date: 2026-04-23 00:01:00
"""

from app import models  # noqa: F401
from app.db.base import Base
from alembic import op


# revision identifiers, used by Alembic.
revision = "202604230001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
