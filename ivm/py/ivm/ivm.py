import ctypes

from .allocator import Allocator
from .ext import Extrinsics, ExtVal
from dataclasses import dataclass, field

from .globals import Global
from .instruction import Instructions, Instruction
from .interact import link_wire, interact
from .port import Port, Tag
from .wire import Wire


@dataclass
class IVM:
    extrinsics: Extrinsics
    allocator: Allocator
    active_fast: list[tuple[Port, Port]] = field(default_factory=list)
    active_slow: list[tuple[Port, Port]] = field(default_factory=list)
    inert: list[tuple[Port, Port]] = field(default_factory=list)
    registers: list[Port] = field(default_factory=list)

    def boot(self, g: Global, ext_val: ExtVal):
        link_wire(
            self,
            Port.from_tag_label_pointer(Tag.Global, 0, ctypes.addressof(g)),
            Port.new_ext_val(ext_val),
        )

    def do_fast(self):
        while self.active_fast:
            a, b = self.active_fast.pop()
            interact(self, a, b)

    def normalize(self):
        while True:
            self.do_fast()
            if self.active_slow:
                a, b = self.active_slow.pop()
                interact(self, a, b)
            else:
                break

    def link_register(self, register: int, port: Port) -> None:
        register_port = self.registers[register]
        if register_port.tag:
            self.registers[register] = Port()
            self.link(port, register_port)
        else:
            self.registers[register] = port

    def link(self, a: Port, b: Port) -> None:
        pass

    def new_node(self, tag: Tag, label: int) -> tuple[Port, Wire, Wire]:
        addr = self.allocator.alloc_node()
        return (
            Port.from_tag_label_pointer(tag, label, addr.value),
            Wire(addr),
            Wire(addr.other_half()),
        )

    def execute(self, instructions: Instructions, port: Port) -> None:
        needed_registers = max(instructions.next_register, 1)
        if needed_registers > len(self.registers):
            self.registers += [Port()] * (needed_registers - len(self.registers))

        self.link_register(0, port)

        for instruction in instructions:
            val = instruction.unpack()
            if isinstance(val, Instruction.Union.NilaryInstruction):
                self.link_register(val.register, Port(val.port.value))
            elif isinstance(val, Instruction.Union.BinaryInstruction):
                p, w1, w2 = self.new_node(Tag(val.tag), val.label)
                self.link_register(val.register0, p)
                self.link_register(val.register1, Port.new_wire(w1.addr))
                self.link_register(val.register2, Port.new_wire(w2.addr))
            elif isinstance(val, Instruction.Union.InertInstruction):
                wires = self.allocator.new_wires()
                self.link_register(val.register0, Port.new_wire(wires[0][0].addr))
                self.link_register(val.register1, Port.new_wire(wires[1][0].addr))
                self.inert.append(
                    (
                        Port.new_wire(wires[0][1].addr),
                        Port.new_wire(wires[1][1].addr),
                    )
                )
            else:
                raise NotImplementedError

        # Registers used twice self clear, whereas odd ones represent leak
        for register in self.registers:
            assert register.tag == 0, f"Found register tag {register.tag}, expected 0"
