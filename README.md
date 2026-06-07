<div align="center">

# ISO-8583
 
**Pure Python ISO-8583 message packing and unpacking. No dependencies.**

[![codecov](https://codecov.io/gh/Bastien-BO/iso-8583/branch/main/graph/badge.svg)](https://codecov.io/gh/Bastien-BO/iso-8583)
[![Lint](https://github.com/Bastien-BO/iso-8583/actions/workflows/lint.yml/badge.svg)](https://github.com/Bastien-BO/iso-8583/actions/workflows/lint.yml)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![PyPI](https://img.shields.io/pypi/v/iso-8583-toolbox)
![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/Bastien-BO/iso-8583/main/pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests](https://github.com/Bastien-BO/iso-8583/actions/workflows/tests.yml/badge.svg)](https://github.com/Bastien-BO/iso-8583/actions/workflows/tests.yml)

</div>


## Features
 
- Pure Python, zero runtime dependencies
- Pack and unpack ISO-8583 messages
- Fixed and variable-length fields (`LLVAR`, `LLLVAR`)
- Many field formats: ASCII, BCD, and raw binary
- Nested subfields, including ASCII TLV and repeatable subfields
- Partial unpacking that stops at the first error
- Bring-your-own `MTI` and `LengthType` enums

## Table of contents
 
- [Installation](#installation)
- [Quick start](#quick-start)
- [Field formats](#field-formats)
- [Length types](#length-types)
- [Subfields](#subfields)
- [Partial unpack](#partial-unpack)
- [Custom MTI](#custom-mti)
- [Custom LengthType](#custom-lengthtype)
- [License](#license)

## Installation
 
```bash
uv add iso-8583-toolbox
```
 
Or with pip:
 
```bash
pip install iso-8583-toolbox
```
 
The package installs as `iso-8583-toolbox` but is imported as `iso_8583`:
 
```python
from iso_8583 import Message
```
 
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
msg2 = Message.unpack(spec, raw)
 
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
msg2 = Message.unpack(spec, raw)
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
msg2 = Message.unpack(spec, raw)
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
msg2 = Message.unpack(spec, raw)
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
 
result, error = Message.unpack_partial(partial_spec, raw)
print(result[2])  # 4242424242424242
print(error)      # bit 3: present in bitmap but not in spec
```
 
## Custom MTI
 
Pass `mti_class` to `unpack` to get the MTI back as your own enum:
 
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
msg2 = Message.unpack(spec, raw)
print(msg2[2])   # 4242424242424242
print(msg2[60])  # HELLO WORLD
```
 
## License
 
See [LICENSE](LICENSE).
