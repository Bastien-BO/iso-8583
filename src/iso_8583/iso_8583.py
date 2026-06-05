"""
ISO-8583 message core:
    field specification, validation, pack/unpack.
"""

from binascii import unhexlify

from iso_8583.exceptions import FieldValidationError, FieldOutOfRange
from iso_8583.fixed_formats import FieldFormat


def encode_bcd(value: str) -> bytes:
    """Encode a digit string to BCD (2 digits per byte).

    Pads with a leading zero if odd number of digits.
    Example: "123" -> "0123" -> b'\\x01\\x23'
    """
    if len(value) % 2:
        value = "0" + value
    return bytes.fromhex(value)


def decode_bcd(data: bytes, positions: int) -> str:
    """Decode BCD bytes to digit string.

    Example: b'\\x01\\x23', 3 -> "123"
    """
    return data.hex().upper()[-positions:]


class FieldSpec:
    """ISO-8583 field specification.

    Agnostic of LengthType implementation: any object with
    prefix_bytes and max_field_length attributes will work.
    """

    # pylint: disable=too-many-arguments too-many-positional-arguments

    def __init__(
        self,
        length_type,
        fmt,
        max_length,
        min_length=0,
        subfields=None,
    ):
        self.length_type = length_type
        self.format = fmt
        self.max_length = max_length
        self.subfields = subfields  # dict[str, SubFieldSpec] | None
        self.repeatable = False

        self.tag_size = 0
        if subfields:
            first_tag = next(iter(subfields))
            self.tag_size = len(first_tag) // 2

        if length_type.prefix_bytes == 0 and min_length == 0:
            # FIXED N values are right-justified and left-filled
            # with zeros by _normalize, so shorter values are valid.
            if fmt is FieldFormat.N:
                self.min_length = 1
            else:
                self.min_length = max_length
        else:
            self.min_length = min_length

        if length_type.max_field_length and max_length > length_type.max_field_length:
            raise ValueError(
                f"max_length {max_length} exceeds "
                f"capacity ({length_type.max_field_length})"
            )

    def validate(self, value):
        """Validate and normalize value against this field specification.

        Returns the normalized value (FIXED N values are zero-padded).
        """
        value = self._normalize(value)
        if self.subfields and isinstance(value, dict):
            return self._validate_subfields(value)
        self._validate_charset(value)
        self._validate_length(value)
        return value

    def _normalize(self, value):
        """Pad FIXED N values with leading zeros to max_length."""
        if (
            self.format is FieldFormat.N
            and self.length_type.prefix_bytes == 0
            and isinstance(value, str)
        ):
            return value.zfill(self.max_length)
        return value

    def _validate_subfields(self, value):
        result = {}
        for tag, sub_value in value.items():
            if tag not in self.subfields:
                raise FieldValidationError(f"subfield {tag} unknown")
            spec = self.subfields[tag]
            if spec.repeatable and isinstance(sub_value, list):
                result[tag] = [spec.validate(item) for item in sub_value]
            else:
                result[tag] = spec.validate(sub_value)
        return result

    def _validate_charset(self, value):
        if self.format.allowed_chars is None:
            return
        if not isinstance(value, str):
            raise FieldValidationError(f"format {self.format.name} requires str")
        for c in value:
            if c not in self.format.allowed_chars:
                raise FieldValidationError(f"invalid char '{c}' for {self.format.name}")

    def _validate_length(self, value):
        if len(value) < self.min_length:
            raise FieldValidationError(f"length {len(value)} < min {self.min_length}")
        if len(value) > self.max_length:
            raise FieldValidationError(f"length {len(value)} > max {self.max_length}")

    def value_encode(self, value: str | bytes) -> bytes:
        """Encode value to wire format."""
        if self.format.wire_format == "bcd":
            return encode_bcd(value)
        if isinstance(value, bytes):
            return value
        return value.encode("ascii")

    def pack(self, value: str | bytes | dict) -> bytes:
        """Serialize value with its length prefix."""
        if self.subfields and isinstance(value, dict):
            encoded = self._pack_subfields(value)
            positions = len(encoded)
            if positions > self.max_length:
                raise FieldValidationError(
                    f"subfields total length {positions} > max {self.max_length}"
                )
        else:
            positions = len(value)
            encoded = self.value_encode(value)

        if self.length_type.prefix_bytes == 0:
            return encoded
        prefix = positions.to_bytes(self.length_type.prefix_bytes, "big")
        return prefix + encoded

    def _pack_subfields(self, value: dict) -> bytes:
        """
        Serialize subfields in binary format.

        Each subfield: tag (b2) + length (same width as parent prefix)
        + value.
        """
        length_size = self.length_type.prefix_bytes
        parts = []
        for tag in sorted(value):
            spec = self.subfields[tag]
            items = value[tag]
            if not (spec.repeatable and isinstance(items, list)):
                items = [items]
            for item in items:
                value_bytes = spec.value_encode(item)
                tag_bytes = bytes.fromhex(tag)
                length_bytes = len(value_bytes).to_bytes(
                    length_size,
                    "big",
                )
                parts.append(tag_bytes + length_bytes + value_bytes)
        return b"".join(parts)

    def unpack(self, buffer: bytes, offset: int) -> tuple:
        """
        Read and decode a field from buffer at offset.

        Returns (value, new_offset).
        """
        if self.length_type.prefix_bytes > 0:
            end = offset + self.length_type.prefix_bytes
            positions = int.from_bytes(buffer[offset:end], "big")
            offset = end
        else:
            positions = self.max_length

        if self.format.wire_format == "bcd":
            byte_len = (positions + 1) // 2
        else:
            byte_len = positions

        data = buffer[offset : offset + byte_len]
        offset += byte_len

        return self.decode_value(data, positions), offset

    def decode_value(self, data: bytes, positions: int) -> str | bytes | dict:
        """
        Decode raw bytes into a Python value based on format.
        """
        if self.subfields:
            return self._unpack_subfields(data)
        if self.format.wire_format == "bcd":
            return decode_bcd(data, positions)
        if self.format.wire_format == "ascii":
            return data.decode("ascii")
        return data

    def _unpack_subfields(self, data: bytes) -> dict:
        """
        Read subfields in binary format.

        Each subfield: tag (b2) + length (same width as parent prefix)
        + value.

        On error, attaches the subfields read so far to the exception
        as `e.partial`, so callers can recover what was decoded.
        """
        length_size = self.length_type.prefix_bytes
        result = {}
        offset = 0
        try:
            while offset < len(data):
                tag = data[offset : offset + self.tag_size].hex().upper()
                offset += self.tag_size
                if tag not in self.subfields:
                    raise FieldValidationError(f"subfield {tag} unknown")
                spec = self.subfields[tag]

                byte_len = int.from_bytes(
                    data[offset : offset + length_size],
                    "big",
                )
                offset += length_size
                if spec.format.wire_format == "bcd":
                    # FIXED N with odd max_length is padded to an even
                    # number of digits on the wire. Strip the pad on read.
                    if spec.length_type.prefix_bytes == 0 and spec.max_length % 2 == 1:
                        positions = spec.max_length
                    else:
                        positions = byte_len * 2
                else:
                    positions = byte_len

                value_data = data[offset : offset + byte_len]
                offset += byte_len
                value = spec.decode_value(value_data, positions)

                if spec.repeatable:
                    result.setdefault(tag, []).append(value)
                else:
                    result[tag] = value
        except FieldValidationError as e:
            raise FieldValidationError(str(e), partial=result) from e
        return result


