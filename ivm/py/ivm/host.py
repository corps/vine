import dataclasses
import sys
from typing import Any, Callable, TextIO

from ivm.extrinsics import ExtValPort
from ivm.globals import Global
from ivm.parser import IvyParser
from ivm.readback import ExtrinsicsCache
from ivm.serialize import insert_nets
from ivm.vm import IVM


@dataclasses.dataclass
class Host:
    ivm: IVM = dataclasses.field(default_factory=lambda: IVM())
    gs: dict[str, Global] = dataclasses.field(default_factory=dict)
    cache: ExtrinsicsCache = dataclasses.field(
        default_factory=lambda: ExtrinsicsCache()
    )
    stdout: TextIO = sys.stdout
    stderr: TextIO = sys.stderr
    stdin: TextIO = sys.stdin

    def __post_init__(self):
        self.cache.install_into(self.ivm.extrinsics)

    def add_constant(self, val: Any) -> ExtValPort:
        return self.cache.add_new_val(val)

    def add_ext_fun(self, c: Callable[[Any, Any], ExtValPort]) -> None:
        self.ivm.extrinsics.ext_fns[c.__name__] = c

    def parse_file(self, filename: str):
        self.gs = insert_nets(self.ivm, IvyParser.from_file(filename).parse_nets())

    def boot(self, global_name: str, value: ExtValPort) -> None:
        self.ivm.boot(self.gs[global_name], value)

    def execute(self) -> None:
        for _ in self.ivm.normalize():
            pass
