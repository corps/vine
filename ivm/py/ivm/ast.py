import ctypes
from dataclasses import dataclass
from math import isnan
from typing import Union, Literal, Sequence, Iterator, OrderedDict, Any, Generator


class N32(ctypes.c_uint32):
    def __eq__(self, other: Any):
        if isinstance(other, N32):
            return self.value == other.value
        return False

class F32(ctypes.c_float):
    def __eq__(self, other: Any):
        if isinstance(other, F32):
            return self.value == other.value
        return False

Tree = Union[
    tuple[Literal["Erase"]],
    tuple[Literal["Comb"], str, "Tree", "Tree"],
    tuple[Literal["ExtFn"], str, "Tree", "Tree"],
    tuple[Literal["Branch"], "Tree", "Tree", "Tree"],
    tuple[Literal["N32"], N32],
    tuple[Literal["F32"], F32],
    tuple[Literal["Var"], str],
    tuple[Literal["Global"], str],
    tuple[Literal["BlackBox"], "Tree"],
]

@dataclass(frozen=True)
class Net:
    root: Tree
    pairs: tuple[tuple[Tree, Tree], ...]

Nets = OrderedDict[str, Net]


def format_tree(tree: Tree) -> str:
    match tree[0]:
        case "Erase":
            return "_"
        case "Comb":
            f, a, b = tree[1:]
            return f"{f}({a}, {b})"
        case "ExtFn":
            e, a, b = tree[1:]
            return f"@{e}({a}, {b})"
        case "Branch":
            a, b, c = tree[1:]
            return f"?({a} {b} {c})"
        case "N32":
            return str(tree[1])
        case "F32":
            if isnan(tree[1]):
                return "+NaN"
            return f"{tree[1]:+?}"
        case "Var":
            return tree[1]
        case "Global":
            return tree[1]
        case "BlackBox":
            return f"#[{format_tree(tree[1])}]"
        case _:
            raise ValueError(f"Unknown tree: {tree}")


def format_net(net: Net) -> str:
    if not net.pairs:
        return " ".join(["{{", format_tree(net.root), "}}"])
    return "\n  ".join(
        [
            "{{",
            format_tree(net.root),
            *[f"{format_tree(a)} = {format_tree(b)}" for a, b in net.pairs],
            "}}",
        ]
    )


def n_ary(label: str, ports: Sequence[Tree]) -> Tree:
    result: Tree | None = None
    for tree in reversed(ports):
        if result is None:
            result = tree
            continue
        result = ("Comb", label, tree, result)
    return result or ("Erase",)


def children(tree: Tree) -> Iterator[Tree]:
    match tree[0]:
        case "Comb":
            yield children(tree[2])
            yield children(tree[3])
        case "ExtFn":
            yield children(tree[3])
            yield children(tree[4])
        case "Branch":
            yield children(tree[1])
            yield children(tree[2])
            yield children(tree[3])
        case "BlackBox":
            yield children(tree[1])

def children_mut(tree: Tree) -> Generator[Tree, Tree, Tree]:
    match tree[0]:
        case "Comb":
            a = yield children(tree[2])
            b = yield children(tree[3])
            return *tree[:2], a, b
        case "ExtFn":
            a = yield children(tree[3])
            b = yield children(tree[4])
            return *tree[:3], a, b
        case "Branch":
            a = yield children(tree[1])
            b = yield children(tree[2])
            c = yield children(tree[3])
            return *tree[:1], a, b, c
        case "BlackBox":
            a = yield children(tree[1])
            return *tree[:1], a
    return tree