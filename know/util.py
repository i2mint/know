"""Util objects"""
from dataclasses import dataclass
from typing import Callable, Any, Iterable, Dict, NewType

from i2 import ContextFanout, FuncFanout, MultiObj

from atypes import Slab, Hunk, FiltFunc
from creek import Creek
from taped import chunk_indices

SlabCallback = Callable[[Slab], Any]
Slabs = Iterable[Slab]
HunkerType = Iterable[Hunk]
Stream = Iterable
StreamId = str

always: FiltFunc
Hunker: HunkerType


def asis(x):
    return x


def always_true(x):
    return True


class MultiIterator(MultiObj):
    def _gen_next(self):
        for name, iterator in self.objects.items():
            yield name, next(iterator, None)

    def __next__(self):
        return dict(self._gen_next())


no_more_data = type('no_more_data', (), {})


class DictZip:
    def __init__(self, *unnamed, takewhile=always_true, **named):
        self.multi_iterator = MultiIterator(*unnamed, **named)
        self.objects = self.multi_iterator.objects
        self.takewhile = takewhile

    def __iter__(self):
        while True:
            x = next(self.multi_iterator)
            if not self.takewhile(x):
                break
            yield x


@dataclass
class Slabbing:
    slabs: Slabs
    slab_callback: SlabCallback

    def __call__(self):
        with ContextFanout(self.slabs, self.slab_callback):
            for slab in self.slabs:
                callback_output = self.slab_callback(slab)

        return callback_output


@dataclass
class LiveProcess:
    streams: Dict[StreamId, Stream]
    slab_callback: SlabCallback = print
    walk: Callable = DictZip

    def __call__(self):
        with ContextFanout(self.streams, self.slab_callback):
            slabs = self.walk(self.streams)
            for slab in slabs:
                callback_output = self.slab_callback(slab)

        return callback_output


# TODO: Weird subclassing. Not the Creek init. Consider factory or delegation
class FixedStepHunker(Creek):
    def __init__(self, src, chk_size, chk_step=None, start_idx=0, end_idx=None):
        intervals = chunk_indices(
            chk_size=chk_size, chk_step=chk_step, start_idx=start_idx, end_idx=end_idx
        )
        super().__init__(stream=intervals)
        self.src = src

    def data_to_obj(self, data):
        return self.src[slice(*data)]
