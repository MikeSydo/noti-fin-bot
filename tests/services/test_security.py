import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.security import encrypt_token, decrypt_token


def test_encrypt_token_success():
    """Test that a valid token can be encrypted and returns bytes."""
    token = "my_secret_access_token"
    encrypted = encrypt_token(token)
    assert encrypted is not None
    assert isinstance(encrypted, bytes)
    assert encrypted != token.encode('utf-8')  # Should not be plaintext


def test_decrypt_token_success():
    """Test that an encrypted token can be decrypted back to the original."""
    token = "my_secret_access_token"
    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)
    assert decrypted == token


def test_encrypt_token_empty():
    """Test that encrypting an empty/None token returns None."""
    assert encrypt_token("") is None
    assert encrypt_token(None) is None


def test_decrypt_token_empty():
    """Test that decrypting an empty/None token returns None."""
    assert decrypt_token(b"") is None
    assert decrypt_token(None) is None


def test_encrypt_decrypt_roundtrip():
    """Test that encrypt -> decrypt produces the original value for various tokens."""
    tokens = [
        "short",
        "a" * 100,
        "token_with_special_chars!@#$%^&*()",
        "notion_secret_ABC_123",
    ]
    for token in tokens:
        encrypted = encrypt_token(token)
        decrypted = decrypt_token(encrypted)
        assert decrypted == token, f"Round-trip failed for token: {token}"
