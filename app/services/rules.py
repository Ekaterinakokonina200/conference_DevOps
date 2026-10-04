"""Основная логика (бизнес-правила) Conference Management System.

Функции не обращаются к базе данных и HTTP, поэтому их проверяют быстрые
unit-тесты tests/unit/test_rules.py. Мутационная проверка (make mutation)
меняет условия в этом файле и убеждается, что тесты замечают каждое изменение.
"""

from collections.abc import Iterable
from datetime import date, datetime

PAID = "paid"
CONFIRMED = "confirmed"
SENT = "sent"

FEE_NOT_PAID = "Registration fee must be paid before confirmation"
DATES_REQUIRED = "Check-in and check-out dates are required"
CHECK_OUT_BEFORE_CHECK_IN = "Check-out date must be after check-in date"


class BusinessRuleError(Exception):
    """Нарушение правила предметной области (API отвечает 409 Conflict)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def has_paid_fee(payment_statuses: Iterable[str]) -> bool:
    """Есть ли у участника хотя бы одна оплата со статусом paid."""
    return PAID in payment_statuses


def ensure_application_status_allowed(
    new_status: str, payment_statuses: Iterable[str]
) -> None:
    """ТЗ 8.1: заявку нельзя подтвердить без оплаты со статусом paid."""
    if new_status == CONFIRMED and not has_paid_fee(payment_statuses):
        raise BusinessRuleError(FEE_NOT_PAID)


def payment_date_for(status: str, now: datetime) -> datetime | None:
    """Дата оплаты ставится только для статуса paid, иначе очищается."""
    if status == PAID:
        return now
    return None


def invitation_sent_at(
    status: str, current: datetime | None, now: datetime
) -> datetime | None:
    """При переводе приглашения в sent фиксируется время отправки."""
    if status == SENT:
        return now
    return current


def validate_stay_dates(
    required: bool, check_in: date | None, check_out: date | None
) -> None:
    """Гостиница: при required=true нужны обе даты и выезд позже заезда."""
    if not required:
        return
    if check_in is None or check_out is None:
        raise ValueError(DATES_REQUIRED)
    if check_out <= check_in:
        raise ValueError(CHECK_OUT_BEFORE_CHECK_IN)
