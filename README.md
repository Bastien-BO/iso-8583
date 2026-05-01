# iso-8583

Pure-Python ISO-8583 message packing and unpacking. No dependencies.

## Quick start

```python
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType
from iso_8583 import FieldSpec, SubFieldSpec, TlvFieldSpec, Message

spec = {
    # Regular field
    2: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19, min_length=8),
    # ASCII TLV subfields
    47: TlvFieldSpec(
        LengthType.LLVAR, FieldFormat.ANSP, 99,
        subfields={
            "T1": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 10),
            "T2": SubFieldSpec(LengthType.LLVAR, FieldFormat.N, 8),
        },
    ),
    # Binary subfields (with a repeatable one)
    59: FieldSpec(
        LengthType.LLLVAR, FieldFormat.B, 255,
        subfields={
            "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.AN, 1),
            "0009": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 8, min_length=1),
            "0010": SubFieldSpec(LengthType.FIXED, FieldFormat.B, 4),
            "0023": SubFieldSpec(
                LengthType.FIXED, FieldFormat.ANSP, 8,
                repeatable=True,
            ),
        },
    ),
}

msg = Message(spec, MTI.AUTHORISATION_REQUEST)
msg[2] = "4242424242424242"
msg[47] = {"T1": "HELLO", "T2": "12345678"}
msg[59] = {
    "0001": "A",
    "0009": "HELLO",
    "0010": b"\xAB\xCD\xEF\x12",
    "0023": ["ENTRY-01", "ENTRY-02"],
}

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MTI)

print(msg2[2])            # 4242424242424242
print(msg2[47]["T1"])     # HELLO
print(msg2[59]["0001"])   # A
print(msg2[59]["0010"])   # b'\xab\xcd\xef\x12'
print(msg2[59]["0023"])   # ['ENTRY-01', 'ENTRY-02']

# Partial unpack stops at the first error and returns what was read
partial_spec = {2: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19)}
msg3, error = Message.unpack_partial(partial_spec, raw, mti_class=MTI)
print(msg3[2])  # 4242424242424242
print(error)    # bit 47: present in bitmap but not in spec
```

## Field formats

| Format | Characters | Wire |
|--------|-----------|------|
| `A` | Letters | ASCII |
| `B` / `ANSB` | Any bytes | Raw |
| `N` | Digits | BCD |
| `P` | Space | ASCII |
| `S` | Punctuation | ASCII |
| `Z` | Digits + D, F | BCD |
| `AN` | Letters + digits | ASCII |
| `ANP` | Letters + digits + space | ASCII |
| `ANS` | Letters + digits + punctuation | ASCII |
| `ANSP` | Letters + digits + punctuation + space | ASCII |

## Length types

| Type | Prefix | Max |
|------|--------|-----|
| `FIXED` | 0 bytes | — |
| `LLVAR` | 1 byte | 99 |
| `LLLVAR` | 2 bytes | 1000 |

## Custom MTI

```python
from enum import Enum
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import LengthType
from iso_8583 import FieldSpec, Message

class MyMTI(int, Enum):
    SALE = 0x0200
    SALE_RESPONSE = 0x0210
    REVERSAL = 0x0400

spec = {2: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19)}

msg = Message(spec, MyMTI.SALE)
msg[2] = "4242424242424242"

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MyMTI)
print(msg2._mti)  # MyMTI.SALE
```

## Custom LengthType

```python
from enum import Enum
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI
from iso_8583 import FieldSpec, Message

class MyLengthType(Enum):
    FIXED = (0, None)
    LLVAR = (1, 99)
    LLLVAR = (1, 255)
    LL2VAR = (2, 999)

    def __init__(self, prefix_bytes, max_field_length):
        self.prefix_bytes = prefix_bytes
        self.max_field_length = max_field_length

spec = {
    2: FieldSpec(MyLengthType.LLVAR, FieldFormat.N, 19),
    60: FieldSpec(MyLengthType.LL2VAR, FieldFormat.ANSP, 999),
}

msg = Message(spec, MTI.AUTHORISATION_REQUEST)
msg[2] = "4242424242424242"
msg[60] = "HELLO WORLD"

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MTI)
print(msg2[2])   # 4242424242424242
print(msg2[60])  # HELLO WORLD
```
