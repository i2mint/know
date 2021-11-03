"""To explore different architectures"""

from dataclasses import dataclass
from typing import Callable, Iterable, Any
from atypes import Slab, MyType
from i2.multi_object import FuncFanout

Consumer = MyType(
    'Consumer', Callable[[Slab], Any], doc="A function that will call slabs iteratively"
)

# TODO: Default consumer(s) (e.g. data-safe prints?)
# TODO: Default slabs? (iterate through
@dataclass
class WithSlabs:
    slabs: Iterable[Slab]
    services: Iterable[Consumer]

    def __post_init__(self):
        if isinstance(self.services, FuncFanout):
            self.multi_service = self.services
        else:
            # TODO: Add capability (in FuncFanout) to get a mix of (un)named consumers
            self.multi_service = FuncFanout(*self.services)

    def __iter__(self):
        for slab in self.slabs:
            yield self.multi_service(slab)

    def __call__(self, callback=None):
        for multi_service_output in self:
            if callback:
                callback(multi_service_output)



