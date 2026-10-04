"""Unit-тесты проверки входных данных (ошибочные данные и граничные значения)."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.application import ApplicationUpdate
from app.schemas.auth import UserCreate
from app.schemas.hotel_request import HotelRequestCreate
from app.schemas.participant import ParticipantCreate
from app.schemas.payment import PaymentCreate


@pytest.mark.parametrize("amount", [0, -1, -0.01])
def test_payment_amount_must_be_positive(amount):
    with pytest.raises(ValidationError):
        PaymentCreate(participant_id=1, amount=amount)


def test_smallest_positive_amount_is_accepted():
    assert PaymentCreate(participant_id=1, amount=0.01).amount == 0.01


def test_payment_status_defaults_to_pending():
    assert PaymentCreate(participant_id=1, amount=100).status == "pending"


def test_unknown_payment_status_is_rejected():
    with pytest.raises(ValidationError):
        PaymentCreate(participant_id=1, amount=100, status="refunded")


@pytest.mark.parametrize("status", ["pending", "confirmed", "rejected"])
def test_known_application_statuses(status):
    assert ApplicationUpdate(status=status).status == status


def test_unknown_application_status_is_rejected():
    with pytest.raises(ValidationError):
        ApplicationUpdate(status="approved")


@pytest.mark.parametrize("email", ["plain", "a@", "@example.com", "a b@example.com"])
def test_invalid_participant_email_is_rejected(email):
    with pytest.raises(ValidationError):
        ParticipantCreate(full_name="Тест", email=email)


@pytest.mark.parametrize(
    ("username", "valid"),
    [("ab", False), ("abc", True), ("a" * 50, True), ("a" * 51, False)],
)
def test_username_length_boundaries(username, valid):
    if valid:
        assert UserCreate(username=username, password="12345678").username
    else:
        with pytest.raises(ValidationError):
            UserCreate(username=username, password="12345678")


@pytest.mark.parametrize(
    ("password", "valid"),
    [("1234567", False), ("12345678", True), ("x" * 128, True), ("x" * 129, False)],
)
def test_password_length_boundaries(password, valid):
    if valid:
        assert UserCreate(username="user", password=password).password
    else:
        with pytest.raises(ValidationError):
            UserCreate(username="user", password=password)


def test_hotel_request_with_equal_dates_is_rejected():
    with pytest.raises(ValidationError):
        HotelRequestCreate(
            participant_id=1,
            required=True,
            check_in=date(2026, 10, 1),
            check_out=date(2026, 10, 1),
        )


def test_hotel_request_not_required_without_dates_is_accepted():
    request = HotelRequestCreate(participant_id=1, required=False)

    assert request.check_in is None
