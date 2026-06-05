"""
Tests for Message: bitmap, pack/unpack, MTI, partial unpack.
"""

import pytest

from iso_8583.exceptions import FieldValidationError, FieldOutOfRange
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import LengthType, MTI
from iso_8583.iso_8583 import FieldSpec, Message

from tests.conftest import (
    full_coverage_spec,
    SampleMTI,
    make_msg,
)


class TestExtendableMTI:
    """
    Verify that the real MTI from extendable_formats works with Message.
    """

    @pytest.mark.parametrize("mti", list(MTI))
    def test_roundtrip(self, mti):
        spec = {2: FieldSpec(LengthType.FIXED, FieldFormat.A, 4)}
        msg = Message(spec, mti)
        msg[2] = "ABCD"
        msg2 = Message.unpack(spec, msg.pack(), mti_class=MTI)
        assert msg2._mti == mti


class TestSetItem:
    def test_unknown_bit(self):
        msg = make_msg()
        with pytest.raises(KeyError, match="bit 999"):
            msg[999] = "test"

    def test_non_dict_for_subfield_field(self):
        msg = make_msg()
        with pytest.raises(FieldValidationError, match="expected dict"):
            msg[100] = "not a dict"

    def test_validation_error_includes_bit(self):
        msg = make_msg()
        with pytest.raises(FieldValidationError, match="bit 2"):
            msg[2] = "1234"  # digits not valid for format A


class TestSetRaw:
    def test_bypasses_validation(self):
        msg = make_msg()
        msg.set_raw(2, b"\x01\x02\x03\x04")
        assert msg[2] == b"\x01\x02\x03\x04"

    def test_unknown_bit(self):
        msg = make_msg()
        with pytest.raises(KeyError, match="bit 999"):
            msg.set_raw(999, b"\x01")


class TestFields:
    def test_returns_copy(self):
        msg = make_msg()
        msg[2] = "ABCD"
        fields = msg.fields()
        assert fields == {2: "ABCD"}
        fields[99] = "extra"
        assert 99 not in msg.fields()


class TestBitmap:
    def test_set_bit(self):
        result = Message.set_bit_into_bitmap("0000000000000000", 2)
        assert int(result, 16) & (1 << 2)

    def test_set_bit_inverted(self):
        result = Message.set_bit_into_bitmap(
            "0000000000000000",
            2,
            inverted=True,
        )
        assert int(result, 16) & (1 << 62)

    def test_out_of_range_64(self):
        with pytest.raises(FieldOutOfRange, match="out of range"):
            Message.set_bit_into_bitmap("0000000000000000", 65)

    def test_out_of_range_128(self):
        with pytest.raises(FieldOutOfRange, match="out of range"):
            Message.set_bit_into_bitmap(
                "00000000000000000000000000000000",
                129,
            )


class TestMessagePack:
    def test_8_byte_bitmap(self):
        msg = make_msg()
        msg[2] = "ABCD"
        raw = msg.pack()
        # MTI(2) + 8-byte bitmap + data
        assert len(raw) == 2 + 8 + 4

    def test_16_byte_bitmap(self):
        msg = make_msg()
        msg[2] = "ABCD"
        msg[100] = {
            "0001": "123456",
            "0003": b"\x01\x02\x03\x04",
        }
        raw = msg.pack()
        # MTI(2) + 16-byte bitmap + data
        assert raw[2] & 0x80  # bit 1 set in primary bitmap


class TestMessageUnpack:
    def test_from_hex_string(self):
        msg = make_msg()
        msg[2] = "ABCD"
        raw = msg.pack()
        msg2 = Message.unpack(
            full_coverage_spec,
            raw.hex(),
            mti_class=SampleMTI,
        )
        assert msg2[2] == "ABCD"

    def test_without_mti_class(self):
        msg = make_msg()
        msg[2] = "ABCD"
        raw = msg.pack()
        msg2 = Message.unpack(full_coverage_spec, raw)
        assert msg2[2] == "ABCD"
        assert msg2._mti == 0x0100

    @pytest.mark.parametrize("mti", list(SampleMTI))
    def test_mti_preserved(self, mti):
        msg = Message(full_coverage_spec, mti)
        msg[2] = "ABCD"
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2._mti == mti

    def test_unknown_mti_raises(self):
        raw = b"\x02\x00" + b"\x00" * 8
        with pytest.raises(ValueError):
            Message.unpack(full_coverage_spec, raw, mti_class=SampleMTI)

    def test_bit_not_in_spec_raises(self):
        partial_spec = {k: v for k, v in full_coverage_spec.items() if k != 2}
        msg = make_msg()
        msg[2] = "ABCD"
        with pytest.raises(FieldValidationError, match="bit 2"):
            Message.unpack(partial_spec, msg.pack(), mti_class=SampleMTI)


class TestMultiField:
    def test_many_fields_roundtrip(self):
        msg = make_msg()
        msg[2] = "ABCD"
        msg[3] = b"\x01\x02\x03\x04"
        msg[4] = "111111"
        msg[5] = "    "
        msg[8] = "ABCD1234"
        msg[14] = "1234567890"
        msg[32] = "12345"
        msg2 = Message.unpack(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert msg2[2] == "ABCD"
        assert msg2[3] == b"\x01\x02\x03\x04"
        assert msg2[4] == "111111"
        assert msg2[5] == "    "
        assert msg2[8] == "ABCD1234"
        assert msg2[14] == "1234567890"
        assert msg2[32] == "12345"


class TestUnpackPartial:
    def test_recovers_fields_before_error(self):
        pack_spec = {
            2: FieldSpec(LengthType.FIXED, FieldFormat.A, 4),
            7: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19),
        }
        unpack_spec = {
            2: FieldSpec(LengthType.FIXED, FieldFormat.A, 4),
        }
        msg = Message(pack_spec, SampleMTI.AUTH_REQ)
        msg[2] = "ABCD"
        msg[7] = "1234567890"
        raw = msg.pack()

        result, err = Message.unpack_partial(
            unpack_spec,
            raw,
            mti_class=SampleMTI,
        )
        assert result[2] == "ABCD"
        assert 7 not in result.fields()
        assert "bit 7" in str(err)

    def test_no_error_returns_none(self):
        msg = make_msg()
        msg[2] = "ABCD"
        result, err = Message.unpack_partial(
            full_coverage_spec,
            msg.pack(),
            mti_class=SampleMTI,
        )
        assert result[2] == "ABCD"
        assert err is None

    def test_partial_without_subfield_recovery(self):
        """
        Error on a non-subfield field has no partial dict.
        """
        pack_spec = {
            2: FieldSpec(LengthType.FIXED, FieldFormat.N, 6),
            7: FieldSpec(LengthType.FIXED, FieldFormat.N, 6),
        }
        unpack_spec = {
            2: FieldSpec(LengthType.FIXED, FieldFormat.N, 6),
        }
        msg = Message(pack_spec, SampleMTI.AUTH_REQ)
        msg[2] = "111111"
        msg[7] = "222222"
        raw = msg.pack()

        result, err = Message.unpack_partial(
            unpack_spec,
            raw,
            mti_class=SampleMTI,
        )
        assert result[2] == "111111"
        assert 7 not in result.fields()
        assert "bit 7" in str(err)
