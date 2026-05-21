from app.auth import validate_password, hash_password, verify_password


def test_validate_password_accepts_strong_password():
    valid, _ = validate_password("Abcd1234!@#$")
    assert valid


def test_validate_password_rejects_short_password():
    valid, reason = validate_password("Abc1!def")
    assert not valid
    assert "at least 12 characters" in reason


def test_validate_password_requires_upper_lower_digit_symbol():
    cases = [
        ("abcdefg12345!", "uppercase"),
        ("ABCDEFG12345!", "lowercase"),
        ("Abcdefghijkl!", "number"),
        ("Abcdefghijkl1", "special"),
    ]

    for password, expected_reason in cases:
        valid, reason = validate_password(password)
        assert not valid
        assert expected_reason in reason


def test_hash_and_verify_password_roundtrip():
    password = "Abcd1234!@#$"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("Wrong1234!@#$", hashed)
