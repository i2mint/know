"""pieces of thing for inspiration

"""
import itertools
from dataclasses import dataclass
from itertools import takewhile as itertools_takewhile

from atypes import Slab
from creek import Creek
from creek.util import to_iterator
from i2 import MultiObj, FuncFanout, ContextFanout, Pipe
from typing import Callable, Iterable, Iterator, Any, Mapping, Dict
from i2 import Pipe
from know.util import (
    Name,
    SlabService,
    iterate,
    FiltFunc,
    iterate_dict_values,
    always_false,
    always_true,
    StreamId,
    Stream,
    SlabCallback,
    HunkerType,
)
from taped import chunk_indices

always: FiltFunc
Hunker: HunkerType


class MultiIterator(MultiObj):
    def _gen_next(self):
        for name, iterator in self.objects.items():
            yield name, next(iterator, None)

    def __next__(self) -> dict:
        return dict(self._gen_next())


# TODO: Make smart default for stop_condition. If finite iterable, use any_value_is_none?

no_more_data = type('no_more_data', (), {})


# class DictZip:
#     def __init__(self, *unnamed, takewhile=None, **named):
#         self.multi_iterator = MultiIterator(*unnamed, **named)
#         self.objects = self.multi_iterator.objects
#         self.takewhile = takewhile
#
#     def __iter__(self):
#         while True:
#             x = next(self.multi_iterator)
#             if not self.takewhile(x):
#                 break
#             yield x

#
# class MultiIterable:
#     def __init__(self, *unnamed, **named):
#         self.multi_iterator = MultiIterator(*unnamed, **named)
#         self.objects = self.multi_iterator.objects
#
#     def __iter__(self):
#         while True:
#             yield next(self.multi_iterator)
#
#     def takewhile(self, predicate=None):
#         """itertools.takewhile applied to self, with a bit of syntactic sugar
#         There's nothing to stop the iteration"""
#         if predicate is None:
#             predicate = lambda x: True  # always true
#         return itertools_takewhile(predicate, self)


def test_multi_iterator():
    # get_multi_iterable = lambda: MultiIterable(
    #     audio=iter([1, 2, 3]), keyboard=iter([4, 5, 6])
    # )

    def is_none(x):
        return x is None

    def is_not_none(x):
        return x is not None

    # Note: Equivalent to any_non_none_value = Pipe(methodcaller('values'), iterize(
    # is_not_none), any)
    def any_non_none_value(d: dict):
        """True if and only if d has any non-None values

        >>> assert not any_non_none_value({'a': None, 'b': None})
        >>> assert any_non_none_value({'a': None, 'b': 3})
        """
        return any(map(is_not_none, d.values()))

    # Note: Does not work (never stops)
    # get_multi_iterable = lambda: MultiIterable(
    #     audio=iter([1, 2, 3]),
    #     keyboard=iter([4, 5, 6])
    # )

    get_multi_iterable = lambda: DictZip(
        audio=iter([1, 2, 3]), keyboard=iter([4, 5, 6]), takewhile=any_non_none_value,
    )

    m = get_multi_iterable()
    assert list(m.objects) == ['audio', 'keyboard']

    from functools import partial

    def if_then_else(x, then_func, else_func, if_func):
        if if_func(x):
            return then_func(x)
        else:
            return else_func(x)

    call_if_not_none = partial(
        if_then_else, if_func=lambda x: x is not None, else_func=lambda x: None
    )
    #
    predicate = partial(call_if_not_none, then_func=lambda x: sum(x.values()) < 7)

    def predicate(x):
        if x is not None:
            return any(v is not None for v in x.values())
        else:
            return False

    m = get_multi_iterable()

    assert list(m) == [
        {'audio': 1, 'keyboard': 4},
        {'audio': 2, 'keyboard': 5},
        {'audio': 3, 'keyboard': 6},
    ]


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


StopCondition = Callable[[Any], bool]


# TODO: Make smart default for stop_condition. If finite iterable, use any_value_is_none?
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


apply = Pipe(map, tuple)


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
