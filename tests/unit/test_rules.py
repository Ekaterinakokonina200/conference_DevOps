"""Unit-тесты основной логики app/services/rules.py (без базы данных)."""

from datetime import UTC, date, datetime

import pytest

from app.services import rules

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
EARLIER = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


# --- ТЗ 8.1: подтверждение заявки только после оплаты ---------------------


def test_fee_is_paid_when_one_payment_is_paid():
    assert rules.has_paid_fee(["pending", "paid"]) is True


@pytest.mark.parametrize(
    "statuses", [[], ["pending"], ["cancelled"], ["pending", "cancelled"], ["PAID"]]
)
def test_fee_is_not_paid_without_paid_payment(statuses):
    assert rules.has_paid_fee(statuses) is False


def test_confirm_without_payment_is_forbidden():
    with pytest.raises(rules.BusinessRuleError) as error:
        rules.ensure_application_status_allowed("confirmed", [])

    assert error.value.detail == "Registration fee must be paid before confirmation"


def test_confirm_with_pending_payment_is_forbidden():
    with pytest.raises(rules.BusinessRuleError):
        rules.ensure_application_status_allowed("confirmed", ["pending"])


def test_confirm_with_paid_payment_is_allowed():
    rules.ensure_application_status_allowed("confirmed", ["paid"])


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_other_statuses_do_not_require_payment(status):
    rules.ensure_application_status_allowed(status, [])


# --- Оплата: дата оплаты -----------------------------------------------------


def test_paid_payment_gets_current_date():
    assert rules.payment_date_for("paid", NOW) == NOW


@pytest.mark.parametrize("status", ["pending", "cancelled"])
def test_unpaid_payment_has_no_date(status):
    assert rules.payment_date_for(status, NOW) is None


# --- Приглашение: время отправки --------------------------------------------


def test_sent_invitation_gets_current_time():
    assert rules.invitation_sent_at("sent", None, NOW) == NOW


def test_resent_invitation_gets_new_time():
    assert rules.invitation_sent_at("sent", EARLIER, NOW) == NOW


@pytest.mark.parametrize("status", ["created", "accepted", "declined"])
def test_other_invitation_statuses_keep_previous_time(status):
    assert rules.invitation_sent_at(status, EARLIER, NOW) == EARLIER
    assert rules.invitation_sent_at(status, None, NOW) is None


# --- Гостиница: даты проживания (граничные случаи) ---------------------------


def test_dates_not_needed_when_hotel_not_required():
    rules.validate_stay_dates(False, None, None)


def test_dates_not_checked_when_hotel_not_required():
    rules.validate_stay_dates(False, date(2026, 10, 5), date(2026, 10, 1))


@pytest.mark.parametrize(
    ("check_in", "check_out"),
    [(None, None), (date(2026, 10, 1), None), (None, date(2026, 10, 2))],
)
def test_required_hotel_needs_both_dates(check_in, check_out):
    with pytest.raises(ValueError, match="^Check-in and check-out dates are required$"):
        rules.validate_stay_dates(True, check_in, check_out)


def test_check_out_on_same_day_is_rejected():
    with pytest.raises(
        ValueError, match="^Check-out date must be after check-in date$"
    ):
        rules.validate_stay_dates(True, date(2026, 10, 1), date(2026, 10, 1))


def test_check_out_before_check_in_is_rejected():
    with pytest.raises(
        ValueError, match="^Check-out date must be after check-in date$"
    ):
        rules.validate_stay_dates(True, date(2026, 10, 2), date(2026, 10, 1))


def test_one_night_stay_is_allowed():
    rules.validate_stay_dates(True, date(2026, 10, 1), date(2026, 10, 2))


# --- Новая функция: причина отклонения заявки ---------------------------------


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_rejection_requires_reason(reason):
    with pytest.raises(ValueError, match="^Rejection reason is required$"):
        rules.rejection_reason_for("rejected", reason)


def test_rejection_reason_is_trimmed():
    assert rules.rejection_reason_for("rejected", "  Нет мест  ") == "Нет мест"


@pytest.mark.parametrize("status", ["pending", "confirmed"])
def test_reason_is_cleared_for_other_statuses(status):
    assert rules.rejection_reason_for(status, "Старая причина") is None
