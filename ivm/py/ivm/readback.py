import dataclasses
from dataclasses import field

from .ast import Tree, N32, F32
from .extrinsics import ExtValPort, PrimitiveExtValPort, ExtFnPort
from .globals import Global, GlobalPort
from .heap import Port, WirePort, ErasePort, BranchPort, Wire
from .vm import IVM


@dataclasses.dataclass
class Reader:
    ivm: IVM
    vars: dict[int, int] = field(default_factory=dict)
    next_var: int = 0

    def read_port(self, port: Port) -> Tree:
        p = self.ivm.follow(port, destructive=False)
        if isinstance(p, WirePort):
            addr = id(p.wire)
            if addr in self.vars:
                n = self.vars.pop(addr)
                del self.vars[addr]
            else:
                n = self.next_var
                self.next_var += 1
                self.vars[addr] = n

            return ("Var", f"n{n}")
        elif isinstance(p, GlobalPort):
            return ("Global", p.global_ref.name)
        elif isinstance(p, ErasePort):
            return ("Erase",)
        elif isinstance(p, ExtValPort):
            if isinstance(p, PrimitiveExtValPort):
                if isinstance(p.value, N32):
                    return ("N32", p.value)
                elif isinstance(p.value, F32):
                    return ("F32", p.value)
            raise NotImplementedError("TODO")
        elif isinstance(p, ExtFnPort):
            p1, p2 = p.aux()
            return ("ExtFn", p.label, self.read_wire(p1), self.read_wire(p2))
        elif isinstance(p, BranchPort):
            p1, p2 = p.aux()
            p1 = self.ivm.follow(p1, destructive=False)
            assert isinstance(p1, BranchPort)
            p11, p12 = p1.aux()
            return ("Branch", self.read_wire(p11), self.read_wire(p12), self.read_wire(p2))
        else:
            raise NotImplementedError("OK TODO")

    def read_wire(self, p: Wire) -> Tree:
        return self.read_port(WirePort(wire=p))

