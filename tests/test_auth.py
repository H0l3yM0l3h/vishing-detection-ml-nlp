from app.auth import validate_password, hash_password, verify_password


def test_validate_password_accepts_strong_password():
    assert validate_password("Abcd1234!@#$")


def test_validate_password_rejects_short_password():
    assert not validate_password("Abc1!def")


def test_validate_password_requires_upper_lower_digit_symbol():
    assert not validate_password("abcdefg12345!")  # missing upper
    assert not validate_password("ABCDEFG12345!")  # missing lower
    assert not validate_password("Abcdefghijkl!")  # missing digit
    assert not validate_password("Abcdefghijkl1")  # missing symbol


def test_hash_and_verify_password_roundtrip():
    password = "Abcd1234!@#$"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("Wrong1234!@#$", hashed)
