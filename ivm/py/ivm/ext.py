from functools import cached_property
from typing import Callable
import ctypes


class ExtTy(ctypes.Union):
    class Meta(ctypes.Structure):
        _fields_ = [("unknown", ctypes.c_uint16, 15), ("is_rc", ctypes.c_bool, 1)]
        unknown: int
        is_rc: bool

    class Id(ctypes.Structure):
        _fields = [("id", ctypes.c_uint16)]
        id: int

    @classmethod
    def from_id_and_rc(cls, id: int, rc: bool) -> "ExtTy":
        result = ExtTy()
        result.as_id.id = id
        result.as_meta.is_rc = rc
        return result

    _fields_ = [("as_meta", Meta), ("as_id", Id)]
    as_meta: Meta
    as_id: Id

assert ctypes.sizeof(ExtTy) == 2, "Alignment wrong for ExtTy"

class ExtVal(ctypes.Structure):
    _fields_ = [
        ("tag", ctypes.c_uint16),
        ("ty", ExtTy),
        ("payload", ctypes.c_uint32),
    ]
    payload: int
    ty: ExtTy
    tag: int


assert ctypes.sizeof(ExtVal) == 8, "Alignment wrong for ExtVal"


class ExtFn(ctypes.Structure):
    _fields_ = [
        ("kind", ctypes.c_uint16, 15),
        ("is_swap", ctypes.c_bool, 1),
    ]
    kind: int
    is_swap: bool

    @cached_property
    def swapped(self) -> "ExtFn":
        return ExtFn(kind=self.kind, is_swap=not self.is_swap)

    @property
    def bits(self) -> int:
        return self.is_swap << 15 | self.kind


assert ctypes.sizeof(ExtFn) == 2, "Alignment wrong for ExtFn"


class Extrinsics:
    light_ext_ty: int
    ext_fns: list[Callable[[ExtVal, ExtVal], ExtVal]]
    n32_ext_type: ExtTy

    MAX_EXT_FN_KIND_COUNT: int = 0x7FFF
    MAX_LIGHT_EXT_TY_COUNT: int = 0x7FFF

    def __init__(self):
        self.ext_fns = []
        self.light_ext_ty = 0
        self.n32_ext_type = self.register_light_ext_ty()

    def register_ext_fn(self, f: Callable[[ExtVal, ExtVal], ExtVal]) -> ExtFn:
        ext_fn_idx = len(self.ext_fns)
        if ext_fn_idx >= self.MAX_EXT_FN_KIND_COUNT:
            raise ValueError(
                "IVM reached maximum amount of registered extrinsic functions"
            )
        result = ExtFn(kind=ext_fn_idx, is_swap=False)
        self.ext_fns.append(f)
        return result

    def register_light_ext_ty(self) -> ExtTy:
        if self.light_ext_ty >= self.MAX_LIGHT_EXT_TY_COUNT:
            raise ValueError(
                "IVM reached maximum amount of registered extrinsic unboxed types"
            )
        result = ExtTy.from_id_and_rc(self.light_ext_ty, False)
        self.light_ext_ty += 1
        return result

    def call(self, ext_fn: ExtFn, arg0: ExtVal, arg1: ExtVal) -> ExtVal:
        callable = self.ext_fns[ext_fn.kind]
        if ext_fn.is_swap:
            arg0, arg1 = arg1, arg0
        return callable(arg0, arg1)

    def as_n32(self, ext_val: ExtVal) -> int:
        assert ext_val.ty == self.n32_ext_type
        return ext_val.payload
