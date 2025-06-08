import abc
import ctypes
import dataclasses
from dataclasses import dataclass
from math import isnan
from typing import (
    OrderedDict,
    Any,
    Iterator,
)

from ivm.heap import Trace


class N32(ctypes.c_uint32):
    def __eq__(self, other: Any):
        if isinstance(other, N32):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return str(self.value)

    __str__ = __repr__


class F32(ctypes.c_float):
    def __eq__(self, other: Any):
        if isinstance(other, F32):
            return self.value == other.value
        return False

    def __repr__(self) -> str:
        return str(self.value)

    __str__ = __repr__


class Tree(abc.ABC):
    trace: Trace | None

    @abc.abstractmethod
    def __iter__(self) -> "Iterator[Tree]": ...


@dataclasses.dataclass
class Erase(Tree):
    trace: Trace | None

    def __str__(self):
        return "_"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]: return iter(())


@dataclasses.dataclass
class CombNode(Tree):
    label: str
    left: "Tree"
    right: "Tree"
    trace: Trace | None

    def __str__(self):
        return f"{self.label}({self.left}, {self.right})"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        yield self.left
        yield self.right


@dataclasses.dataclass
class ExtFnNode(Tree):
    label: str
    left: "Tree"
    right: "Tree"
    trace: Trace | None

    def __str__(self):
        return f"@{self.label}({self.left}, {self.right})"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        yield self.left
        yield self.right


@dataclasses.dataclass
class BranchNode(Tree):
    n0: "Tree"
    n1: "Tree"
    n2: "Tree"
    trace: Trace | None

    def __str__(self):
        return f"?({self.n0} {self.n1} {self.n2})"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        yield self.n0
        yield self.n1
        yield self.n2



@dataclasses.dataclass
class N32Node(Tree):
    value: N32
    trace: Trace | None

    def __str__(self):
        return f"{self.value.value}"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())


@dataclasses.dataclass
class F32Node(Tree):
    value: F32
    trace: Trace | None

    def __str__(self):
        if isnan(self.value.value):
            return "+NaN"
        return f"{self.value:+?}"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())


@dataclasses.dataclass
class VarNode(Tree):
    name: str
    trace: Trace | None

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())


@dataclasses.dataclass
class GlobalNode(Tree):
    name: str
    trace: Trace | None

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())


@dataclasses.dataclass
class BlackBox(Tree):
    inner: "Tree"
    trace: Trace | None

    def __str__(self):
        return f"{self.inner}"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(self.inner)


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
