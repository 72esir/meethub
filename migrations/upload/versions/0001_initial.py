"""initial upload schema

Revision ID: 0001_upload_initial
Revises: 
Create Date: 2026-04-07 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_upload_initial"
down_revision = None
branch_labels = None
depends_on = None


upload_status_enum = sa.Enum("pending", "uploaded", "transcoding", "ready", "error", name="uploadstatus")


def upgrade() -> None:
    upload_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "upload_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("s3_key", sa.String(length=500), nullable=False),
        sa.Column("status", upload_status_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("location_city", sa.String(length=128), nullable=True),
        sa.Column("location_latitude", sa.Float(), nullable=True),
        sa.Column("location_longitude", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("s3_key"),
    )
    op.create_index(op.f("ix_upload_sessions_user_id"), "upload_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_sessions_user_id"), table_name="upload_sessions")
    op.drop_table("upload_sessions")
    upload_status_enum.drop(op.get_bind(), checkfirst=True)
