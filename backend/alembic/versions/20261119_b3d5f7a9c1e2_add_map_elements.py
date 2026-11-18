from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3d5f7a9c1e2"
down_revision: str | None = "9e2a4b6c8d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "damage_maps",
        sa.Column(
            "elements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "damage_maps", sa.Column("elements_edited", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column(
        "damage_maps",
        sa.Column(
            "correction_log",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("damage_maps", sa.Column("field_inspected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("damage_maps", sa.Column("field_inspected_by", sa.Uuid(), nullable=True))
    op.add_column("damage_maps", sa.Column("field_notes", sa.Text(), server_default="", nullable=False))
    op.create_foreign_key(
        op.f("fk_damage_maps_field_inspected_by_users"),
        "damage_maps",
        "users",
        ["field_inspected_by"],
        ["id"],
        ondelete="SET NULL",
    )
    for column in ("elements", "elements_edited", "correction_log", "field_notes"):
        op.alter_column("damage_maps", column, server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("fk_damage_maps_field_inspected_by_users"), "damage_maps", type_="foreignkey")
    for column in (
        "field_notes",
        "field_inspected_by",
        "field_inspected_at",
        "correction_log",
        "elements_edited",
        "elements",
    ):
        op.drop_column("damage_maps", column)
