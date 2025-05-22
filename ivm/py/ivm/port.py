import ctypes
from enum import IntEnum


from .addr import Addr
from .ext import ExtVal


class Tag(IntEnum):
    Wire = 1
    Global = 2
    Erase = 3
    ExtVal = 4
    Comb = 5
    ExtFn = 6
    Branch = 7


class Port(ctypes.c_uint64):
    @classmethod
    def ERASE(cls) -> "Port":
        return Port(Tag.Erase.value)

    @classmethod
    def from_tag_label_pointer(cls, tag: int, label: int, pointer: int):
        return cls(label << 48 | pointer | tag)

    @property
    def tag(self) -> int:
        return self.value & 0b111

    @property
    def addr(self) -> Addr:
        return Addr(self.value & 0x0000_FFFF_FFFF_FFF8)

    @property
    def label(self) -> int:
        return self.value >> 48

    def aux(self) -> tuple[Addr, Addr]:
        addr = self.addr
        return addr, addr.other_half()

    @classmethod
    def new_wire(cls, addr: Addr) -> "Port":
        return cls.from_tag_label_pointer(Tag.Wire, 0, addr.value)

    @classmethod
    def new_ext_val(cls, ext_val: ExtVal) -> "Port":
        return Port.from_buffer(bytes(ext_val))
