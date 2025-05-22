from ctypes import c_uint64
from dataclasses import dataclass
import ctypes

from .addr import Addr
from .heap import Heap

import sys

from .wire import Wire

_free = ctypes.c_uint64((2**64 - 1) & ~0b111)


@dataclass
class Allocator:
    heap: Heap
    free_head: Addr = Addr(0)
    next_idx: int = 0

    def alloc_node(self) -> Addr:
        sys.audit("ivm.alloc", self.heap, 2)
        if self.free_head.value != 0:
            addr = self.free_head
            self.free_head = Addr.from_address(addr.value)
        else:
            sys.audit("ivm.heap", self.heap, 2)
            index = self.next_idx
            self.next_idx += 1
            _addr = self.heap.get(index)
            if _addr is None:
                raise MemoryError(
                    f"Allocator ran out of memory after {self.next_idx} allocations"
                )
            addr = _addr

        c_uint64.from_address(addr.value).value = 0
        c_uint64.from_address(addr.other_half().value).value = 0
        return addr

    def free_wire(self, wire: Wire):
        sys.audit("ivm.free", self.heap, 1)
        addr = wire.addr
        ctypes.c_uint64.from_address(addr.value).value = _free.value
        if addr.other_half().value == _free.value:
            addr = addr.left_half()
            ctypes.c_uint64.from_address(addr.value).value = self.heap.head.value
            self.heap.head = addr

    def new_wire(self) -> tuple[Wire, Wire]:
        addr = self.alloc_node()
        self.free_wire(Wire(addr.other_half()))
        return Wire(addr), Wire(addr)

    def new_wires(self) -> tuple[tuple[Wire, Wire], tuple[Wire, Wire]]:
        addr = self.alloc_node()
        return (
            (Wire(addr), Wire(addr)),
            (Wire(addr.other_half()), Wire(addr.other_half())),
        )
