"""initial feed schema

Revision ID: 0001_feed_initial
Revises: 
Create Date: 2026-04-07 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_feed_initial"
down_revision = None
branch_labels = None
depends_on = None


video_status_enum = sa.Enum("moderation_pending", "approved", "rejected", name="videostatus")
video_status_column_enum = postgresql.ENUM(
    "moderation_pending",
    "approved",
    "rejected",
    name="videostatus",
    create_type=False,
)


def upgrade() -> None:
    video_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hashtags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("location_city", sa.String(length=128), nullable=True),
        sa.Column("location_latitude", sa.Float(), nullable=True),
        sa.Column("location_longitude", sa.Float(), nullable=True),
        sa.Column("hls_url", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("status", video_status_column_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_videos_author_id"), "videos", ["author_id"], unique=False)
    op.create_index(op.f("ix_videos_created_at"), "videos", ["created_at"], unique=False)
    op.create_index(op.f("ix_videos_status"), "videos", ["status"], unique=False)

    op.create_table(
        "likes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "video_id", name="uq_like_user_video"),
    )
    op.create_index(op.f("ix_likes_user_id"), "likes", ["user_id"], unique=False)
    op.create_index(op.f("ix_likes_video_id"), "likes", ["video_id"], unique=False)

    op.create_table(
        "follows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("followee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("follower_id", "followee_id", name="uq_follow_pair"),
    )
    op.create_index(op.f("ix_follows_follower_id"), "follows", ["follower_id"], unique=False)
    op.create_index(op.f("ix_follows_followee_id"), "follows", ["followee_id"], unique=False)

    op.create_table(
        "views",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "video_id", name="uq_view_user_video"),
    )
    op.create_index(op.f("ix_views_user_id"), "views", ["user_id"], unique=False)
    op.create_index(op.f("ix_views_video_id"), "views", ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_views_video_id"), table_name="views")
    op.drop_index(op.f("ix_views_user_id"), table_name="views")
    op.drop_table("views")
    op.drop_index(op.f("ix_follows_followee_id"), table_name="follows")
    op.drop_index(op.f("ix_follows_follower_id"), table_name="follows")
    op.drop_table("follows")
    op.drop_index(op.f("ix_likes_video_id"), table_name="likes")
    op.drop_index(op.f("ix_likes_user_id"), table_name="likes")
    op.drop_table("likes")
    op.drop_index(op.f("ix_videos_status"), table_name="videos")
    op.drop_index(op.f("ix_videos_created_at"), table_name="videos")
    op.drop_index(op.f("ix_videos_author_id"), table_name="videos")
    op.drop_table("videos")
    video_status_enum.drop(op.get_bind(), checkfirst=True)
