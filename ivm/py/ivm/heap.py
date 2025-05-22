import ctypes

from .addr import Addr


class Heap:
    memory: ctypes.Array[ctypes.c_uint8]
    nodes: int
    head: Addr

    def get(self, node_idx: int) -> Addr | None:
        if node_idx < self.nodes:
            return Addr(self.head.value + node_idx * 16)
        return None


def new_heap(bytes: int):
    if bytes % 16 != 0:
        raise ValueError(f"size {bytes} was not multiple of 16.")
    buff_type = ctypes.c_uint8 * bytes

    class SizedHeap(ctypes.Structure, Heap):
        _fields_ = [("memory", buff_type)]
        nodes = bytes // 16

    result = SizedHeap()
    result.head = Addr(ctypes.addressof(result.memory))
    assert result.head == result.head.left_half()
    return result
