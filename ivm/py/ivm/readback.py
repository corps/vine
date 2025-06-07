import dataclasses
from dataclasses import field
from typing import Any

from .extrinsics import ExtValPort, PrimitiveExtValPort, ExtFnPort, Extrinsics
from .globals import GlobalPort
from .heap import Port, WirePort, ErasePort, BranchPort, Wire, CombPort
from .tree import (
    Tree,
    N32,
    F32,
    VarTree,
    GlobalTree,
    Erase,
    N32Tree,
    F32Tree,
    ExtFnTree,
    BranchTree, CombTree,
)
from .vm import IVM


class CachedExtValPort(ExtValPort):
    serialized: Tree

    def __init__(self, value: Any, tree: Tree):
        self.serialized = tree
        super().__init__(value=value)


@dataclasses.dataclass
class ExtrinsicsCache:
    cache: list[Any] = dataclasses.field(default_factory=list)
    ext_fn_name: str = "cache"

    def __call__(self, value: Any, b: Any) -> ExtValPort:
        assert isinstance(value, N32)
        return CachedExtValPort(
            self.cache[value.value],
            ExtFnTree(
                self.ext_fn_name, N32Tree(value, None), N32Tree(N32(0), None), None
            ),
        )

    def add_new_val(self, val: Any) -> ExtValPort:
        idx = N32(len(self.cache))
        self.cache.append(val)
        return self(idx, idx)

    def install_into(self, extrinsics: Extrinsics) -> None:
        assert self.ext_fn_name not in extrinsics.ext_fns
        extrinsics.ext_fns[self.ext_fn_name] = self


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
            else:
                n = self.next_var
                self.next_var += 1
                self.vars[addr] = n

            return VarTree(f"n{n}", p.trace)
        elif isinstance(p, GlobalPort):
            return GlobalTree(p.global_ref.name, p.trace)
        elif isinstance(p, ErasePort):
            return Erase(p.trace)
        elif isinstance(p, ExtValPort):
            if isinstance(p, PrimitiveExtValPort):
                if isinstance(p.value, N32):
                    return N32Tree(p.value, p.trace)
                elif isinstance(p.value, F32):
                    return F32Tree(p.value, p.trace)
            elif isinstance(p, CachedExtValPort):
                return p.serialized
            raise NotImplementedError(f"Unknown ExtValPort type {type(p)}")
        elif isinstance(p, CombPort):
            p1, p2 = p.aux()
            return CombTree(p.label, self.read_wire(p1), self.read_wire(p2), p.trace)
        elif isinstance(p, ExtFnPort):
            p1, p2 = p.aux()
            return ExtFnTree(p.label, self.read_wire(p1), self.read_wire(p2), p.trace)
        elif isinstance(p, BranchPort):
            p1, p2 = p.aux()
            bp = self.ivm.follow(WirePort(wire=p1), destructive=False)
            assert isinstance(bp, BranchPort)
            p11, p12 = bp.aux()
            return BranchTree(
                self.read_wire(p11), self.read_wire(p12), self.read_wire(p2), p.trace
            )
        else:
            raise NotImplementedError(f"Unknown type {type(p)}")

    def read_wire(self, p: Wire) -> Tree:
        return self.read_port(WirePort(wire=p))
