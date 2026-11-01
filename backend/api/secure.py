"""Secure Vault API — AES-256 and RSA Hybrid endpoints (Tasks 1 & 2).

Mounted at  /api  alongside the existing routes blueprint.
"""

from flask import Blueprint, jsonify, request

from ciphers import aes_cipher, rsa_hybrid

secure = Blueprint("secure", __name__, url_prefix="/api")

MAX_TEXT    = 50_000
MAX_PEM_LEN = 12_000   # RSA-4096 PEM is ~3.2 KB; 12 KB is very generous


def _fail(message, status=400):
    return jsonify({"error": message}), status


# ===================================================================== AES-256

@secure.get("/aes/keygen")
def aes_keygen():
    """Generate a random AES key.

    Query params:
        bits  128 | 192 | 256  (default 256)
    Returns:
        { key: <hex>, bits: <int> }
    """
    try:
        bits = int(request.args.get("bits", 256))
    except ValueError:
        return _fail("'bits' must be an integer")
    if bits not in (128, 192, 256):
        return _fail("'bits' must be 128, 192, or 256")
    key = aes_cipher.random_key(bits=bits)
    return jsonify({"key": key, "bits": bits})


@secure.post("/aes/encrypt")
def aes_encrypt():
    """Encrypt plaintext with AES-256-CBC.

    Body JSON:
        plaintext  str  (required)
        key        str  hex key or passphrase (required)
    Returns:
        { ciphertext, algorithm, key_bits, mode, padding, ... }
    """
    payload   = request.get_json(silent=True) or {}
    plaintext = (payload.get("plaintext") or "").strip()
    key       = (payload.get("key")       or "").strip()
    if not plaintext:
        return _fail("'plaintext' is required")
    if not key:
        return _fail("'key' is required")
    if len(plaintext) > MAX_TEXT:
        return _fail(f"'plaintext' exceeds {MAX_TEXT} character limit")
    try:
        ciphertext = aes_cipher.encrypt(plaintext, key)
        info       = aes_cipher.key_info(key)
    except Exception as exc:
        return _fail(str(exc))
    return jsonify({
        "ciphertext":        ciphertext,
        "plaintext_length":  len(plaintext),
        "ciphertext_length": len(ciphertext),
        **info,
    })


@secure.post("/aes/decrypt")
def aes_decrypt():
    """Decrypt AES-256-CBC ciphertext produced by /api/aes/encrypt.

    Body JSON:
        ciphertext  str  base64 blob (required)
        key         str  same key used for encryption (required)
    Returns:
        { plaintext, algorithm, key_bits, ... }
    """
    payload    = request.get_json(silent=True) or {}
    ciphertext = (payload.get("ciphertext") or "").strip()
    key        = (payload.get("key")        or "").strip()
    if not ciphertext:
        return _fail("'ciphertext' is required")
    if not key:
        return _fail("'key' is required")
    try:
        plaintext = aes_cipher.decrypt(ciphertext, key)
        info      = aes_cipher.key_info(key)
    except Exception as exc:
        return _fail(str(exc))
    return jsonify({"plaintext": plaintext, **info})


# ============================================================= RSA Hybrid

@secure.post("/hybrid/keygen")
def hybrid_keygen():
    """Generate an RSA key pair for the hybrid system.

    Body JSON:
        bits  1024 | 2048 | 4096  (default 2048, recommended)
    Returns:
        { public_key, private_key, bits, public_exponent, modulus_bits, ... }
    """
    payload = request.get_json(silent=True) or {}
    try:
        bits = int(payload.get("bits", 2048))
    except (TypeError, ValueError):
        return _fail("'bits' must be an integer")
    if bits not in (1024, 2048, 4096):
        return _fail("'bits' must be 1024, 2048, or 4096")
    try:
        result = rsa_hybrid.generate_rsa_keypair(bits=bits)
    except Exception as exc:
        return _fail(str(exc))
    return jsonify(result)


@secure.post("/hybrid/encrypt")
def hybrid_encrypt():
    """Hybrid-encrypt a message: AES-256 data + RSA-sealed session key.

    Body JSON:
        plaintext   str  (required)
        public_key  str  RSA public key PEM (required)
    Returns:
        bundle dict { rsa_encrypted_key, iv, aes_ciphertext, aes_key_bits,
                      rsa_bits, message_length, aes_key_hex_prefix }
    """
    payload    = request.get_json(silent=True) or {}
    plaintext  = (payload.get("plaintext")  or "").strip()
    public_key = (payload.get("public_key") or "").strip()
    if not plaintext:
        return _fail("'plaintext' is required")
    if not public_key:
        return _fail("'public_key' is required")
    if len(plaintext) > MAX_TEXT:
        return _fail(f"'plaintext' exceeds {MAX_TEXT} character limit")
    if len(public_key) > MAX_PEM_LEN:
        return _fail("'public_key' is unexpectedly long")
    try:
        bundle = rsa_hybrid.encrypt(plaintext, public_key)
    except Exception as exc:
        return _fail(str(exc))
    return jsonify(bundle)


@secure.post("/hybrid/decrypt")
def hybrid_decrypt():
    """Hybrid-decrypt a bundle produced by /api/hybrid/encrypt.

    Body JSON:
        bundle       dict  (required — as returned by /hybrid/encrypt)
        private_key  str   RSA private key PEM (required)
    Returns:
        { plaintext, aes_key_hex, aes_key_bits, message_length }
    """
    payload     = request.get_json(silent=True) or {}
    bundle      = payload.get("bundle")
    private_key = (payload.get("private_key") or "").strip()
    if not bundle or not isinstance(bundle, dict):
        return _fail("'bundle' is required and must be an object")
    if not private_key:
        return _fail("'private_key' is required")
    if len(private_key) > MAX_PEM_LEN:
        return _fail("'private_key' is unexpectedly long")
    try:
        result = rsa_hybrid.decrypt(bundle, private_key)
    except Exception as exc:
        return _fail(str(exc))
    return jsonify(result)
