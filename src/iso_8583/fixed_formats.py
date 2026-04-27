"""
ISO-8583 barebone formats
"""

import string
from enum import Enum


class FieldFormat(Enum):
    """
    ISO-8583 field character format.

    Each member defines:
        allowed_chars: Set of valid characters for input validation.
            None for binary fields.
        wire_format: Encoding strategy for serialization.
            'ascii' for text fields, 'bcd' for numeric, 'raw' for binary.
    """

    A = (frozenset(string.ascii_letters), "ascii")
    B = (None, "raw")
    N = (frozenset(string.digits), "bcd")
    P = (frozenset(" "), "ascii")
    S = (frozenset(string.punctuation), "ascii")
    Z = (  # ISO 7813 format
        frozenset(string.digits + "DF"),
        "bcd",
    )
    AN = (
        frozenset(string.ascii_letters + string.digits),
        "ascii",
    )
    ANP = (
        frozenset(string.ascii_letters + string.digits + " "),
        "ascii",
    )
    ANS = (
        frozenset(string.ascii_letters + string.digits + string.punctuation),
        "ascii",
    )
    ANSB = (None, "raw")
    ANSP = (
        frozenset(string.ascii_letters + string.digits + string.punctuation + " "),
        "ascii",
    )

    def __init__(self, allowed_chars, wire_format):
        self.allowed_chars = allowed_chars
        self.wire_format = wire_format
