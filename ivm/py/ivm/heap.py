import dataclasses
import enum
import sys
from typing import Any, ClassVar, Literal, reveal_type, Optional


class Wire:
    other_half: "Wire"
    left_half: "Wire"
    target: Any = None

    def __new__(cls, *args: Any, **kwds: Any) -> "Wire":
        left = object.__new__(cls)
        right = object.__new__(cls)

        left.other_half = right
        left.left_half = left
        right.other_half = left
        right.left_half = left
        return left

    def load_target(self) -> Optional["Port"]:
        port = self.target
        if port is None:
            return None

        assert isinstance(port, Port)
        return port

    def swap_target(self, port: "Port") -> Optional["Port"]:
        old = self.load_target()
        self.target = port
        return old


# Notably, the two references --are the same wire--, but are returned
# as two possible routes to the underlying wire (two sides of the same underlying
# port pointer).  This works because in practice if both sides of a wire
# are "occupied" principally, there is an interaction which can be reduced.
TwoSidedWireReference = tuple[Wire, Wire]

# These two references --are two paris of wires-- allocated side by side,
# unlike TwoSidedWireReference, as they reference to differentiated principal
# ports.
AuxPairWireReference = tuple[Wire, Wire]

class Tag(enum.IntEnum):
    Wire = 1
    Global = 2
    Erase = 3
    ExtVal = 4
    Comb = 5
    ExtFn = 6
    Branch = 7

@dataclasses.dataclass
class Port:
    tag: Tag

    ERASE: "ClassVar[NilaryNodePort]"

@dataclasses.dataclass
class NilaryNodePort(Port):
    pass

    def fork(self) -> "NilaryNodePort":
        return self

    def drop(self) -> None:
        return

@dataclasses.dataclass
class ErasePort(NilaryNodePort):
    tag: Tag = Tag.Erase
Port.ERASE = ErasePort()

@dataclasses.dataclass
class WirePort(NilaryNodePort):
    wire: Wire
    tag: Tag = Tag.Wire

@dataclasses.dataclass
class BinaryNodePort(Port):
    tag: Tag
    target: Wire
    label: str

    def aux(self) -> AuxPairWireReference:
        return self.target, self.target.other_half

@dataclasses.dataclass
class CombPort(BinaryNodePort):
    label: str
    target: Wire
    tag: Tag = Tag.Comb

@dataclasses.dataclass
class BranchPort(BinaryNodePort):
    target: Wire
    tag: Tag = Tag.Branch


@dataclasses.dataclass
class WireHeap:
    wires: list[Wire] = dataclasses.field(default_factory=list)
    free_head: Wire | None = None
    max_size: int = 1024 * 1024

    def alloc_node(self) -> Wire:
        sys.audit("ivm.alloc", self)
        if self.free_head is not None:
            wire = self.free_head
            self.free_head = self.free_head.target
        else:
            sys.audit("ivm.heap", self)
            if len(self.wires) < self.max_size:
                wire = Wire()
                self.wires.append(wire)
            else:
                raise MemoryError(f"WireHeap max_size {self.max_size} exceeded")

        wire.other_half.target = None
        wire.target = None
        return wire

    def free_wire(self, wire: Wire) -> None:
        sys.audit("ivm.free_wire", self)
        wire.target = None
        if wire.other_half.target is not None:
            wire = wire.left_half
            wire.target = self.free_head
            self.free_head = wire

    def new_wire(self) -> TwoSidedWireReference:
        wire = self.alloc_node()
        self.free_wire(wire.other_half)
        return wire, wire

    def new_wires(self) -> tuple[TwoSidedWireReference, TwoSidedWireReference]:
        wire = self.alloc_node()
        return (wire, wire), (wire.other_half, wire.other_half)



