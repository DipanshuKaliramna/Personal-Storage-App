"""initial schema

Revision ID: 20260411_0001
Revises:
Create Date: 2026-04-11 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260411_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_code", sa.String(length=6), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("used_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "media_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("s3_key"),
    )
    op.create_index(op.f("ix_media_items_owner_id"), "media_items", ["owner_id"], unique=False)

    op.create_table(
        "albums",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_albums_owner_id"), "albums", ["owner_id"], unique=False)

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    op.create_table(
        "share_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=True),
        sa.Column("album_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"]),
        sa.ForeignKeyConstraint(["media_id"], ["media_items.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_share_links_owner_id"), "share_links", ["owner_id"], unique=False)
    op.create_index(op.f("ix_share_links_token"), "share_links", ["token"], unique=True)

    op.create_table(
        "album_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("album_id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"]),
        sa.ForeignKeyConstraint(["media_id"], ["media_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("album_id", "media_id", name="uq_album_media"),
    )


def downgrade() -> None:
    op.drop_table("album_items")
    op.drop_index(op.f("ix_share_links_token"), table_name="share_links")
    op.drop_index(op.f("ix_share_links_owner_id"), table_name="share_links")
    op.drop_table("share_links")
    op.drop_table("oauth_accounts")
    op.drop_index(op.f("ix_albums_owner_id"), table_name="albums")
    op.drop_table("albums")
    op.drop_index(op.f("ix_media_items_owner_id"), table_name="media_items")
    op.drop_table("media_items")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
