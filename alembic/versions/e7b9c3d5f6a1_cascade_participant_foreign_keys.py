"""cascade participant foreign keys and index them

Revision ID: e7b9c3d5f6a1
Revises: d4f8a1c2b3e5

Изменение схемы №2 (ЛР3). Раньше удаление участника, у которого есть
заявки, оплаты, тезисы, приглашения или запросы на гостиницу, падало
с ошибкой внешнего ключа (500 Internal Server Error). Теперь связанные
записи удаляются вместе с участником (ON DELETE CASCADE), а поиск
по participant_id ускорен индексами.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7b9c3d5f6a1"
down_revision: str | Sequence[str] | None = "d4f8a1c2b3e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHILD_TABLES = ("applications", "invitations", "payments", "theses", "hotel_requests")


def recreate_foreign_key(table: str, ondelete: str | None) -> None:
    name = f"{table}_participant_id_fkey"
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(
        name, table, "participants", ["participant_id"], ["id"], ondelete=ondelete
    )


def upgrade() -> None:
    for table in CHILD_TABLES:
        recreate_foreign_key(table, ondelete="CASCADE")
        op.create_index(f"ix_{table}_participant_id", table, ["participant_id"])


def downgrade() -> None:
    for table in CHILD_TABLES:
        op.drop_index(f"ix_{table}_participant_id", table_name=table)
        recreate_foreign_key(table, ondelete=None)
