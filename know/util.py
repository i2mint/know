"""Util objects"""
from dataclasses import dataclass
from typing import Callable, Any, Iterable

from i2 import ContextFanout, FuncFanout

from atypes import Slab
from creek import Creek
from taped import chunk_indices

SlabCallback = Callable[[Slab], Any]


@dataclass
class LiveProcess:
    slabs: Iterable[Slab]
    slab_callback: SlabCallback

    def __call__(self):
        with ContextFanout(self.slabs, self.slab_callback):
            for slab in self.slabs:
                callback_output = self.slab_callback(slab)

        return callback_output


# TODO: Weird subclassing. Not the Creek init. Consider factory or delegation
class Hunker(Creek):
    def __init__(self, src, chk_size, chk_step=None, start_idx=0, end_idx=None):
        intervals = chunk_indices(
            chk_size=chk_size, chk_step=chk_step, start_idx=start_idx, end_idx=end_idx
        )
        super().__init__(stream=intervals)
        self.src = src

    def data_to_obj(self, data):
        return self.src[slice(*data)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass