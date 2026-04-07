"""initial moderation schema

Revision ID: 0001_moderation_initial
Revises: 
Create Date: 2026-04-07 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_moderation_initial"
down_revision = None
branch_labels = None
depends_on = None


moderation_status_enum = sa.Enum("pending", "approved", "rejected", name="moderationstatus")


def upgrade() -> None:
    moderation_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "moderation_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_url", sa.String(length=500), nullable=False),
        sa.Column("status", moderation_status_enum, nullable=False),
        sa.Column("moderator_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_moderation_queue_author_id"), "moderation_queue", ["author_id"], unique=False)
    op.create_index(op.f("ix_moderation_queue_status"), "moderation_queue", ["status"], unique=False)
    op.create_index(op.f("ix_moderation_queue_video_id"), "moderation_queue", ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_moderation_queue_video_id"), table_name="moderation_queue")
    op.drop_index(op.f("ix_moderation_queue_status"), table_name="moderation_queue")
    op.drop_index(op.f("ix_moderation_queue_author_id"), table_name="moderation_queue")
    op.drop_table("moderation_queue")
    moderation_status_enum.drop(op.get_bind(), checkfirst=True)
