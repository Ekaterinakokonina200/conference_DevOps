"""Unit-тесты хеширования паролей и JWT (ТЗ 6.1, 8.4, 8.5)."""

import jwt
import pytest

from app import security


def test_hash_is_argon2_and_not_plain_password():
    hashed = security.hash_password("StrongPassword123!")

    assert hashed.startswith("$argon2")
    assert "StrongPassword123!" not in hashed


def test_same_password_gives_different_hashes():
    assert security.hash_password("secret-pass") != security.hash_password(
        "secret-pass"
    )


def test_verify_password():
    hashed = security.hash_password("secret-pass")

    assert security.verify_password("secret-pass", hashed) is True
    assert security.verify_password("Secret-pass", hashed) is False


def test_access_token_has_subject_and_expiration():
    token = security.create_access_token("anna")
    payload = jwt.decode(
        token, security.JWT_SECRET_KEY, algorithms=[security.JWT_ALGORITHM]
    )

    assert payload["sub"] == "anna"
    assert "exp" in payload


def test_token_signed_with_other_key_is_rejected():
    token = security.create_access_token("anna")

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "other-key-" * 5, algorithms=[security.JWT_ALGORITHM])
