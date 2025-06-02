import dataclasses
from typing import Protocol, Iterator

from .extrinsics import ExtFnPort
from .heap import Port, NilaryNodePort, Tag, WireHeap, CombPort, BranchPort, WirePort


class ExecutionContext(Protocol):
    heap: WireHeap
    def link_register(self, register: int, port: Port): ...

class Instruction(Protocol):
    def execute(self, context: "ExecutionContext", port: Port) -> tuple[Port, Port] | None: ...

@dataclasses.dataclass
class Nilary(Instruction):
    register: int
    port: NilaryNodePort

    def execute(self, context: ExecutionContext, port: Port) -> tuple[Port, Port] | None:
        assert isinstance(port, NilaryNodePort)
        context.link_register(self.register, port.fork())

@dataclasses.dataclass
class Binary(Instruction):
    tag: Tag
    label: str
    register0: int
    register1: int
    register2: int

    def execute(self, context: ExecutionContext, port: Port) -> tuple[Port, Port] | None:
        wire = context.heap.alloc_node()
        if self.tag == Tag.Comb:
            port = CombPort(target=wire, label=self.label)
        elif self.tag == Tag.Branch:
            port = BranchPort(target=wire, label=self.label)
        else:
            port = ExtFnPort(target=wire, label=self.label)
        context.link_register(self.register0, port)
        context.link_register(self.register1, WirePort(wire=wire))
        context.link_register(self.register2, WirePort(wire=wire.other_half))

@dataclasses.dataclass
class Inert(Instruction):
    register0: int
    register1: int

    def execute(self, context: ExecutionContext, port: Port) -> tuple[Port, Port] | None:
        wires = context.heap.new_wires()
        context.link_register(self.register0, WirePort(wire=wires[0][0]))
        context.link_register(self.register1, WirePort(wire=wires[1][0]))
        return WirePort(wire=wires[0][1]), WirePort(wire=wires[1][1])

@dataclasses.dataclass
class Instructions:
    instructions: list[Instruction] = dataclasses.field(default_factory=list)
    next_register: int = 1

    def new_register(self) -> int:
        register = self.next_register
        self.next_register += 1
        return register

    def __iter__(self) -> Iterator[Instruction]:
        return iter(self.instructions)

    def append(self, instruction: Instruction) -> None:
        self.instructions.append(instruction)

@dataclasses.dataclass
class Global:
    name: str
    # Specifically, the combinator labels that exist in this network -- used to shortcut
    # copying global = combinator interactions when they would just erase anyways.
    # See serialization logic for how this gets filled out.
    labels: tuple[set[str], dict[str, set[str]]] = dataclasses.field(default_factory=lambda: (set(), {}))
    instructions: Instructions = dataclasses.field(default_factory=Instructions)

    def contains_label(self, label: str) -> bool:
        s, o = self.labels
        return label in s or any(label in s_ for s_ in o.items())

    def add_label(self, label: str) -> None:
        self.labels[0].add(label)

    def extend_labels(self, other: "Global"):
        self.labels[1][other.name] = other.labels[0]


@dataclasses.dataclass
class GlobalPort(NilaryNodePort):
    global_ref: Global
    tag: Tag = Tag.Global
