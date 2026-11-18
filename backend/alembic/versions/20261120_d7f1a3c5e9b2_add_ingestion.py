from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7f1a3c5e9b2"
down_revision: str | None = "c4e6a8b0d2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("damage_maps", sa.Column("source", sa.String(length=16), nullable=True))
    op.add_column("damage_maps", sa.Column("source_label", sa.String(length=200), nullable=True))

    op.create_table(
        "devices",
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name_ar", sa.String(length=200), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("facade_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot_url", sa.String(length=500), nullable=True),
        sa.Column("rtsp_url", sa.String(length=500), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("secret_env", sa.String(length=100), nullable=True),
        sa.Column("interval_h", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_capture_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=16), nullable=True),
        sa.Column("last_error_ar", sa.Text(), nullable=True),
        sa.Column("last_photo_key", sa.String(length=300), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("interval_h IS NULL OR interval_h > 0", name=op.f("ck_devices_positive_interval")),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_devices_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["facade_id"], ["facades.id"], name=op.f("fk_devices_facade_id_facades"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_devices_site_id_sites"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
    )
    op.create_index(op.f("ix_devices_site_id"), "devices", ["site_id"], unique=False)

    op.create_table(
        "ingest_jobs",
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("source_label", sa.String(length=200), nullable=True),
        sa.Column("file_name", sa.String(length=200), nullable=False),
        sa.Column("photo_key", sa.String(length=300), nullable=True),
        sa.Column("photo_ready", sa.Boolean(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("facade_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("error_ar", sa.Text(), nullable=True),
        sa.Column("photo_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("map_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_ingest_jobs_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.id"], name=op.f("fk_ingest_jobs_device_id_devices"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["facade_id"], ["facades.id"], name=op.f("fk_ingest_jobs_facade_id_facades"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["map_id"],
            ["damage_maps.id"],
            name=op.f("fk_ingest_jobs_map_id_damage_maps"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_ingest_jobs_site_id_sites"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_jobs")),
    )
    op.create_index(op.f("ix_ingest_jobs_batch_id"), "ingest_jobs", ["batch_id"], unique=False)
    op.create_index(
        "ix_ingest_jobs_due",
        "ingest_jobs",
        ["next_attempt_at"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "ix_ingest_jobs_device_recent",
        "ingest_jobs",
        ["device_id", sa.literal_column("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_jobs_device_recent", table_name="ingest_jobs")
    op.drop_index(
        "ix_ingest_jobs_due", table_name="ingest_jobs", postgresql_where=sa.text("status = 'queued'")
    )
    op.drop_index(op.f("ix_ingest_jobs_batch_id"), table_name="ingest_jobs")
    op.drop_table("ingest_jobs")
    op.drop_index(op.f("ix_devices_site_id"), table_name="devices")
    op.drop_table("devices")
    op.drop_column("damage_maps", "source_label")
    op.drop_column("damage_maps", "source")
