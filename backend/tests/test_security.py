from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("Secret#123")
    assert hashed != "Secret#123"
    assert verify_password("Secret#123", hashed)
    assert not verify_password("wrong", hashed)


def test_token_contains_user_and_role():
    payload = decode_access_token(create_access_token(7, "PROJECT_MANAGER"))
    assert payload["sub"] == "7"
    assert payload["role"] == "PROJECT_MANAGER"
