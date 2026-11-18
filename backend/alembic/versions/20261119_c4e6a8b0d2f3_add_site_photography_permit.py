from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e6a8b0d2f3"
down_revision: str | None = "b3d5f7a9c1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("field_photography_permitted", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("sites", "field_photography_permitted", server_default=None)


def downgrade() -> None:
    op.drop_column("sites", "field_photography_permitted")
