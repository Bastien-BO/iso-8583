"""
Shared fixtures and helpers for the ISO-8583 test suite.
"""

from enum import Enum

from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import LengthType
from iso_8583.iso_8583 import FieldSpec, SubFieldSpec, TlvFieldSpec, Message


class SampleMTI(int, Enum):
    """
    Minimal MTI enum for tests.
    """

    AUTH_REQ = 0x0100
    AUTH_RESP = 0x0110
    AUTH_ADVICE = 0x0120


# Every FieldFormat × LengthType combination, plus edge cases.
full_coverage_spec = {
    # FIXED × each format
    2: FieldSpec(LengthType.FIXED, FieldFormat.A, 4),
    3: FieldSpec(LengthType.FIXED, FieldFormat.B, 4),
    4: FieldSpec(LengthType.FIXED, FieldFormat.N, 6),
    5: FieldSpec(LengthType.FIXED, FieldFormat.P, 4),
    6: FieldSpec(LengthType.FIXED, FieldFormat.S, 4),
    7: FieldSpec(LengthType.FIXED, FieldFormat.Z, 16),
    8: FieldSpec(LengthType.FIXED, FieldFormat.AN, 8),
    9: FieldSpec(LengthType.FIXED, FieldFormat.ANP, 6),
    10: FieldSpec(LengthType.FIXED, FieldFormat.ANS, 8),
    11: FieldSpec(LengthType.FIXED, FieldFormat.ANSP, 10),
    # LLVAR × each format
    12: FieldSpec(LengthType.LLVAR, FieldFormat.A, 20),
    13: FieldSpec(LengthType.LLVAR, FieldFormat.B, 50),
    14: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19),
    15: FieldSpec(LengthType.LLVAR, FieldFormat.P, 20),
    16: FieldSpec(LengthType.LLVAR, FieldFormat.S, 20),
    17: FieldSpec(LengthType.LLVAR, FieldFormat.Z, 19),
    18: FieldSpec(LengthType.LLVAR, FieldFormat.AN, 30),
    19: FieldSpec(LengthType.LLVAR, FieldFormat.ANP, 40),
    20: FieldSpec(LengthType.LLVAR, FieldFormat.ANS, 40),
    21: FieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 40),
    # LLLVAR × each format
    22: FieldSpec(LengthType.LLLVAR, FieldFormat.A, 120),
    23: FieldSpec(LengthType.LLLVAR, FieldFormat.B, 255),
    24: FieldSpec(LengthType.LLLVAR, FieldFormat.N, 100),
    25: FieldSpec(LengthType.LLLVAR, FieldFormat.P, 100),
    26: FieldSpec(LengthType.LLLVAR, FieldFormat.S, 100),
    27: FieldSpec(LengthType.LLLVAR, FieldFormat.Z, 100),
    28: FieldSpec(LengthType.LLLVAR, FieldFormat.AN, 200),
    29: FieldSpec(LengthType.LLLVAR, FieldFormat.ANP, 200),
    30: FieldSpec(LengthType.LLLVAR, FieldFormat.ANS, 255),
    31: FieldSpec(LengthType.LLLVAR, FieldFormat.ANSP, 255),
    # Odd-length BCD
    32: FieldSpec(LengthType.FIXED, FieldFormat.N, 5),
    33: FieldSpec(LengthType.LLVAR, FieldFormat.N, 5),
    34: FieldSpec(LengthType.LLLVAR, FieldFormat.N, 5),
    # Min length
    35: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19, min_length=5),
    36: FieldSpec(LengthType.LLVAR, FieldFormat.B, 50, min_length=8),
    37: FieldSpec(LengthType.LLLVAR, FieldFormat.ANSP, 255, min_length=10),
    # Binary subfields (LLVAR parent, b1 length)
    100: FieldSpec(
        LengthType.LLVAR,
        FieldFormat.B,
        99,
        subfields={
            "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 6),
            "0002": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 20),
            "0003": SubFieldSpec(LengthType.FIXED, FieldFormat.B, 4),
        },
    ),
    # Binary subfields (LLLVAR parent, b2 length)
    101: FieldSpec(
        LengthType.LLLVAR,
        FieldFormat.B,
        255,
        subfields={
            "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 6),
            "0002": SubFieldSpec(LengthType.FIXED, FieldFormat.ANSP, 8),
            "0003": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 7),
            "0023": SubFieldSpec(
                LengthType.FIXED,
                FieldFormat.ANSP,
                8,
                repeatable=True,
            ),
        },
    ),
    # TLV ASCII subfields
    102: TlvFieldSpec(
        LengthType.LLVAR,
        FieldFormat.ANSP,
        99,
        subfields={
            "08": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 8),
            "20": SubFieldSpec(
                LengthType.LLVAR,
                FieldFormat.ANSP,
                20,
                repeatable=True,
            ),
            "30": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 1),
        },
    ),
}

# Bit lists for parametrized tests

FIXED_BITS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 32]
# FIXED N auto-pads, so shorter values are accepted.
FIXED_NO_PAD_BITS = [2, 3, 5, 6, 7, 8, 9, 10, 11]
VAR_BITS = [
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    33,
    34,
    35,
    36,
    37,
]
ALL_BITS = FIXED_BITS + VAR_BITS
ODD_BCD_BITS = [32, 33, 34]
MIN_LENGTH_BITS = [35, 36, 37]
# Bits with charset validation (exclude B: 3, 13, 23, 36).
CHARSET_BITS = [b for b in ALL_BITS if b not in (3, 13, 23, 36)]


# Value helpers


def valid_value(fmt, length):
    """
    Return a value accepted by the given format and length.
    """
    if fmt is FieldFormat.B:
        return b"\xab" * length
    if fmt is FieldFormat.N:
        return "1" * length
    if fmt is FieldFormat.P:
        return " " * length
    if fmt is FieldFormat.S:
        return "!" * length
    if fmt is FieldFormat.Z:
        return "1" * length
    # A, AN, ANP, ANS, ANSP all accept ascii letters.
    return "A" * length


def invalid_value(fmt, length):
    """
    Return a value rejected by the given format's charset.

    Raises ValueError for formats without a clear invalid case.
    """
    if fmt is FieldFormat.N:
        return "X" * length
    if fmt is FieldFormat.A:
        return "1" * length
    if fmt is FieldFormat.P:
        return "X" * length
    if fmt is FieldFormat.S:
        return "A" * length
    if fmt is FieldFormat.Z:
        return "X" * length
    if fmt is FieldFormat.AN:
        return "!" * length
    if fmt is FieldFormat.ANP:
        return "!" * length
    if fmt is FieldFormat.ANS:
        return " " * length
    if fmt is FieldFormat.ANSP:
        return "\t" * length
    raise ValueError(f"no invalid value for {fmt.name}")


def make_msg():
    """
    Shortcut to create a Message with the full coverage spec.
    """
    return Message(full_coverage_spec, SampleMTI.AUTH_REQ)
