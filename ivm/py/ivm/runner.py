from io import TextIOWrapper, StringIO

from ivm.compat import add_std_compat
from ivm.debugger import attach_debugger_to
from ivm.extrinsics import PrimitiveExtValPort
from ivm.host import Host
import os.path

from ivm.tree import N32


stdin = StringIO("9\n")
stdout = StringIO()

host = Host(stdin=stdin, stdout=stdout)
add_std_compat(host)
# attach_debugger_to(host)

host.parse_file(os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "ivy", "examples", "fizzbuzz.iv")))
host.execute(
    "::main",
    PrimitiveExtValPort(N32(0))
)

print("Output:")
print(stdout.getvalue())