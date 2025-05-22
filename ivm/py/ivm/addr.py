import ctypes


class Addr(ctypes.c_uint64):
    def other_half(self) -> "Addr":
        return Addr(self.value ^ 0b1000)

    def left_half(self) -> "Addr":
        return Addr(self.value & ~0b1000)
