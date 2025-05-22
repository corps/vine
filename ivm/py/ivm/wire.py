from dataclasses import dataclass
import ctypes

from .addr import Addr
from .port import Port


@dataclass
class Wire:
    addr: Addr

    def load_target(self) -> Port | None:
        port = Port()
        ctypes.memmove(ctypes.addressof(port), self.addr.value, ctypes.sizeof(Port))
        if port.tag == 0:
            return None
        return port

    def swap_target(self, port: Port) -> Port | None:
        old = Port.from_address(self.addr.value)
        result = Port(old.value) if old.tag != 0 else None
        ctypes.pointer(old)[0] = port
        return result
