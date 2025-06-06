import abc
import ctypes
import dataclasses
from dataclasses import dataclass
from math import isnan
from typing import (
    Union,
    Literal,
    Sequence,
    Iterator,
    OrderedDict,
    Any,
    Generator,
    Callable,
)


class N32(ctypes.c_uint32):
    def __eq__(self, other: Any):
        if isinstance(other, N32):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return self.value


class F32(ctypes.c_float):
    def __eq__(self, other: Any):
        if isinstance(other, F32):
            return self.value == other.value
        return False


class Tree(abc.ABC):
    trace: Callable[[], None] | None


@dataclasses.dataclass
class Erase(Tree):
    trace: Callable[[], None] | None

    def __str__(self):
        return "_"

    __repr__ = __str__


@dataclasses.dataclass
class CombTree(Tree):
    label: str
    left: "Tree"
    right: "Tree"
    trace: Callable[[], None] | None

    def __str__(self):
        return f"{self.label}({self.left}, {self.right})"

    __repr__ = __str__


@dataclasses.dataclass
class ExtFnTree(Tree):
    label: str
    left: "Tree"
    right: "Tree"
    trace: Callable[[], None] | None

    def __str__(self):
        return f"@{self.label}({self.left}, {self.right})"

    __repr__ = __str__


@dataclasses.dataclass
class BranchTree(Tree):
    n0: "Tree"
    n1: "Tree"
    n2: "Tree"
    trace: Callable[[], None] | None

    def __str__(self):
        return f"?({self.n0} {self.n1} {self.n2})"

    __repr__ = __str__


@dataclasses.dataclass
class N32Tree(Tree):
    value: N32
    trace: Callable[[], None] | None

    def __str__(self):
        return f"{self.value.value}"

    __repr__ = __str__


@dataclasses.dataclass
class F32Tree(Tree):
    value: F32
    trace: Callable[[], None] | None

    def __str__(self):
        if isnan(self.value.value):
            return "+NaN"
        return f"{self.value:+?}"

    __repr__ = __str__


@dataclasses.dataclass
class VarTree(Tree):
    name: str
    trace: Callable[[], None] | None

    def __str__(self):
        return self.name

    __repr__ = __str__


@dataclasses.dataclass
class GlobalTree(Tree):
    name: str
    trace: Callable[[], None] | None

    def __str__(self):
        return self.name

    __repr__ = __str__


@dataclasses.dataclass
class BlackBox(Tree):
    inner: "Tree"
    trace: Callable[[], None] | None

    def __str__(self):
        return f"{self.inner}"

    __repr__ = __str__


@dataclass(frozen=True)
class Net:
    root: Tree
    pairs: tuple[tuple[Tree, Tree], ...]

    def __str__(self):
        if not self.pairs:
            return " ".join(["{{", str(self.root), "}}"])
        return "\n  ".join(
            [
                "{{",
                str(self.root),
                *[f"{a} = {b}" for a, b in self.pairs],
                "}}",
            ]
        )


Nets = OrderedDict[str, Net]
