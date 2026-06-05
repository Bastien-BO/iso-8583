"""
Tests for FieldSpec: validation, encoding, pack/unpack round-trips.
"""

import pytest

from iso_8583.exceptions import FieldValidationError
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import LengthType
from iso_8583.iso_8583 import FieldSpec, Message, encode_bcd, decode_bcd

from tests.conftest import (
    full_coverage_spec, SampleMTI, make_msg,
    valid_value, invalid_value,
    ALL_BITS, FIXED_BITS, FIXED_NO_PAD_BITS, VAR_BITS,
    CHARSET_BITS, ODD_BCD_BITS, MIN_LENGTH_BITS,
)


class TestEncodeBcd:

    def test_even_length(self):
        assert encode_bcd("1234") == b"\x12\x34"

    def test_odd_length_pads(self):
        assert encode_bcd("123") == b"\x01\x23"

    def test_single_digit(self):
        assert encode_bcd("5") == b"\x05"


class TestDecodeBcd:

    def test_normal(self):
        assert decode_bcd(b"\x01\x23", 3) == "123"

    def test_full_bytes(self):
        assert decode_bcd(b"\x12\x34", 4) == "1234"

    def test_uppercase(self):
        assert decode_bcd(b"\xAB\xCD", 4) == "ABCD"


class TestNormalize:

    def test_fixed_n_is_padded(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.N, 6)
        assert spec.validate("42") == "000042"

    def test_var_n_not_padded(self):
        spec = FieldSpec(LengthType.LLVAR, FieldFormat.N, 19)
        assert spec.validate("42") == "42"

    def test_fixed_a_not_padded(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.A, 4)
        with pytest.raises(FieldValidationError):
            spec.validate("AB")  # too short, not padded


class TestCharset:

    @pytest.mark.parametrize("bit", CHARSET_BITS)
    def test_invalid_chars_rejected(self, bit):
        spec = full_coverage_spec[bit]
        with pytest.raises(FieldValidationError, match="invalid char"):
            make_msg()[bit] = invalid_value(spec.format, spec.max_length)

    def test_non_string_rejected(self):
        msg = make_msg()
        with pytest.raises(FieldValidationError, match="requires str"):
            msg[4] = 123456  # bit 4 is FIXED N

    def test_bytes_rejected_on_ascii(self):
        msg = make_msg()
        with pytest.raises(FieldValidationError, match="requires str"):
            msg[2] = b"ABCD"  # bit 2 is FIXED A

    def test_invalid_value_raises_for_binary(self):
        with pytest.raises(ValueError, match="no invalid value"):
            invalid_value(FieldFormat.B, 4)


class TestFixedLength:

    @pytest.mark.parametrize("bit", FIXED_NO_PAD_BITS)
    def test_too_short(self, bit):
        spec = full_coverage_spec[bit]
        with pytest.raises(FieldValidationError):
            make_msg()[bit] = valid_value(spec.format, spec.max_length - 1)

    @pytest.mark.parametrize("bit", FIXED_BITS)
    def test_too_long(self, bit):
        spec = full_coverage_spec[bit]
        with pytest.raises(FieldValidationError):
            make_msg()[bit] = valid_value(spec.format, spec.max_length + 1)


class TestVarLength:

    @pytest.mark.parametrize("bit", VAR_BITS)
    def test_too_long(self, bit):
        spec = full_coverage_spec[bit]
        with pytest.raises(FieldValidationError):
            make_msg()[bit] = valid_value(spec.format, spec.max_length + 1)


class TestMinLength:

    @pytest.mark.parametrize("bit", MIN_LENGTH_BITS)
    def test_below_min(self, bit):
        spec = full_coverage_spec[bit]
        with pytest.raises(FieldValidationError):
            make_msg()[bit] = valid_value(spec.format, spec.min_length - 1)

    @pytest.mark.parametrize("bit", MIN_LENGTH_BITS)
    def test_at_min(self, bit):
        spec = full_coverage_spec[bit]
        msg = make_msg()
        msg[bit] = valid_value(spec.format, spec.min_length)



class TestFieldSpecInit:

    def test_fixed_n_min_length_relaxed(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.N, 6)
        assert spec.min_length == 1

    def test_fixed_a_min_length_equals_max(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.A, 4)
        assert spec.min_length == 4

    def test_fixed_z_min_length_equals_max(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.Z, 8)
        assert spec.min_length == 8

    def test_explicit_min_length(self):
        spec = FieldSpec(LengthType.LLVAR, FieldFormat.N, 19, min_length=5)
        assert spec.min_length == 5

    def test_exceeds_capacity_raises(self):
        with pytest.raises(ValueError, match="exceeds"):
            FieldSpec(LengthType.LLVAR, FieldFormat.A, 100)  # max 99


class TestValueEncode:

    def test_bcd(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.N, 4)
        assert spec.value_encode("1234") == b"\x12\x34"

    def test_ascii(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.A, 4)
        assert spec.value_encode("ABCD") == b"ABCD"

    def test_raw_bytes(self):
        spec = FieldSpec(LengthType.FIXED, FieldFormat.B, 4)
        data = b"\x01\x02\x03\x04"
        assert spec.value_encode(data) == data


class TestValidValues:

    @pytest.mark.parametrize("bit", ALL_BITS)
    def test_accepted(self, bit):
        spec = full_coverage_spec[bit]
        msg = make_msg()
        value = valid_value(spec.format, spec.max_length)
        msg[bit] = value
        assert msg[bit] == value


class TestRoundTrip:

    @pytest.mark.parametrize("bit", ALL_BITS)
    def test_pack_unpack(self, bit):
        spec = full_coverage_spec[bit]
        msg = make_msg()
        msg[bit] = valid_value(spec.format, spec.max_length)
        msg2 = Message.unpack(
            full_coverage_spec, msg.pack(), mti_class=SampleMTI,
        )
        assert msg2[bit] == msg[bit]


class TestOddBcd:

    @pytest.mark.parametrize("bit", ODD_BCD_BITS)
    def test_roundtrip(self, bit):
        msg = make_msg()
        msg[bit] = "12345"
        msg2 = Message.unpack(
            full_coverage_spec, msg.pack(), mti_class=SampleMTI,
        )
        assert msg2[bit] == "12345"


class TestFormatBoundaries:

    def test_ans_excludes_space(self):
        assert " " not in FieldFormat.ANS.allowed_chars

    def test_anp_excludes_punct(self):
        assert "!" not in FieldFormat.ANP.allowed_chars

    def test_ansp_includes_space_and_punct(self):
        chars = FieldFormat.ANSP.allowed_chars
        assert " " in chars
        assert "!" in chars
        assert "A" in chars
        assert "1" in chars


class TestFieldValidationErrorPartial:

    def test_with_partial(self):
        partial = {"0001": "123"}
        err = FieldValidationError("broken", partial=partial)
        assert err.partial == {"0001": "123"}
        assert str(err) == "broken"
