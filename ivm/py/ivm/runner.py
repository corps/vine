import importlib
import sys
from io import BytesIO, TextIOWrapper

from ivm.compat import add_std_compat
from ivm.debugger import attach_debugger_to
from ivm.extrinsics import PrimitiveExtValPort
from ivm.host import Host
import os.path
import argparse

from ivm.tree import N32


def main():
    parser = argparse.ArgumentParser(description="A python ivm runner and debugger")
    parser.add_argument("--file", type=str, help="iv file to be run")
    parser.add_argument(
        "--extension",
        dest="extensions",
        help="python.module.path:function_name to run on the Host object before execution",
    )
    parser.add_argument("--debug", action="store_true", help="Use debugger interface")
    args = parser.parse_args()

    if args.debug:
        host = Host(
            stdin=TextIOWrapper(BytesIO()),
            stdout=TextIOWrapper(BytesIO()),
            stderr=TextIOWrapper(BytesIO()),
        )
        debugger = attach_debugger_to(host)
    else:
        host = Host()
        debugger = None
    add_std_compat(host)

    if args.extensions:
        for extension in args.extensions:
            module_name, function_name = extension.split(":")
            module = importlib.import_module(module_name)
            getattr(module, function_name)(host)

    if os.path.isfile(args.file):
        host.parse_file(args.file)
    else:
        print(f"File not found: {args.file}", file=sys.stderr)

    host.boot("::main", PrimitiveExtValPort(N32(0)))

    if debugger is not None:
        debugger.run()
        print(host.stdout.buffer.getvalue().decode("utf-8"))
    else:
        host.execute()

    if __name__ == "__main__":
        main()
