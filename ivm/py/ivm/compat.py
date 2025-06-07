from typing import Any, Callable

from ivm.extrinsics import ExtValPort, PrimitiveExtValPort
from ivm.host import Host
from ivm.tree import N32
import sys


def add_std_compat(host: Host):
    def default_ext_fn(c: Callable[[Any, Any], ExtValPort]):
        host.add_ext_fun(c)

    @default_ext_fn
    def io_print_byte(io: Any, byte: N32) -> ExtValPort:
        sys.stdout.write(chr(byte.value))
        return PrimitiveExtValPort(N32(0))

    @default_ext_fn
    def io_flush(io: Any, _: Any) -> ExtValPort:
        sys.stdout.flush()
        return PrimitiveExtValPort(N32(0))

    @default_ext_fn
    def n32_sub(a: N32, b: N32) -> ExtValPort:
        return PrimitiveExtValPort(N32(a.value - b.value))

    @default_ext_fn
    def n32_add(a: N32, b: N32) -> ExtValPort:
        return PrimitiveExtValPort(N32(a.value + b.value))

    @default_ext_fn
    def n32_eq(a: N32, b: N32) -> ExtValPort:
        return PrimitiveExtValPort(N32(a.value == b.value))

    @default_ext_fn
    def n32_mul(a: N32, b: N32) -> ExtValPort:
        return PrimitiveExtValPort(N32(a.value * b.value))

    @default_ext_fn
    def n32_rem(a: N32, b: N32) -> ExtValPort:
        return PrimitiveExtValPort(N32(a.value % b.value))

    @default_ext_fn
    def n32_div(a: N32, b: N32) -> ExtValPort:
        return PrimitiveExtValPort(N32(a.value // b.value))

    @default_ext_fn
    def io_read_byte(io: Any, default: N32) -> ExtValPort:
        result = sys.stdin.read(1)
        if not result:
            return PrimitiveExtValPort(default)
        return PrimitiveExtValPort(N32(ord(result)))