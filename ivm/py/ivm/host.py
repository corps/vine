import dataclasses
from typing import Any, Callable

from ivm.extrinsics import ExtValPort, ExtFnPort
from ivm.globals import Global
from ivm.readback import ExtrinsicsCache
from ivm.vm import IVM


@dataclasses.dataclass
class Host:
    ivm: IVM = dataclasses.field(default_factory=lambda: IVM())
    gs: dict[str, Global] = dataclasses.field(default_factory=dict)
    cache: ExtrinsicsCache = dataclasses.field(
        default_factory=lambda: ExtrinsicsCache()
    )

    def __post_init__(self):
        self.cache.install_into(self.ivm.extrinsics)

    def add_constant(self, val: Any) -> ExtValPort:
        return self.cache.add_new_val(val)

    def add_ext_fun(self, c: Callable[[Any, Any], ExtValPort]) -> None:
        self.ivm.extrinsics.ext_fns[c.__name__] = c

    def parse_file(self, filename: str):
        pass
