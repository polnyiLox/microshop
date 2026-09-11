from app.security.refresh_token import hash_refresh_token, verify_refresh_token


def test_refresh_token_hash_is_deterministic_and_not_plaintext() -> None:
    digest = hash_refresh_token("refresh-token")

    assert digest == hash_refresh_token("refresh-token")
    assert digest != "refresh-token"
    assert verify_refresh_token("refresh-token", digest)
    assert not verify_refresh_token("other-token", digest)
