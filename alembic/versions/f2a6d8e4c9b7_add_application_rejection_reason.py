"""add rejection reason to applications

Revision ID: f2a6d8e4c9b7
Revises: e7b9c3d5f6a1

Изменение схемы №3 (ЛР3) для новой функции: отклонённая заявка должна
содержать причину отклонения. Уже отклонённым заявкам (до версии 0.3.0)
проставляется причина по умолчанию, после чего база запрещает статус
rejected без причины.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a6d8e4c9b7"
down_revision: str | Sequence[str] | None = "e7b9c3d5f6a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_REASON = "Причина не указана (заявка отклонена до версии 0.3.0)"


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE applications SET rejection_reason = :reason "
            "WHERE status = 'rejected'"
        ).bindparams(reason=DEFAULT_REASON)
    )
    op.create_check_constraint(
        "ck_applications_rejection_reason",
        "applications",
        "status <> 'rejected' OR rejection_reason IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_applications_rejection_reason", "applications", type_="check"
    )
    op.drop_column("applications", "rejection_reason")
