import ctypes

from .instruction import Instructions
from .vector import Vector


class LabelSet(ctypes.Structure):
    _fields_ = [("cap", ctypes.c_uint16), ("bits", Vector.for_type(ctypes.c_uint64))]

    cap: int = 0
    bits: list[ctypes.c_uint64]

    def add(self, label: int):
        if label >= 2**16 - 1:
            raise ValueError(f"Label must be less than 2^16-1")
        self.cap = max(self.cap, label + 1)
        index = label >> 6
        bit = label & 63
        for _ in range(index - len(self.bits) + 1):
            self.bits.append(ctypes.c_uint64(0))

        self.bits[index].value |= 1 << bit

    def has(self, label: int) -> bool:
        if label >= self.cap:
            return False
        index = label >> 6
        bit = label & 63
        return self.bits[index].value & (1 << bit) != 0

    def extend(self, other: "LabelSet"):
        self.cap = max(self.cap, other.cap)
        for _ in range(len(other.bits) - len(self.bits)):
            self.bits.append(ctypes.c_uint64(0))
        for i, b in enumerate(other.bits):
            self.bits[i].value |= b.value


class Global(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.POINTER(ctypes.c_char)),
        ("labels", LabelSet),
        ("instructions", Instructions),
        ("flag", ctypes.c_uint64),
    ]

    name: bytes
    labels: LabelSet
    instructions: Instructions
    flag: int
