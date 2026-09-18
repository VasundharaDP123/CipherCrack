"""Every cipher must round-trip, and keys must behave like keys."""

import random

import pytest

import ciphers
from ciphers import substitution as sub
from ciphers.alphabet import clean, letters_only, to_indices, to_text

MESSAGE = "Attack at dawn, bring the maps and the lantern!"


@pytest.mark.parametrize("name", ciphers.CIPHER_NAMES)
def test_round_trip(name):
    ciphertext, key = ciphers.encrypt(name, MESSAGE)
    recovered = ciphers.decrypt(name, ciphertext, key)
    if name == "transposition":
        # Transposition works on letters only and pads with X to fill its grid,
        # so it recovers the letters and nothing else.
        assert recovered.startswith(letters_only(MESSAGE))
    else:
        # The others substitute letters in place and pass punctuation and
        # spacing through untouched, so the original comes back verbatim.
        assert recovered == MESSAGE.upper()


@pytest.mark.parametrize("name", ciphers.CIPHER_NAMES)
def test_random_key_is_usable(name):
    key = ciphers.random_key(name)
    ciphertext, _ = ciphers.encrypt(name, MESSAGE, key=key)
    assert ciphertext


def test_unknown_cipher_raises():
    with pytest.raises(ValueError):
        ciphers.get("enigma")


def test_substitution_key_validation():
    assert sub.is_valid_key(sub.random_key())
    assert not sub.is_valid_key("TOO SHORT")
    assert not sub.is_valid_key("A" * 26)          # not a permutation
    with pytest.raises(ValueError):
        sub.encrypt(MESSAGE, "A" * 26)


def test_invert_key_is_an_involution():
    for _ in range(20):
        key = sub.random_key()
        assert sub.invert_key(sub.invert_key(key)) == key


def test_substitution_preserves_spaces():
    key = sub.random_key(random.Random(0))
    ciphertext = sub.encrypt("HELLO WORLD", key)
    assert ciphertext[5] == " "


def test_caesar_brute_force_contains_truth():
    ciphertext = ciphers.caesar.encrypt("ATTACK AT DAWN", 7)
    assert ("ATTACK AT DAWN", 7) in [
        (text, shift) for shift, text in ciphers.caesar.brute_force(ciphertext)
    ]


def test_clean_and_indices_round_trip():
    text = clean("Hello,   World!")
    assert text == "HELLO WORLD"
    assert to_text(to_indices(text)) == text


def test_vigenere_with_repeated_key_is_caesar():
    assert ciphers.vigenere.encrypt("HELLO", "AAAAA") == "HELLO"
    assert ciphers.vigenere.encrypt("HELLO", "BBBBB") == ciphers.caesar.encrypt("HELLO", 1)
