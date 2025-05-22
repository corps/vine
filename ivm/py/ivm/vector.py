import ctypes
from typing import Generic, TypeVar, Any, Iterator

_A = TypeVar("_A", bound=ctypes._CData)


class Vector(ctypes.Structure, Generic[_A]):
    ptr: Any
    length: int

    def push(self, item: _A):
        if self.length >= 2**32 - 1:
            raise ValueError("Too many items")

        _size = ctypes.sizeof(type(item))
        if not self.ptr or not self.length:
            self.ptr = ctypes.cast(
                ctypes.pointer((type(item) * 33)()), ctypes.POINTER(type(item)) #  type: ignore
            )
            ctypes.memset(self.ptr, 0, _size * 33)
            ctypes.memset(self.ptr, 1, _size * 32)
        elif not self.ptr[self.length + 1]:
            new_buf = ctypes.cast(
                ctypes.pointer((type(item) * (self.length * 2 + 1))()), #  type: ignore
                ctypes.POINTER(type(item)),
            )
            ctypes.memset(new_buf, 0, (self.length * 2 + 1) * _size)
            ctypes.memset(new_buf, 1, self.length * 2 * _size)
            ctypes.memmove(new_buf, self.ptr, self.length * _size)
            self.ptr = new_buf

        self.ptr[self.length] = item
        self.length += 1

    def __iter__(self) -> Iterator[_A]:
        for i in range(self.length):
            yield self.ptr[i]

    def __getitem__(self, item: int) -> _A:
        return self.ptr[item]

    def __setitem__(self, item: int, value: _A) -> None:
        self.ptr[item] = value

    def __len__(self) -> int:
        return self.length

    @staticmethod
    def for_type(a: type[_A]) -> "type[Vector[_A]]":
        class _Vector(Vector):
            _fields_ = [("length", ctypes.c_uint32), ("ptr", ctypes.POINTER(a))]

        return _Vector


def test_vector():
    a = Vector.for_type(ctypes.c_uint32)()

    for i in range(100):
        a.push(ctypes.c_uint32(i))

    assert list(a) == list(range(100))
