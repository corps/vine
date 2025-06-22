import dataclasses
import enum
from typing import Any, ClassVar, Optional, Callable


# TODO: Move these into distinct file
@dataclasses.dataclass
class SpanInfo:
    head_span: tuple[int, tuple[int, int]]
    row_span: tuple[int, int]
    col_span: tuple[int, int]


@dataclasses.dataclass
class SourceInfo(SpanInfo):
    head_span: tuple[int, tuple[int, int]]
    containing_net_name: str
    containing_net_source: list[str]
    row_span: tuple[int, int]
    col_span: tuple[int, int]


Trace = SourceInfo | SpanInfo


class Wire:
    other_half: "Wire"
    left_half: "Wire"
    target: "Wire | Port | None" = None

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
        if not isinstance(port, Port):
            return None

        return port

    def swap_target(self, port: "Port") -> Optional["Port"]:
        old = self.load_target()
        self.target = port
        return old


TwoSidedWireReference = tuple[Wire, Wire]
AuxPairWireReference = tuple[Wire, Wire]


class Tag(enum.IntEnum):
    Wire = 1
    Global = 2
    Erase = 3
    ExtVal = 4
    Comb = 5
    ExtFn = 6
    Branch = 7


class Port:
    tag: Tag
    trace: Trace | None = None

    ERASE: "ClassVar[NilaryNodePort]"


@dataclasses.dataclass
class NilaryNodePort(Port):
    def fork(self) -> "NilaryNodePort":
        return self

    def drop(self) -> None:
        return


@dataclasses.dataclass
class ErasePort(NilaryNodePort):
    tag: Tag = Tag.Erase
    trace: Trace | None = None


Port.ERASE = ErasePort()


@dataclasses.dataclass
class WirePort(NilaryNodePort):
    wire: Wire
    tag: Tag = Tag.Wire
    trace: Trace | None = None


@dataclasses.dataclass
class BinaryNodePort(Port):
    target: Wire
    label: str
    tag: Tag
    trace: Trace | None = None

    def aux(self) -> AuxPairWireReference:
        return self.target, self.target.other_half


@dataclasses.dataclass
class CombPort(BinaryNodePort):
    label: str
    target: Wire
    tag: Tag = Tag.Comb
    trace: Trace | None = None


@dataclasses.dataclass
class BranchPort(BinaryNodePort):
    target: Wire
    tag: Tag = Tag.Branch
    trace: Trace | None = None

@dataclasses.dataclass
class WireHeap:
    wires: list[Wire] = dataclasses.field(default_factory=list)
    free_head: Wire | None = None
    max_size: int = 1024 * 1024

    def alloc_node(self) -> Wire:
        if self.free_head is not None:
            wire = self.free_head
            self.free_head = self.free_head.target # type: ignore
        else:
            if len(self.wires) < self.max_size:
                wire = Wire()
                self.wires.append(wire)
            else:
                raise MemoryError(f"WireHeap max_size {self.max_size} exceeded")

        wire.other_half.target = None
        wire.target = None
        return wire

    def free_wire(self, wire: Wire) -> None:
        wire.target = None
        if wire.other_half.target is None:
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
