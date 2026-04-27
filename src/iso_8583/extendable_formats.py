"""
ISO-8583 barebone formats

Can be extended or replace by any similar structure with values of your choice
"""

from enum import Enum


class MTI(int, Enum):
    """
    ISO-8583 Basic Message Type Indicator.
    """

    AUTHORISATION_REQUEST = 0x0100
    AUTHORISATION_RESPONSE = 0x0110
    AUTHORISATION_ADVICE = 0x0120
    AUTHORISATION_ADVICE_REPEAT = 0x0121
    ACQUIRER_RESPONSE_TO_AUTHORIZATION_ADVICE = 0x0130
    ACQUIRER_FINANCIAL_REQUEST = 0x0200
    AUTHORISATION_REQUEST_RESPONSE = 0x0210
    ACQUIRER_RESPONSE = 0x0220
    ACQUIRER_FINANCIAL_ADVICE_REPEAT = 0x0221
    ACQUIRER_RESPONSE_TO_FINANCIAL_ADVICE = 0x0230
    BATCH_UPLOAD = 0x0320
    BATCH_UPLOAD_RESPONSE = 0x0330
    ACQUIRER_REVERSAl_REQUEST = 0x0400
    ACQUIRER_REVERSAl_ADVICE = 0x0420
    ACQUIRER_REVERSAL_ADVICE_RESPONSE = 0x0430
    BATCH_SETTLEMENT_RESPONSE = 0x0510
    NETWORK_MANAGEMENT_REQUEST = 0x0800
    NETWORK_MANAGEMENT_RESPONSE = 0x0810
    NETWORK_MANAGEMENT_ADVICE = 0x0820


class LengthType(Enum):
    """
    ISO-8583 length prefix type.

    Each member defines:
        prefix_bytes: Number of bytes in the binary length prefix.
            0 means no prefix (fixed-length field).
        max_field_length: Maximum field length allowed by the prefix.
            None for fixed-length fields.
    """

    FIXED = (0, None)
    LLVAR = (1, 99)
    LLLVAR = (2, 1000)

    def __init__(self, prefix_bytes: int, max_field_length: int | None):
        self.prefix_bytes = prefix_bytes
        self.max_field_length = max_field_length