class SubFieldSpec(FieldSpec):
    """
    Subfield within a parent ISO-8583 field.

    Inherits validation and pack/unpack from FieldSpec.
    Adds repeatable support, cannot have subfields.
    """

    # pylint: disable=too-many-arguments too-many-positional-arguments

    def __init__(
        self,
        length_type,
        fmt,
        max_length,
        min_length=0,
        repeatable=False,
    ):
        super().__init__(length_type, fmt, max_length, min_length)
        self.repeatable = repeatable


class TlvFieldSpec(FieldSpec):
    """
    Field with TLV-structured subfields in ASCII format.

    Each subfield is serialized as: tag(2 ASCII) + length(2 ASCII) + value.

    For the default binary subfield format (tag b2 + length b1),
    use FieldSpec with subfields directly.
    """

    TAG_SIZE = 2
    LENGTH_SIZE = 2

    def pack(self, value: dict) -> bytes:
        """
        Serialize ASCII TLV subfields with the parent length prefix.
        """
        parts = []
        for tag in sorted(value):
            spec = self.subfields[tag]
            items = value[tag]
            if not (spec.repeatable and isinstance(items, list)):
                items = [items]
            for item in items:
                value_bytes = spec.value_encode(item)
                length_str = str(len(value_bytes)).zfill(self.LENGTH_SIZE)
                parts.append(
                    tag.encode("ascii") + length_str.encode("ascii") + value_bytes
                )

        encoded = b"".join(parts)
        if len(encoded) > self.max_length:
            raise FieldValidationError(
                f"TLV total length {len(encoded)} > max {self.max_length}"
            )
        prefix = len(encoded).to_bytes(
            self.length_type.prefix_bytes,
            "big",
        )
        return prefix + encoded

    def unpack(self, buffer: bytes, offset: int) -> tuple:
        """
        Read ASCII TLV subfields from buffer.

        On error, attaches the subfields read so far to the exception
        as `e.partial`.
        """
        end = offset + self.length_type.prefix_bytes
        total_length = int.from_bytes(buffer[offset:end], "big")
        offset = end
        stop = offset + total_length

        result = {}
        try:
            while offset < stop:
                tag = buffer[offset : offset + self.TAG_SIZE].decode("ascii")
                offset += self.TAG_SIZE
                length = int(buffer[offset : offset + self.LENGTH_SIZE].decode("ascii"))
                offset += self.LENGTH_SIZE

                if tag not in self.subfields:
                    raise FieldValidationError(f"subfield {tag} unknown")

                spec = self.subfields[tag]
                data = buffer[offset : offset + length]
                offset += length
                value = spec.decode_value(data, spec.max_length)

                if spec.repeatable:
                    result.setdefault(tag, []).append(value)
                else:
                    result[tag] = value
        except FieldValidationError as e:
            raise FieldValidationError(str(e), partial=result) from e

        return result, offset


