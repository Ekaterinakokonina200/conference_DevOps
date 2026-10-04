"""add status and amount check constraints

Revision ID: d4f8a1c2b3e5
Revises: c027a5eb74d0

Изменение схемы №1 (ЛР3). Допустимые статусы и положительная сумма
оплаты проверяются не только приложением, но и самой базой данных.
Перед созданием ограничений существующие данные приводятся к допустимому
виду, поэтому миграция проходит и на базе, где уже есть записи.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4f8a1c2b3e5"
down_revision: str | Sequence[str] | None = "c027a5eb74d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# таблица: (имя ограничения, допустимые значения, значение по умолчанию)
STATUS_CHECKS = {
    "applications": (
        "ck_applications_status",
        ("pending", "confirmed", "rejected"),
        "pending",
    ),
    "payments": ("ck_payments_status", ("pending", "paid", "cancelled"), "pending"),
    "invitations": (
        "ck_invitations_status",
        ("created", "sent", "accepted", "declined"),
        "created",
    ),
    "theses": (
        "ck_theses_status",
        ("submitted", "approved", "rejected"),
        "submitted",
    ),
}


def condition(values: tuple[str, ...]) -> str:
    return "status IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    connection = op.get_bind()

    bad_payments = connection.scalar(
        sa.text("SELECT count(*) FROM payments WHERE amount <= 0")
    )
    if bad_payments:
        raise RuntimeError(
            f"В таблице payments {bad_payments} записей с amount <= 0. "
            "Финансовые данные не исправляются автоматически: исправьте их "
            "вручную и повторите alembic upgrade head."
        )

    for table, (name, values, default) in STATUS_CHECKS.items():
        # 'Paid ' -> 'paid'; неизвестные значения -> статус по умолчанию
        op.execute(f"UPDATE {table} SET status = lower(trim(status))")
        op.execute(
            f"UPDATE {table} SET status = '{default}' WHERE NOT {condition(values)}"
        )
        op.create_check_constraint(name, table, condition(values))

    op.create_check_constraint("ck_payments_amount_positive", "payments", "amount > 0")


def downgrade() -> None:
    op.drop_constraint("ck_payments_amount_positive", "payments", type_="check")
    for table, (name, _values, _default) in STATUS_CHECKS.items():
        op.drop_constraint(name, table, type_="check")
