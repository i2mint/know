"""Util objects"""
from dataclasses import dataclass
from typing import Callable, Any, Iterable, Dict, Mapping, Iterator
import itertools

from i2 import ContextFanout, FuncFanout, MultiObj, Pipe

from atypes import Slab, Hunk, FiltFunc, MyType
from creek import Creek
from creek.util import to_iterator
from know.base import do_not_break, IteratorExit
from taped import chunk_indices

SlabCallback = Callable[[Slab], Any]
Slabs = Iterable[Slab]
HunkerType = Iterable[Hunk]
Stream = Iterable
StreamId = str

always: FiltFunc
Hunker: HunkerType

SlabService = MyType(
    'Consumer', Callable[[Slab], Any], doc='A function that will call slabs iteratively'
)
Name = str
# BoolFunc = Callable[[...], bool]
FiltFunc = Callable[[Any], bool]


class _MultiIterator(MultiObj):
    """Helper class for DictZip"""

    def __init__(self, *unnamed, **named):
        super().__init__(*unnamed, **named)
        self.objects = {k: to_iterator(v) for k, v in self.objects.items()}

    def _gen_next(self):
        for name, iterator in self.objects.items():
            yield name, next(iterator, None)

    def __next__(self) -> dict:
        return dict(self._gen_next())


def asis(x: Any):
    return x


def always_true(x: Any) -> True:
    """Returns True, regardless of input. Meant for filter functions."""
    return True


def always_false(x: Any) -> False:
    """Returns False, regardless of input. Meant for stopping (filter) functions"""
    return False


def any_value_is_none(d: Mapping):
    """Returns True if any value of the mapping is None"""
    return any(d[k] is None for k in d)


def let_through(x):
    return x


def iterate(iterators: Iterable[Iterator]):
    while True:
        items = apply(next, iterators)
        yield items


def iterate_dict_values(iterator_dict: Mapping[Name, Iterator]):
    while True:
        try:
            yield {k: next(v, None) for k, v in iterator_dict.items()}
        except IteratorExit:
            break


apply = Pipe(map, tuple)

StopCondition = Callable[[Any], bool]


# TODO: Make smart default for stop_condition. If finite iterable, use any_value_is_none?
class MultiIterable:
    """Join several iterables together.

    >>> from know.util import any_value_is_none
    >>> from functools import partial
    >>>
    >>> any_value_is_none = lambda d: any(d[k] is None for k in d)
    >>> mk_multi_iterable = partial(MultiIterable, stop_condition=any_value_is_none)
    >>> mi = mk_multi_iterable(lets='abc', nums=[1, 2, 3, 4])
    >>> list(mi)
    [{'lets': 'a', 'nums': 1}, {'lets': 'b', 'nums': 2}, {'lets': 'c', 'nums': 3}]

    >>> mi = MultiIterable(
    ...     x=[5, 4, 3, 2, 1], y=[1, 2, 3, 4, 5],
    ...     stop_condition=lambda d: d['x'] == d['y']
    ... )
    >>> list(mi)
    [{'x': 5, 'y': 1}, {'x': 4, 'y': 2}]
    """

    def __init__(self, *unnamed, stop_condition: StopCondition = always_false, **named):
        self.multi_iterator = _MultiIterator(*unnamed, **named)
        self.iterators = self.multi_iterator.objects
        self.stop_condition = stop_condition

    def __iter__(self):
        while not self.stop_condition(items := next(self.multi_iterator)):
            yield items

    def takewhile(self, predicate=None):
        """itertools.takewhile applied to self, with a bit of syntactic sugar
        There's nothing to stop the iteration"""
        if predicate is None:
            predicate = lambda x: True  # always true
        return itertools.takewhile(predicate, self)