class Message:
    """
    ISO-8583 message with validation on assignment.

    Agnostic of MTI implementation: any int-like object will work.
    """

    def __init__(self, spec: dict[int, FieldSpec], mti):
        self._spec = spec
        self._mti = mti
        self._data: dict = {}

    def __setitem__(self, bit: int, value: str | bytes | dict) -> None:
        if bit not in self._spec:
            raise KeyError(f"bit {bit} unknown")
        if self._spec[bit].subfields and not isinstance(value, dict):
            raise FieldValidationError(f"bit {bit}: expected dict for subfields")
        try:
            self._data[bit] = self._spec[bit].validate(value)
        except FieldValidationError as e:
            raise FieldValidationError(f"bit {bit}: {e}") from e

    def set_raw(self, bit: int, value: bytes) -> None:
        """
        Set a pre-built raw value, bypassing subfield validation.
        """
        if bit not in self._spec:
            raise KeyError(f"bit {bit} unknown")
        self._data[bit] = value

    def __getitem__(self, bit: int) -> str | bytes | dict:
        return self._data[bit]

    def fields(self) -> dict:
        """
        Return all fields and their values.
        """
        return dict(self._data)

    @classmethod
    def set_bit_into_bitmap(
        cls,
        bitmap: str,
        bit: int,
        inverted: bool = False,
    ) -> str:
        """
        Set a bit in the bitmap (hex string representation).

        :param bitmap: Bitmap in b16 str format
        :param bit: Bit position to be set
        :param inverted: Invert the bitmap reading direction
        """
        max_field_size: int = (len(bitmap) // 2) * 8
        position: int = bit
        if inverted:
            position = max_field_size - bit
        if bit > max_field_size:
            raise FieldOutOfRange(f"bitmap editor: field {bit} is out of range")
        return (str(hex(int(bitmap, 16) | (1 << position)))[2:]).zfill(len(bitmap))

    def pack(self) -> bytes:
        """
        Serialize the full message: MTI + bitmap + fields.

        The bitmap is 8 bytes by default. When a bit above 64 is used,
        it grows to 16 bytes and bit 1 is set to signal the extension.
        """
        # Build the bitmap as a hex string.
        needs_extension = any(bit > 64 for bit in self._data)
        if needs_extension:
            bitmap = "80000000000000000000000000000000"  # 16 bytes, bit 1 set
        else:
            bitmap = "0000000000000000"  # 8 bytes

        for bit in self._data:
            bitmap = self.set_bit_into_bitmap(bitmap, bit, inverted=True)

        # Assemble MTI + bitmap + every field value.
        result = int(self._mti).to_bytes(2, "big")
        result += unhexlify(bitmap)
        for bit in sorted(self._data):
            result += self._spec[bit].pack(self._data[bit])
        return result

    @classmethod
    def unpack(
        cls,
        spec: dict,
        raw: str | bytes,
        mti_class=None,
    ) -> "Message":
        """
        Reconstruct a message from raw bytes or hex string.

        Raises FieldValidationError on any field error.
        """
        msg, _ = cls._unpack(spec, raw, mti_class, strict=True)
        return msg

    @classmethod
    def unpack_partial(
        cls,
        spec: dict,
        raw: str | bytes,
        mti_class=None,
    ) -> tuple["Message", FieldValidationError | None]:
        """
        Unpack as much as possible, return (message, error or None).

        Unlike `unpack`, this stops at the first error and returns
        the partially-filled message alongside the error. Useful
        for debugging malformed payloads from a real server.
        """
        return cls._unpack(spec, raw, mti_class, strict=False)

    @classmethod
    def _unpack(
        cls,
        spec: dict,
        raw: str | bytes,
        mti_class,
        strict: bool,
    ) -> tuple["Message", FieldValidationError | None]:
        """
        Internal unpack. If strict, raises on error; else returns it.
        """
        if isinstance(raw, str):
            raw = bytes.fromhex(raw)

        # Read the MTI (first 2 bytes).
        mti_value = int.from_bytes(raw[0:2], "big")
        if mti_class is not None:
            mti_value = mti_class(mti_value)

        # Read the bitmap (8 or 16 bytes depending on bit 1).
        primary = int.from_bytes(raw[2:10], "big")
        if primary & (
            1 << 63
        ):  # Logical AND, first bit set length of first field (bitmap)
            bitmap = int.from_bytes(raw[2:18], "big")
            offset = 18
        else:
            bitmap = primary << 64
            offset = 10

        # Read every field listed in the bitmap (skip bit 1).
        msg = cls(spec, mti_value)
        for bit in range(2, 129):
            if not bitmap & (1 << (128 - bit)):
                continue
            try:
                if bit not in spec:
                    raise FieldValidationError("present in bitmap but not in spec")
                value, offset = spec[bit].unpack(raw, offset)
            except FieldValidationError as e:
                error = FieldValidationError(f"bit {bit}: {e}")
                if strict:
                    raise error from e
                # Recover whatever subfields were read before the error.
                if e.partial:
                    msg._data[bit] = e.partial
                return msg, error
            msg._data[bit] = value

        return msg, None
