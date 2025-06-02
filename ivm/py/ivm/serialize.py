from .ast import Nets, Net, Tree
from .extrinsics import PrimitiveExtValPort
from .globals import Global, Nilary, Binary, GlobalPort, Inert
from .heap import Port, Tag
from .vm import IVM

def insert_nets(ivm: IVM, nets: Nets) -> dict[str, Global]:
    gs: dict[str, Global] = { name: Global(name) for name in nets.keys() }
    for name, net in nets.items():
        serialize_net(ivm, net, name, gs)

    for g in gs.items():
        connect_comb_labels(g)

    return gs

class UnknownGlobal(Exception):
    pass

def connect_comb_labels(g: Global):
    q: list[Global] = [g]
    seen: set[Global] = set()
    while q:
        next_g = q.pop(0)
        if next_g in seen:
            continue
        seen.add(next_g)

        for instruction in next_g.instructions:
            if isinstance(instruction, Nilary) and isinstance(instruction.port, GlobalPort):
                next_g.extend_labels(instruction.port.global_ref)
                if instruction.port.global_ref not in seen:
                    q.append(instruction.port.global_ref)
            if isinstance(instruction, Binary):
                if instruction.tag == Tag.Comb:
                    next_g.add_label(instruction.label)

def serialize_net(ivm: IVM, net: Net, name: str, gs: dict[str, Global]):
    g = gs[name]
    instructions = g.instructions
    equivalents: dict[str, str] = {}
    registers: dict[str, int] = {}

    def serialize_pair(a: Tree, b: Tree):
        a = unbox(a)
        b = unbox(b)
        if b[0] == "Var":
            if a[0] == "Var":
                return
            a, b = b, a

        to = serialize_tree(a)
        serialize_tree_to(b, to)

    def serialize_tree(a: Tree) -> int:
        tree = unbox(a)
        if tree[0] == "Var":
            if (register := registers.get(tree[1])) is None:
                register = instructions.new_register()
                registers[tree[1]] = register
                return register
            return register
        register = instructions.new_register()
        serialize_tree_to(tree, register)
        return register

    def serialize_tree_to(b: Tree, to: int):
        tree = unbox(b)
        if tree[0] == "Erase":
            instructions.append(Nilary(to, Port.ERASE))
        elif tree[0] == "N32" or tree[0] == "F32":
            instructions.append(Nilary(to, PrimitiveExtValPort(value=tree[1])))
        elif tree[0] == "Comb":
            a = serialize_tree(tree[2])
            b = serialize_tree(tree[3])
            instructions.append(Binary(Tag.Comb, tree[1], to, a, b))
        elif tree[0] == "ExtFn":
            a = serialize_tree(tree[2])
            b = serialize_tree(tree[3])
            instructions.append(Binary(Tag.ExtFn, tree[1], to, a, b))
        elif tree[0] == "Global":
            try:
                port = GlobalPort(global_ref=gs[tree[1]])
            except KeyError:
                raise UnknownGlobal(f"unknown global {repr(tree[1])}")
            instructions.append(Nilary(to, port))
        elif tree[0] == "Branch":
            r = instructions.new_register()
            t1 = serialize_tree(tree[1])
            t2 = serialize_tree(tree[2])
            instructions.append(Binary(Tag.Branch, "", r, t1, t2))
            t3 = serialize_tree(tree[3])
            instructions.append(Binary(Tag.Branch, "", to, r, t3))
        elif tree[0] == "Var":
            assert tree[1] not in registers
            registers[tree[1]] = to
        elif tree[0] == "BlackBox":
            from_ = serialize_tree(tree[1])
            instructions.append(Inert(to, from_))
        else:
            assert False, "unreachable"

    for pa, pb in net.pairs:
        pa, pb = unbox(pa), unbox(pb)
        if pa[0] == "Var" and pb[0] == "Var":
            an = equivalents.pop(pa[1], pa[1])
            bn = equivalents.pop(pb[1], pb[1])
            equivalents[an] = bn
            equivalents[bn] = an

    for a, b in equivalents.items():
        if a < b:
            registers[b] = registers[a] = instructions.new_register()

    root = unbox(net.root)
    if root[0] == "Var":
        registers[root[1]] = 0
        if b := equivalents.get(root[1]):
            registers[b] = 0

    for pa, pb in reversed(net.pairs):
        serialize_pair(pa, pb)

    if root[0] != "Var":
        serialize_tree_to(net.root, 0)

    connect_comb_labels(g)

def unbox(a: Tree) -> Tree:
    while a[0] == "Blackbox":
        a = a[1]
    return a
