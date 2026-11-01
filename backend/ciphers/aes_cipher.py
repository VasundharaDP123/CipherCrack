"""AES-256 symmetric encryption (CBC mode with PKCS7 padding).

Uses pycryptodome (Crypto) — install with:
    pip install pycryptodome

Public API mirrors the classical cipher modules:
    encrypt(plaintext, key)  -> ciphertext_b64
    decrypt(ciphertext_b64, key) -> plaintext
    random_key()             -> 32-byte hex string (256-bit key)
    key_info(raw_key)        -> dict with algorithm details

Key may be supplied as:
    - 32-char hex string   (128-bit / 16 bytes)
    - 48-char hex string   (192-bit / 24 bytes)
    - 64-char hex string   (256-bit / 32 bytes)
    - any other string     -> SHA-256 hashed to 32 bytes (256-bit)
"""

import base64
import hashlib
import os
import secrets

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ------------------------------------------------------------------ helpers

VALID_KEY_SIZES = {16: 128, 24: 192, 32: 256}  # bytes -> bits


def _resolve_key(raw_key: str) -> bytes:
    """Convert a user-supplied key string to a valid AES key (bytes)."""
    raw_key = raw_key.strip()
    # Try hex decode for exact 32 / 48 / 64 hex chars
    if len(raw_key) in (32, 48, 64) and all(c in "0123456789abcdefABCDEF" for c in raw_key):
        key_bytes = bytes.fromhex(raw_key)
        if len(key_bytes) in VALID_KEY_SIZES:
            return key_bytes
    # Fallback: hash to 32-byte (256-bit) key with SHA-256
    return hashlib.sha256(raw_key.encode()).digest()


def key_bits(raw_key: str) -> int:
    """Return the effective AES key size in bits."""
    return VALID_KEY_SIZES.get(len(_resolve_key(raw_key)), 256)


# ------------------------------------------------------------------ public API

def random_key(bits: int = 256, rng=None) -> str:
    """Generate a cryptographically random AES key as a hex string.

    Args:
        bits: 128, 192, or 256 (default 256).
    Returns:
        Hex-encoded key string.
    """
    n_bytes = {128: 16, 192: 24, 256: 32}.get(bits, 32)
    return secrets.token_hex(n_bytes)


def encrypt(plaintext: str, key: str) -> str:
    """Encrypt *plaintext* with AES-256-CBC.

    Returns a base64-encoded string of  IV (16 bytes) || ciphertext.
    The key is derived via SHA-256 if it is not already a valid hex key.
    """
    key_bytes = _resolve_key(key)
    iv = os.urandom(16)                                   # fresh random IV each call
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    ciphertext = cipher.encrypt(padded)
    blob = iv + ciphertext                                # prepend IV for decryption
    return base64.b64encode(blob).decode("ascii")


def decrypt(ciphertext_b64: str, key: str) -> str:
    """Decrypt an AES-256-CBC ciphertext produced by :func:`encrypt`.

    Args:
        ciphertext_b64: Base64 string (IV prefix || ciphertext).
        key: Same key (hex or passphrase) used for encryption.
    Returns:
        Decoded plaintext string.
    Raises:
        ValueError: On padding / format errors (wrong key).
    """
    key_bytes = _resolve_key(key)
    try:
        blob = base64.b64decode(ciphertext_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 ciphertext: {exc}") from exc
    if len(blob) < 32:
        raise ValueError("Ciphertext too short — must be at least 32 bytes (IV + 1 block).")
    iv, raw_ct = blob[:16], blob[16:]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    try:
        plaintext = unpad(cipher.decrypt(raw_ct), AES.block_size)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Decryption failed — wrong key or corrupted ciphertext: {exc}") from exc
    return plaintext.decode("utf-8")


def key_info(raw_key: str) -> dict:
    """Return human-readable metadata about the derived AES key."""
    key_bytes = _resolve_key(raw_key)
    bits = VALID_KEY_SIZES[len(key_bytes)]
    return {
        "algorithm": f"AES-{bits}-CBC",
        "key_bits": bits,
        "key_bytes": len(key_bytes),
        "key_hex": key_bytes.hex(),
        "mode": "CBC",
        "iv_bytes": 16,
        "block_size_bytes": 16,
        "padding": "PKCS7",
    }
