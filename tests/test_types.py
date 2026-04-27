"""
Tests for FieldFormat, LengthType, MTI and exception classes.
"""

import pytest

from iso_8583.exceptions import FieldValidationError, FieldOutOfRange
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType


class TestFieldFormat:
    def test_member_count(self):
        # ANSB is an alias of B, so 10 unique members.
        assert len(FieldFormat) == 10

    def test_ansb_is_alias_of_b(self):
        assert FieldFormat.ANSB is FieldFormat.B

    @pytest.mark.parametrize(
        "name_wire",
        [
            ("A", "ascii"),
            ("B", "raw"),
            ("N", "bcd"),
            ("P", "ascii"),
            ("S", "ascii"),
            ("Z", "bcd"),
            ("AN", "ascii"),
            ("ANP", "ascii"),
            ("ANS", "ascii"),
            ("ANSP", "ascii"),
        ],
    )
    def test_wire_format(self, name_wire):
        name, wire = name_wire
        assert FieldFormat[name].wire_format == wire

    @pytest.mark.parametrize("name", ["B", "ANSB"])
    def test_no_charset_for_binary(self, name):
        assert FieldFormat[name].allowed_chars is None

    @pytest.mark.parametrize(
        "name",
        [
            "A",
            "N",
            "P",
            "S",
            "Z",
            "AN",
            "ANP",
            "ANS",
            "ANSP",
        ],
    )
    def test_charset_not_none(self, name):
        assert FieldFormat[name].allowed_chars is not None

    def test_ansp_includes_space_and_punct(self):
        chars = FieldFormat.ANSP.allowed_chars
        assert " " in chars
        assert "!" in chars
        assert "A" in chars
        assert "1" in chars

    def test_ans_excludes_space(self):
        assert " " not in FieldFormat.ANS.allowed_chars

    def test_anp_excludes_punct(self):
        assert "!" not in FieldFormat.ANP.allowed_chars


class TestLengthType:
    def test_fixed(self):
        assert LengthType.FIXED.prefix_bytes == 0
        assert LengthType.FIXED.max_field_length is None

    def test_llvar(self):
        assert LengthType.LLVAR.prefix_bytes == 1
        assert LengthType.LLVAR.max_field_length == 99

    def test_lllvar(self):
        assert LengthType.LLLVAR.prefix_bytes == 2
        assert LengthType.LLLVAR.max_field_length == 1000

    def test_member_count(self):
        assert len(LengthType) == 3


class TestMTI:
    def test_auth_request(self):
        assert MTI.AUTHORISATION_REQUEST == 0x0100

    def test_network_management(self):
        assert MTI.NETWORK_MANAGEMENT_REQUEST == 0x0800

    def test_all_are_int(self):
        for mti in MTI:
            assert isinstance(mti, int)

    def test_member_count(self):
        assert len(MTI) == 19


class TestFieldValidationError:
    def test_message(self):
        err = FieldValidationError("test error")
        assert str(err) == "test error"
        assert err.partial is None

    def test_with_partial(self):
        partial = {"0001": "123"}
        err = FieldValidationError("broken", partial=partial)
        assert err.partial == {"0001": "123"}
        assert str(err) == "broken"

    def test_is_value_error(self):
        assert issubclass(FieldValidationError, ValueError)


class TestFieldOutOfRange:
    def test_message(self):
        err = FieldOutOfRange("too high")
        assert str(err) == "too high"

    def test_is_value_error(self):
        assert issubclass(FieldOutOfRange, ValueError)
