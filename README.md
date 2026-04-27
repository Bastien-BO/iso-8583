# iso-8583

Pure-Python ISO-8583 message packing and unpacking. No dependencies.

## Quick start

```python
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType
from iso_8583 import FieldSpec, Message

spec = {
    2: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19),
    3: FieldSpec(LengthType.FIXED, FieldFormat.N, 6),
    4: FieldSpec(LengthType.FIXED, FieldFormat.N, 12),
    41: FieldSpec(LengthType.FIXED, FieldFormat.ANSP, 8),
}

msg = Message(spec, MTI.AUTHORISATION_REQUEST)
msg[2] = "4242424242424242"
msg[3] = "000000"
msg[4] = "000000001000"
msg[41] = "TERM0001"

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MTI)

print(msg2[2])   # 4242424242424242
print(msg2[41])  # TERM0001
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

## Subfields

```python
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType
from iso_8583 import FieldSpec, SubFieldSpec, Message

spec = {
    119: FieldSpec(
        LengthType.LLLVAR, FieldFormat.B, 255,
        subfields={
            "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.AN, 1),
            "0009": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 8),
            "0011": SubFieldSpec(LengthType.LLVAR, FieldFormat.N, 19),
        },
    ),
}

msg = Message(spec, MTI.AUTHORISATION_REQUEST)
msg[119] = {"0001": "A", "0009": "HELLO", "0011": "1234567890"}

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MTI)
print(msg2[119])
# {'0001': 'A', '0009': 'HELLO', '0011': '1234567890'}
```

For ASCII TLV subfields (tag 2 chars + length 2 chars + value), use `TlvFieldSpec`:

```python
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType
from iso_8583 import TlvFieldSpec, SubFieldSpec, Message

spec = {
    47: TlvFieldSpec(
        LengthType.LLVAR, FieldFormat.ANSP, 99,
        subfields={
            "T1": SubFieldSpec(LengthType.LLVAR, FieldFormat.ANSP, 10),
            "T2": SubFieldSpec(LengthType.LLVAR, FieldFormat.N, 8),
        },
    ),
}

msg = Message(spec, MTI.AUTHORISATION_REQUEST)
msg[47] = {"T1": "HELLO", "T2": "12345678"}

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MTI)
print(msg2[47])
# {'T1': 'HELLO', 'T2': '12345678'}
```

Repeatable subfields accept a list:

```python
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType
from iso_8583 import FieldSpec, SubFieldSpec, Message

spec = {
    56: FieldSpec(
        LengthType.LLVAR, FieldFormat.B, 99,
        subfields={
            "0001": SubFieldSpec(LengthType.FIXED, FieldFormat.N, 4),
            "0023": SubFieldSpec(
                LengthType.FIXED, FieldFormat.ANSP, 8,
                repeatable=True,
            ),
        },
    ),
}

msg = Message(spec, MTI.AUTHORISATION_REQUEST)
msg[56] = {"0001": "1234", "0023": ["ENTRY-01", "ENTRY-02"]}

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MTI)
print(msg2[56]["0023"])
# ['ENTRY-01', 'ENTRY-02']
```

## Partial unpack

Stops at the first error and returns what was read:

```python
from iso_8583.fixed_formats import FieldFormat
from iso_8583.extendable_formats import MTI, LengthType
from iso_8583 import FieldSpec, Message

full_spec = {
    2: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19),
    3: FieldSpec(LengthType.FIXED, FieldFormat.N, 6),
}
partial_spec = {
    2: FieldSpec(LengthType.LLVAR, FieldFormat.N, 19),
}

msg = Message(full_spec, MTI.AUTHORISATION_REQUEST)
msg[2] = "4242424242424242"
msg[3] = "000000"
raw = msg.pack()

result, error = Message.unpack_partial(partial_spec, raw, mti_class=MTI)
print(result[2])  # 4242424242424242
print(error)      # bit 3: present in bitmap but not in spec
```

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
from iso_8583 import FieldSpec, Message

class MyLengthType(Enum):
    FIXED = (0, None)
    LLVAR = (1, 99)
    LLLVAR = (1, 255)
    LL2VAR = (2, 999)

    def __init__(self, prefix_bytes, max_field_length):
        self.prefix_bytes = prefix_bytes
        self.max_field_length = max_field_length

class MyMTI(int, Enum):
    AUTH = 0x0100

spec = {
    2: FieldSpec(MyLengthType.LLVAR, FieldFormat.N, 19),
    60: FieldSpec(MyLengthType.LL2VAR, FieldFormat.ANSP, 999),
}

msg = Message(spec, MyMTI.AUTH)
msg[2] = "4242424242424242"
msg[60] = "HELLO WORLD"

raw = msg.pack()
msg2 = Message.unpack(spec, raw, mti_class=MyMTI)
print(msg2[2])   # 4242424242424242
print(msg2[60])  # HELLO WORLD
```