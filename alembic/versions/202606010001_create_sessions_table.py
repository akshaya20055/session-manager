"""create interview sessions table

Revision ID: 202606010001
Revises:
Create Date: 2026-06-01 00:01:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202606010001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "PAUSED",
                "ENDED",
                name="session_status",
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_sessions_candidate_id"), "interview_sessions", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_id"), "interview_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_status"), "interview_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_interview_sessions_status"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_id"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_candidate_id"), table_name="interview_sessions")
    op.drop_table("interview_sessions")
