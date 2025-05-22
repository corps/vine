import ctypes
from typing import Any, Iterator

from .port import Port
from .vector import Vector


class Instruction(ctypes.Structure):
    class Union(ctypes.Union):
        class NilaryInstruction(ctypes.Structure):
            _fields_ = [("register", ctypes.c_uint32), ("port", Port)]

            register: int
            port: Port

        class BinaryInstruction(ctypes.Structure):
            _fields_ = [
                ("tag", ctypes.c_uint8),
                ("label", ctypes.c_uint16),
                ("register0", ctypes.c_uint32),
                ("register1", ctypes.c_uint32),
                ("register2", ctypes.c_uint32),
            ]

            tag: int
            label: int
            register0: int
            register1: int
            register2: int

        class InertInstruction(ctypes.Structure):
            _fields_ = [("register0", ctypes.c_uint32), ("register1", ctypes.c_uint32)]

            register0: int
            register1: int

        _fields_ = [
            ("as_nilary", NilaryInstruction),
            ("as_binary", BinaryInstruction),
            ("as_inert", InertInstruction),
        ]

        as_nilary: NilaryInstruction
        as_binary: BinaryInstruction
        as_inert: InertInstruction

    _fields_ = [("tag", ctypes.c_uint8), ("inner", Union)]

    tag: int
    inner: Union

    def unpack(
        self,
    ) -> Union.NilaryInstruction | Union.BinaryInstruction | Union.InertInstruction:
        if self.tag == 1:
            return self.inner.as_nilary
        elif self.tag == 2:
            return self.inner.as_binary
        elif self.tag == 3:
            return self.inner.as_inert
        raise ValueError(f"Unknown tag {self.tag}")

    @classmethod
    def pack(
        cls,
        value: (
            Union.NilaryInstruction | Union.BinaryInstruction | Union.InertInstruction
        ),
    ) -> "Instruction":
        if isinstance(value, cls.Union.NilaryInstruction):
            return cls(tag=1, inner=value)
        elif isinstance(value, cls.Union.BinaryInstruction):
            return cls(tag=2, inner=value)
        elif isinstance(value, cls.Union.InertInstruction):
            return cls(tag=3, inner=value)
        raise ValueError(f"{value} is not a valid instruction")


class Instructions(ctypes.Structure):
    _fields_ = [
        ("next_register", ctypes.c_uint32),
        ("instructions", Vector.for_type(Instruction)),
    ]

    next_register: int
    instructions: Vector[Instruction]

    def new_register(self) -> int:
        result = self.next_register
        self.next_register += 1
        return result

    def __iter__(self) -> Iterator[Instruction]:
        return iter(self.instructions)
