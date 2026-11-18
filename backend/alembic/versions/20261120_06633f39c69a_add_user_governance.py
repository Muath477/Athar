from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "06633f39c69a"
down_revision: str | None = "c4e6a8b0d2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(120), server_default="", nullable=False))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column(
        "users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "user_sites",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_sites_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_user_sites_site_id_sites"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "site_id", name=op.f("pk_user_sites")),
    )
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"])
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_table("user_sites")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "is_active")
    op.drop_column("users", "display_name")
