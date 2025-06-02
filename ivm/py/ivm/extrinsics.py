import dataclasses
from dataclasses import field
from typing import Any, Callable, Mapping

from .ast import N32, F32
from .heap import NilaryNodePort, Tag, BinaryNodePort, Wire


@dataclasses.dataclass
class ExtValPort(NilaryNodePort):
    value: Any
    tag: Tag = Tag.ExtVal

    def fork(self) -> "NilaryNodePort":
        raise NotImplementedError(f"Extrinsic values should subclass fork")

    def drop(self) -> None:
        raise NotImplementedError(f"Extrinsic values should subclass drop")

@dataclasses.dataclass
class PrimitiveExtValPort(ExtValPort):
    value: N32 | F32
    tag: Tag = Tag.ExtVal

    def fork(self) -> "NilaryNodePort":
        return self

    def drop(self) -> None:
        return

@dataclasses.dataclass
class ExtFnPort(BinaryNodePort):
    label: str
    target: Wire
    tag: Tag = Tag.ExtFn

    @property
    def swapped(self) -> bool:
        return self.label.startswith("@")

    def unwrap_label(self) -> str:
        if self.swapped:
            return self.label[1:]
        else:
            return self.label


    def swap(self) -> "ExtFnPort":
        if self.swapped:
            return dataclasses.replace(self, label=self.label[1:])
        else:
            return dataclasses.replace(self, label="@" + self.label)

@dataclasses.dataclass
class Extrinsics:
    ext_fns: dict[str, Callable[[Any, Any], ExtFnPort]] = field(default_factory=dict)