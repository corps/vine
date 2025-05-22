import sys

from .ext import ExtFn, ExtVal
from .ivm import IVM
from .port import Port, Tag
from .wire import Wire
from .globals import Global


def link(ivm: IVM, a: Port, b: Port):
    if a.tag < b.tag:
        comb = (a.tag, b.tag, a.label == b.label)
    else:
        comb = (b.tag, a.tag, a.label == b.label)
    match comb:
        # Wires link
        case (Tag.Wire, _, _):
            link_wire(ivm, Wire(a.addr), b)
        case (_, Tag.Wire, _):
            link_wire(ivm, Wire(b.addr), a)

        # Nilary erase
        case (
            (Tag.Global, Tag.Erase, _)
            | (Tag.ExtVal, Tag.Erase, _)
            | (Tag.Erase, Tag.Global, _)
            | (Tag.Erase, Tag.ExtVal, _)
        ):
            sys.audit("ivm.erase", ivm, 1)

        # Commute
        case (Tag.Comb, Tag.Comb, True) | (Tag.ExtFn, Tag.ExtFn, True):
            ivm.active_fast.append((a, b))

        # Expand
        case (Tag.Global, _, _) | (_, Tag.Global, _):
            ivm.active_slow.append((a, b))

        # Thingy
        case (
            (Tag.Erase, _, _)
            | (_, Tag.Erase, _)
            | (Tag.ExtVal, _, _)
            | (_, Tag.ExtVal, _)
        ):
            ivm.active_fast.append((a, b))

        case _:
            ivm.active_slow.append((a, b))


def interact(ivm: IVM, a: Port, b: Port):
    pass


def expand(ivm: IVM, a: Port, b: Port):
    sys.audit("ivm.expand", ivm, 1)
    g = Global.from_address(a.addr.value)
    ivm.execute(g.instructions, b)


def annihilate(ivm: IVM, a: Port, b: Port):
    sys.audit("ivm.annihilate", ivm, 1)
    a1, a2 = a.aux()
    b1, b2 = b.aux()
    link_wire_wire(ivm, Wire(a1), Wire(b1))
    link_wire_wire(ivm, Wire(a2), Wire(b2))


def copy(ivm: IVM, a: Port, b: Port):
    sys.audit("ivm.copy", ivm, 1)
    x, y = b.aux()
    link_wire(ivm, Wire(x), Port(a.value))
    link_wire(ivm, Wire(y), a)


def commute(ivm: IVM, a: Port, b: Port):
    sys.audit("ivm.commute", ivm, 1)
    a1 = ivm.new_node(Tag(a.tag), a.label)
    a2 = ivm.new_node(Tag(a.tag), a.label)
    b1 = ivm.new_node(Tag(b.tag), b.label)
    b2 = ivm.new_node(Tag(b.tag), b.label)

    a_1, a_2 = a.aux()
    b_1, b_2 = b.aux()

    link_wire_wire(ivm, a1[1], b1[1])
    link_wire_wire(ivm, a1[2], b2[1])
    link_wire_wire(ivm, a2[1], b1[2])
    link_wire_wire(ivm, a2[2], b2[2])

    link_wire(ivm, Wire(a_1), b1[0])
    link_wire(ivm, Wire(a_2), b2[0])
    link_wire(ivm, Wire(b_1), a1[0])
    link_wire(ivm, Wire(b_2), a2[0])


def call(ivm: IVM, a: Port, b: Port):
    fn = ExtFn.from_address(a.addr.value)
    rhs, out = a.aux()
    rhs_wire = Wire(rhs)
    rhs_port = rhs_wire.load_target()
    if rhs_port:
        if rhs_port.tag == Tag.ExtVal:
            sys.audit("ivm.call", ivm, 1)
            ivm.allocator.free_wire(rhs_wire)
            result = ivm.extrinsics.call(
                fn,
                ExtVal.from_address(b.addr.value),
                ExtVal.from_address(rhs_port.addr.value),
            )
            link_wire(ivm, Wire(out), Port.new_ext_val(result))
            return

    new_fn = ivm.new_node(Tag.ExtFn, fn.swapped.bits)
    link_wire(ivm, rhs_wire, new_fn[0])
    link_wire(ivm, new_fn[1], a)
    link_wire_wire(ivm, new_fn[2], Wire(out))


def branch(ivm: IVM, a: Port, b: Port):
    sys.audit("ivm.branch", ivm, 1)
    val = ivm.extrinsics.as_n32(ExtVal.from_buffer(bytes(b)))
    b1, b2 = b.aux()
    branch, z, p = ivm.new_node(Tag.Branch, 0)
    link_wire(ivm, Wire(b1), branch)
    if val == 0:
        y, n = z, p
    else:
        y, n = p, z
    link_wire(ivm, n, Port.ERASE())
    link_wire_wire(ivm, Wire(b2), y)


def link_wire(ivm: IVM, a: Wire, b: Port):
    b = follow(ivm, b, True)
    c = a.swap_target(b)
    if c:
        ivm.allocator.free_wire(a)
        link(ivm, c, b)


def link_wire_wire(ivm: IVM, a: Wire, b: Wire):
    return link_wire(ivm, a, Port.new_wire(b.addr))


def follow(ivm: IVM, a: Port, destructive: bool) -> Port:
    while a.tag == Tag.Wire:
        wire = Wire(a.addr)
        b = wire.load_target()
        if b:
            if destructive:
                ivm.allocator.free_wire(wire)
            a = b
    return a
