"""
Tests for binary subfields, TLV subfields, repeatable, and partial recovery.
"""

import pytest

from iso_8583.exceptions import FieldValidationError
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import LengthType
from iso_8583.iso_8583 import FieldSpec, SubFieldSpec, TlvFieldSpec, Message

from tests.conftest import full_coverage_spec, SampleMTI, make_msg


class TestBinarySubfields:
    """
    LLVAR parent with b1 subfield length prefix.
    """

    def test_roundtrip(self):
        msg = make_msg()
        msg[100] = {
            "0001": "123456",
            "0002": "Hello!",
            "0003": b"\x01\x02\x03\x04",
        }
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[100]["0001"] == "123456"
        assert msg2[100]["0002"] == "Hello!"
        assert msg2[100]["0003"] == b"\x01\x02\x03\x04"

    def test_partial_subfields(self):
        """
        Only some subfields present on the wire.
        """
        msg = make_msg()
        msg[100] = {"0001": "123456", "0003": b"\x01\x02\x03\x04"}
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert "0001" in msg2[100]
        assert "0002" not in msg2[100]
        assert "0003" in msg2[100]

    def test_unknown_subfield_on_validate(self):
        msg = make_msg()
        with pytest.raises(FieldValidationError, match="subfield 9999 unknown"):
            msg[100] = {"0001": "123456", "9999": "bad"}


class TestLLLVARSubfields:
    """
    LLLVAR parent with b2 subfield length prefix.
    """

    def test_roundtrip(self):
        msg = make_msg()
        msg[101] = {
            "0001": "123456",
            "0002": "ABCDEFGH",
            "0003": "1234567",
        }
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[101]["0001"] == "123456"
        assert msg2[101]["0002"] == "ABCDEFGH"
        assert msg2[101]["0003"] == "1234567"

    def test_odd_n_subfield(self):
        """
        FIXED N 7 subfield strips the leading zero on unpack.
        """
        msg = make_msg()
        msg[101] = {"0001": "123456", "0003": "4047672"}
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[101]["0003"] == "4047672"

    def test_length_prefix_is_two_bytes(self):
        msg = make_msg()
        msg[101] = {"0001": "123456"}
        raw = msg.pack()
        # Subfield on wire: tag(2) + length(2) + value(3 bcd bytes)
        # 0001 0003 123456 → 7 bytes total
        # LLLVAR prefix(2) = 0007
        # Find the subfield: should contain 00 03 (2-byte length)
        body = raw[18:]  # skip MTI + 16-byte bitmap
        assert b"\x00\x01\x00\x03" in body


class TestTlvSubfields:
    """
    TLV ASCII subfields.
    """

    def test_roundtrip(self):
        msg = make_msg()
        msg[102] = {"08": "TEST", "30": "5"}
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[102] == {"08": "TEST", "30": "5"}

    def test_unknown_tag_on_unpack(self):
        spec_full = {
            47: TlvFieldSpec(
                LengthType.LLVAR,
                FieldFormat.ANSP,
                99,
                subfields={
                    "AA": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 10),
                    "BB": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 10),
                },
            ),
        }
        spec_partial = {
            47: TlvFieldSpec(
                LengthType.LLVAR,
                FieldFormat.ANSP,
                99,
                subfields={
                    "AA": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 10),
                },
            ),
        }
        msg = Message(spec_full, SampleMTI.AUTH_REQ)
        msg[47] = {"AA": "HELLO", "BB": "WORLD"}
        raw = msg.pack()

        with pytest.raises(FieldValidationError, match="subfield BB unknown"):
            Message.unpack(spec_partial, raw, mti_class=SampleMTI)

    def test_tlv_overflow(self):
        spec = {
            44: TlvFieldSpec(
                LengthType.LLVAR,
                FieldFormat.ANSP,
                10,
                subfields={
                    "AA": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 20),
                },
            ),
        }
        msg = Message(spec, SampleMTI.AUTH_REQ)
        msg[44] = {"AA": "WAY TOO LONG VALUE"}
        with pytest.raises(FieldValidationError, match="TLV total length"):
            msg.pack()


class TestRepeatable:
    """
    Subfields with repeatable=True.
    """

    def test_binary_repeatable_roundtrip(self):
        msg = make_msg()
        msg[101] = {
            "0001": "123456",
            "0023": ["AAAAAAAA", "BBBBBBBB", "CCCCCCCC"],
        }
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[101]["0023"] == ["AAAAAAAA", "BBBBBBBB", "CCCCCCCC"]

    def test_tlv_repeatable_roundtrip(self):
        msg = make_msg()
        msg[102] = {"20": ["FIRST", "SECOND", "THIRD"]}
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[102]["20"] == ["FIRST", "SECOND", "THIRD"]

    def test_repeatable_validate_list(self):
        """
        The list comprehension branch in _validate_subfields.
        """
        msg = make_msg()
        msg[101] = {"0001": "123456", "0023": ["ABCDEFGH"]}
        assert msg[101]["0023"] == ["ABCDEFGH"]

    def test_invalid_item_in_repeatable_list(self):
        msg = make_msg()
        with pytest.raises(FieldValidationError):
            msg[101] = {"0001": "123456", "0023": ["ABCDEFGH", "\t\t\t\t\t\t\t\t"]}


class TestSubfieldOverflow:
    def test_binary_total_exceeds_max(self):
        spec = {
            100: FieldSpec(
                LengthType.LLVAR,
                FieldFormat.B,
                5,
                subfields={
                    "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 10),
                },
            ),
        }
        msg = Message(spec, SampleMTI.AUTH_REQ)
        msg[100] = {"0001": "1234567890"}
        with pytest.raises(FieldValidationError, match="subfields total length"):
            msg.pack()


class TestUnknownSubfieldOnUnpack:
    """
    Unknown binary subfield tag produces partial recovery.
    """

    PACK_SPEC = {
        56: FieldSpec(
            LengthType.LLVAR,
            FieldFormat.B,
            99,
            subfields={
                "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 6),
                "0099": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 2),
            },
        ),
    }
    UNPACK_SPEC = {
        56: FieldSpec(
            LengthType.LLVAR,
            FieldFormat.B,
            99,
            subfields={
                "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 6),
            },
        ),
    }

    def test_strict_raises(self):
        msg = Message(self.PACK_SPEC, SampleMTI.AUTH_REQ)
        msg[56] = {"0001": "123456", "0099": "99"}
        raw = msg.pack()

        with pytest.raises(FieldValidationError, match="bit 56"):
            Message.unpack(self.UNPACK_SPEC, raw, mti_class=SampleMTI)

    def test_partial_recovers_read_subfields(self):
        msg = Message(self.PACK_SPEC, SampleMTI.AUTH_REQ)
        msg[56] = {"0001": "123456", "0099": "99"}
        raw = msg.pack()

        result, err = Message.unpack_partial(
            self.UNPACK_SPEC,
            raw,
            mti_class=SampleMTI,
        )
        assert result[56] == {"0001": "123456"}
        assert "subfield 0099 unknown" in str(err)
