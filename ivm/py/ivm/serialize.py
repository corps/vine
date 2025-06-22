from .tree import (
    Nets,
    Net,
    Tree,
    VarNode,
    Erase,
    N32Node,
    F32Node,
    CombNode,
    ExtFnNode,
    GlobalNode,
    BranchNode,
    BlackBox,
)
from .extrinsics import PrimitiveExtValPort
from .globals import Global, Nilary, Binary, GlobalPort, Inert
from .heap import Port, Tag, ErasePort
from .vm import IVM


def insert_nets(ivm: IVM, nets: Nets) -> dict[str, Global]:
    gs: dict[str, Global] = {name: Global(name) for name in nets.keys()}
    for name, net in nets.items():
        serialize_net(ivm, net, name, gs)

    for g in gs.values():
        connect_comb_labels(g)

    return gs


class UnknownGlobal(Exception):
    pass


def connect_comb_labels(g: Global):
    q: list[Global] = [g]
    seen: set[str] = set()
    while q:
        next_g = q.pop(0)
        if next_g.name in seen:
            continue
        seen.add(next_g.name)

        for instruction in next_g.instructions:
            if isinstance(instruction, Nilary) and isinstance(
                instruction.port, GlobalPort
            ):
                next_g.extend_labels(instruction.port.global_ref)
                if instruction.port.global_ref.name not in seen:
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
        if isinstance(b, VarNode):
            if isinstance(a, VarNode):
                # Already handled via equivalents
                return
            a, b = b, a

        to = serialize_tree(a)
        serialize_tree_to(b, to)

    def serialize_tree(a: Tree) -> int:
        tree = unbox(a)
        if isinstance(tree, VarNode):
            if (register := registers.get(tree.name)) is None:
                register = instructions.new_register()
                registers[tree.name] = register
                return register
            return register
        register = instructions.new_register()
        serialize_tree_to(tree, register)
        return register

    def serialize_tree_to(fr: Tree, to: int):
        tree = unbox(fr)
        if isinstance(tree, Erase):
            instructions.append(Nilary(to, ErasePort(trace=tree.trace)))
        elif isinstance(tree, (N32Node, F32Node)):
            instructions.append(
                Nilary(to, PrimitiveExtValPort(value=tree.value, trace=tree.trace))
            )
        elif isinstance(tree, CombNode):
            a = serialize_tree(tree.left)
            b = serialize_tree(tree.right)
            instructions.append(Binary(Tag.Comb, tree.label, to, a, b, tree.trace))
        elif isinstance(tree, ExtFnNode):
            a = serialize_tree(tree.left)
            b = serialize_tree(tree.right)
            instructions.append(Binary(Tag.ExtFn, tree.label, to, a, b, tree.trace))
        elif isinstance(tree, GlobalNode):
            try:
                port = GlobalPort(global_ref=gs[tree.name], trace=tree.trace)
            except KeyError:
                raise UnknownGlobal(f"unknown global {repr(tree.name)}")
            instructions.append(Nilary(to, port))
        elif isinstance(tree, BranchNode):
            r = instructions.new_register()
            t1 = serialize_tree(tree.n0)
            t2 = serialize_tree(tree.n1)
            instructions.append(Binary(Tag.Branch, "", r, t1, t2, tree.trace))
            t3 = serialize_tree(tree.n2)
            instructions.append(Binary(Tag.Branch, "", to, r, t3, tree.trace))
        elif isinstance(tree, VarNode):
            assert tree.name not in registers
            registers[tree.name] = to
        elif isinstance(tree, BlackBox):
            from_ = serialize_tree(tree.inner)
            instructions.append(Inert(to, from_))
        else:
            raise NotImplementedError(f"unknown tree {repr(tree)}")

    for pa, pb in net.pairs:
        pa, pb = unbox(pa), unbox(pb)
        if isinstance(pa, VarNode) and isinstance(pb, VarNode):
            an = equivalents.pop(pa.name, pa.name)
            bn = equivalents.pop(pb.name, pb.name)
            equivalents[an] = bn
            equivalents[bn] = an

    for a, b in equivalents.items():
        if a < b:
            registers[b] = registers[a] = instructions.new_register()

    root = unbox(net.root)
    if isinstance(root, VarNode):
        registers[root.name] = 0
        if bb := equivalents.get(root.name):
            registers[bb] = 0

    for pa, pb in reversed(net.pairs):
        serialize_pair(pa, pb)

    if not isinstance(root, VarNode):
        serialize_tree_to(net.root, 0)

    connect_comb_labels(g)


def unbox(a: Tree) -> Tree:
    while isinstance(a, BlackBox):
        a = a.inner
    return a
