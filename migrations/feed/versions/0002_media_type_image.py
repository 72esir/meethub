"""add media type and image url

Revision ID: 0002_feed_media_type
Revises: 0001_feed_initial
Create Date: 2026-04-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_feed_media_type"
down_revision = "0001_feed_initial"
branch_labels = None
depends_on = None


media_type_enum = sa.Enum("video", "image", name="mediatype")
media_type_column_enum = postgresql.ENUM("video", "image", name="mediatype", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    media_type_enum.create(bind, checkfirst=True)
    op.add_column("videos", sa.Column("media_type", media_type_column_enum, nullable=True))
    op.add_column("videos", sa.Column("media_url", sa.String(length=500), nullable=True))
    op.execute("UPDATE videos SET media_type = 'video' WHERE media_type IS NULL")
    op.execute("UPDATE videos SET media_url = hls_url WHERE media_url IS NULL")
    op.alter_column("videos", "media_type", nullable=False)
    op.alter_column("videos", "hls_url", nullable=True)
    op.create_index(op.f("ix_videos_media_type"), "videos", ["media_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_videos_media_type"), table_name="videos")
    op.alter_column("videos", "hls_url", nullable=False)
    op.drop_column("videos", "media_url")
    op.drop_column("videos", "media_type")
    media_type_enum.drop(op.get_bind(), checkfirst=True)
