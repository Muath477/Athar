from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7c1d2e3f4a5b"
down_revision: str | None = "398e8f500201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "damage_maps",
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("facade_id", sa.Uuid(), nullable=True),
        sa.Column("wall_name", sa.String(length=200), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("cols", sa.Integer(), nullable=False),
        sa.Column("corners", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("photo_key", sa.String(length=300), nullable=False),
        sa.Column("rectified_key", sa.String(length=300), nullable=False),
        sa.Column("rectified_width_px", sa.Integer(), nullable=False),
        sa.Column("rectified_height_px", sa.Integer(), nullable=False),
        sa.Column("detector", sa.String(length=40), nullable=False),
        sa.Column("detector_status", sa.String(length=16), nullable=False),
        sa.Column("summary_ar", sa.Text(), nullable=False),
        sa.Column("model_cells", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name=op.f("ck_damage_maps_approved_has_reviewer"),
        ),
        sa.CheckConstraint("width_m > 0 AND height_m > 0", name=op.f("ck_damage_maps_positive_size")),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], name=op.f("fk_damage_maps_approved_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_damage_maps_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["facade_id"], ["facades.id"], name=op.f("fk_damage_maps_facade_id_facades"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_damage_maps_site_id_sites"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_damage_maps")),
    )
    op.create_index(
        "ix_damage_maps_facade_recent",
        "damage_maps",
        ["facade_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_damage_maps_site_recent",
        "damage_maps",
        ["site_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_table(
        "damage_map_cells",
        sa.Column("map_id", sa.Uuid(), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("damage_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.CheckConstraint('"row" >= 0 AND col >= 0', name=op.f("ck_damage_map_cells_non_negative_cell")),
        sa.ForeignKeyConstraint(
            ["map_id"],
            ["damage_maps.id"],
            name=op.f("fk_damage_map_cells_map_id_damage_maps"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("map_id", "row", "col", name=op.f("pk_damage_map_cells")),
    )


def downgrade() -> None:
    op.drop_table("damage_map_cells")
    op.drop_index("ix_damage_maps_site_recent", table_name="damage_maps")
    op.drop_index("ix_damage_maps_facade_recent", table_name="damage_maps")
    op.drop_table("damage_maps")
