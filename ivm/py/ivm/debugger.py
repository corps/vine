import curses
import dataclasses
import sys
from collections import defaultdict
from functools import cached_property
from typing import Callable, Any

from ivm.extrinsics import ExtValPort
from ivm.globals import Global

from ivm.heap import Port
from ivm.readback import Reader
from ivm.vm import IVM


@dataclasses.dataclass
class Debugger(IVM):

    @cached_property
    def reader(self) -> Reader:
        return Reader(self)

    def debug_print(self, name: str, port: Port):
        file_part = ""
        if isinstance(port.trace, tuple):
            file_name, line_span, col_span = port.trace
            file_part = f"({file_name}:{line_span[0]}:{col_span[0]})"

        print(f"{name} {file_part}")
        reader = Reader(self)
        print(str(reader.read_port(port)))

    def interact(self, a: Port, b: Port) -> None:
        self.debug_print("a", a)
        self.debug_print("b", b)

        input("Press Enter to continue...")

        super().interact(a, b)

        if self.counts:
            print("==== Counts")
            for k, v in self.counts.items():
                print(f"{k}: {v}")
        if any(self.registers):
            print("==== Registers")
            for i, register in enumerate(self.registers):
                if register is None:
                    continue
                self.debug_print(f"register{i}", register)