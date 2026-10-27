import hashlib
import secrets
import base64
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("Security")

# Hardcoded internal application pepper
_APP_PEPPER = "PN_HOADON_SECURE_PEPPER_v1_2026_@!"

def hash_password(password: str) -> tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Returns: (hash_hex, salt_hex)
    """
    salt = secrets.token_bytes(16)
    pwd_bytes = password.strip().encode("utf-8")
    pwd_hash = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, 100000)
    return pwd_hash.hex(), salt.hex()

def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """
    Verify password against stored hash and salt.
    """
    if not password or not hash_hex or not salt_hex:
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        pwd_bytes = password.strip().encode("utf-8")
        calc_hash = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, 100000).hex()
        return secrets.compare_digest(calc_hash, hash_hex)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def _get_cipher(seed: str) -> Fernet:
    combined = f"{_APP_PEPPER}_{seed}"
    key = base64.urlsafe_b64encode(hashlib.sha256(combined.encode("utf-8")).digest())
    return Fernet(key)

def encrypt_text(plaintext: str, seed: str) -> str:
    """
    Encrypt text using AES-128-CBC + HMAC-SHA256 (Fernet).
    """
    if not plaintext:
        return ""
    plaintext = plaintext.strip()
    # If already looks like a fernet token, don't double encrypt
    if plaintext.startswith("gAAAAAB"):
        return plaintext
    cipher = _get_cipher(seed)
    return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_text(ciphertext: str, seed: str) -> str:
    """
    Decrypt text. If not encrypted or invalid token, gracefully return original.
    """
    if not ciphertext:
        return ""
    ciphertext = ciphertext.strip()
    if not ciphertext.startswith("gAAAAAB"):
        # Plaintext fallback
        return ciphertext
    try:
        cipher = _get_cipher(seed)
        return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.warning(f"Could not decrypt text, returning raw: {e}")
        return ciphertext