# TODO: Default consumer(s) (e.g. data-safe prints?)
# TODO: Default slabs? (iterate through
@dataclass
class SlabsPushTuple:
    slabs: Iterable[Slab]
    services: Mapping[Name, SlabService]

    def __post_init__(self):
        if isinstance(self.services, FuncFanout):
            self.multi_service = self.services
        else:
            # TODO: Add capability (in FuncFanout) to get a mix of (un)named consumers
            self.multi_service = FuncFanout(**self.services)
        self.slabs_and_services_context = ContextFanout(
            slabs=self.slabs, **self.multi_service
        )

    def __iter__(self):
        with self.slabs_and_services_context:  # enter all contained contexts
            # get an iterable slabs object
            if isinstance(self.slabs, ContextFanout):
                its = tuple(getattr(self.slabs, s) for s in self.slabs)
                slabs = iterate(its)
                # slabs = iterate_dict_values(self.slabs)
            else:
                slabs = self.slabs
            # Now iterate...
            for slab in slabs:
                yield self.multi_service(slab)  # ... calling the services on each slab

    def __call__(
        self, callback: Callable = None, sentinel_func: FiltFunc = None,
    ):
        for multi_service_output in self:
            if callback:
                callback_output = callback(multi_service_output)
                if sentinel_func and sentinel_func(callback_output):
                    break


@dataclass
class SlabsPush:
    slabs: Iterable[Slab]
    services: Mapping[Name, SlabService]

    def __post_init__(self):
        if isinstance(self.services, FuncFanout):
            self.multi_service = self.services
        else:
            # TODO: Add capability (in FuncFanout) to get a mix of (un)named consumers
            self.multi_service = FuncFanout(**self.services)
        # Put slabs and multi_services in a ContextFanout so that
        # anything that needs to be contextualized, will.
        self.slabs_and_services_context = ContextFanout(
            slabs=self.slabs, **self.multi_service
        )

    def __iter__(self):
        with self.slabs_and_services_context:  # enter all contained contexts
            # get an iterable slabs object
            # TODO: not sure this ContextFanout is the right check
            if isinstance(self.slabs, ContextFanout):
                slabs = iterate_dict_values(self.slabs)
            else:
                slabs = self.slabs
            # Now iterate...
            for slab in slabs:
                yield self.multi_service(slab)  # ... calling the services on each slab

    def __call__(
        self, callback: Callable = None, sentinel_func: FiltFunc = None,
    ):
        for multi_service_output in self:
            if callback:
                callback_output = callback(multi_service_output)
                if sentinel_func and sentinel_func(callback_output):
                    break


do_not_break.__doc__ = (
    'Sentinel that should be used to signal SlabsIter iteration not to break. '
    'This sentinel should be returned by exception handlers if they want to tell '
    'the iteration not to stop (in all other cases, the iteration will stop)'
)


class DictZip:
    def __init__(self, *unnamed, takewhile=None, **named):
        self.multi_iterator = _MultiIterator(*unnamed, **named)
        self.objects = self.multi_iterator.objects
        if takewhile is None:
            takewhile = always_true
        self.takewhile = takewhile

    def __iter__(self):
        while self.takewhile(d := next(self.multi_iterator)):
            yield d


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


#
# from i2 import Pipe
# from typing import Iterable
# from typing import Iterator
#
#
# def iterate(
#     iterators: Iterable[Iterator],
#     stop_condition: Callable[[Iterable], bool] = always_false,
# ):
#     # TODO: Ensure iterators
#     while not stop_condition(items := tuple(map(next, iterators))):
#         yield items
#
#
# from i2.multi_object import MultiObj
#
#
# class MultiIterator(MultiObj):
#     def _gen_next(self):
#         for name, iterator in self.objects.items():
#             yield name, next(iterator)
#
#     def __next__(self):
#         return dict(self._gen_next())
#
#
#
# # NOTE: Just zip?
# class MultiIter:
#     def __init__(self, *iterables):
#         self.iterables = iterables
#
#     def __iter__(self):
#         yield from self.iterables
