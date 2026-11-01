"""Simple Hybrid Encryption System — RSA-2048 + AES-256-CBC  (Task 2).

How it works (identical to TLS record layer):
  Encrypt
  -------
  Step 1  Generate a random AES-256 session key  (32 secret bytes).
  Step 2  Encrypt the plaintext with AES-256-CBC using that session key.
  Step 3  Encrypt the session key itself with RSA-2048 OAEP (public key).
  Step 4  Return a bundle  { rsa_encrypted_key | iv | aes_ciphertext }.

  Decrypt
  -------
  Step 1  Recover the AES session key: RSA-OAEP decrypt with private key.
  Step 2  Decrypt the AES ciphertext with the recovered session key + IV.
  Step 3  Return plaintext.

Why hybrid?
  RSA can only encrypt data up to (key_size_bytes − 42) bytes with OAEP.
  For RSA-2048 that is 214 bytes — far too small for a real message.
  AES-256-CBC handles arbitrary-length data at hardware speed.
  Combining both gives us the security of RSA with the speed of AES.
"""

import base64
import os
import secrets
import time

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad


# ------------------------------------------------------------------ key pair

def generate_rsa_keypair(bits: int = 2048) -> dict:
    """Generate a fresh RSA key pair.

    Args:
        bits: Key size in bits. Typical values: 1024, 2048, 4096.
              2048 is the current NIST recommendation for long-term security.
    Returns:
        dict with PEM-encoded keys and human-readable metadata.
    """
    t0 = time.perf_counter()
    key = RSA.generate(bits)
    elapsed = round(time.perf_counter() - t0, 3)

    pub = key.publickey()
    return {
        "public_key":          pub.export_key("PEM").decode(),
        "private_key":         key.export_key("PEM").decode(),
        "bits":                bits,
        "public_exponent":     int(key.e),
        "modulus_bits":        key.size_in_bits(),
        "modulus_hex_prefix":  hex(int(key.n))[:66] + "…",
        "key_gen_seconds":     elapsed,
    }


# ------------------------------------------------------------------ encrypt

def encrypt(plaintext: str, public_key_pem: str) -> dict:
    """Hybrid-encrypt *plaintext* with the given RSA public key.

    Returns a JSON-serialisable bundle dict:
        {
          "rsa_encrypted_key":  <base64>,   # AES session key, RSA-OAEP sealed
          "iv":                 <base64>,   # AES IV (16 random bytes)
          "aes_ciphertext":     <base64>,   # Message ciphertext (AES-256-CBC)
          "aes_key_bits":       256,
          "rsa_bits":           2048,
          "message_length":     <int>,
          "aes_key_hex_prefix": <str>,      # First 8 bytes shown for demo
        }
    """
    # Step 1 — ephemeral AES-256 session key + IV
    aes_key = secrets.token_bytes(32)       # 256-bit, cryptographically random
    iv      = os.urandom(16)               # fresh IV for every encryption

    # Step 2 — encrypt the message with AES-256-CBC + PKCS7 padding
    aes_cipher  = AES.new(aes_key, AES.MODE_CBC, iv)
    padded      = pad(plaintext.encode("utf-8"), AES.block_size)
    aes_ct      = aes_cipher.encrypt(padded)

    # Step 3 — seal the AES session key with RSA-2048 OAEP (SHA-256 hash)
    rsa_key     = RSA.import_key(public_key_pem)
    rsa_cipher  = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256)
    rsa_sealed  = rsa_cipher.encrypt(aes_key)

    return {
        "rsa_encrypted_key":  base64.b64encode(rsa_sealed).decode(),
        "iv":                 base64.b64encode(iv).decode(),
        "aes_ciphertext":     base64.b64encode(aes_ct).decode(),
        "aes_key_bits":       256,
        "rsa_bits":           rsa_key.size_in_bits(),
        "message_length":     len(plaintext),
        "aes_key_hex_prefix": aes_key[:8].hex() + "…",
    }


# ------------------------------------------------------------------ decrypt

def decrypt(bundle: dict, private_key_pem: str) -> dict:
    """Hybrid-decrypt a bundle produced by :func:`encrypt`.

    Args:
        bundle:          dict from :func:`encrypt`.
        private_key_pem: RSA private key (PEM).
    Returns:
        dict with ``plaintext`` and decryption metadata.
    Raises:
        ValueError: Wrong key or corrupted bundle.
    """
    try:
        rsa_sealed  = base64.b64decode(bundle["rsa_encrypted_key"])
        iv          = base64.b64decode(bundle["iv"])
        aes_ct      = base64.b64decode(bundle["aes_ciphertext"])
    except (KeyError, Exception) as exc:
        raise ValueError(f"Invalid bundle — missing or corrupt field: {exc}") from exc

    # Step 1 — recover AES session key via RSA private key
    try:
        rsa_key    = RSA.import_key(private_key_pem)
        rsa_cipher = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256)
        aes_key    = rsa_cipher.decrypt(rsa_sealed)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"RSA decryption failed — wrong private key? ({exc})") from exc

    # Step 2 — decrypt message with recovered AES key
    try:
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        plaintext  = unpad(aes_cipher.decrypt(aes_ct), AES.block_size).decode("utf-8")
    except (ValueError, KeyError) as exc:
        raise ValueError(f"AES decryption failed: {exc}") from exc

    return {
        "plaintext":      plaintext,
        "aes_key_hex":    aes_key.hex(),
        "aes_key_bits":   len(aes_key) * 8,
        "message_length": len(plaintext),
    }
