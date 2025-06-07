from ivm.compat import add_std_compat
from ivm.debugger import Debugger
from ivm.extrinsics import PrimitiveExtValPort
from ivm.host import Host
import os.path

from ivm.tree import N32

host = Host(ivm=Debugger())

add_std_compat(host)
host.parse_file(os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "ivy", "examples", "fib_repl.iv")))
host.execute(
    "::main",
    PrimitiveExtValPort(N32(0))
)