from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9e2a4b6c8d10"
down_revision: str | None = "7c1d2e3f4a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_scans",
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("is_sample", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("baseline_start", sa.Date(), nullable=False),
        sa.Column("baseline_end", sa.Date(), nullable=False),
        sa.Column("recent_start", sa.Date(), nullable=False),
        sa.Column("recent_end", sa.Date(), nullable=False),
        sa.Column("baseline_scenes", sa.Integer(), nullable=False),
        sa.Column("recent_scenes", sa.Integer(), nullable=False),
        sa.Column("valid_share", sa.Float(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("before_key", sa.String(length=300), nullable=True),
        sa.Column("after_key", sa.String(length=300), nullable=True),
        sa.Column("change_key", sa.String(length=300), nullable=True),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ground_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mission_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name=op.f("ck_site_scans_score_range")),
        sa.CheckConstraint("valid_share BETWEEN 0 AND 1", name=op.f("ck_site_scans_valid_share_range")),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
            name=op.f("fk_site_scans_acknowledged_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_site_scans_site_id_sites"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_scans")),
    )
    op.create_index(
        "ix_site_scans_site_recent",
        "site_scans",
        ["site_id", sa.literal_column("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_site_scans_site_recent", table_name="site_scans")
    op.drop_table("site_scans")
