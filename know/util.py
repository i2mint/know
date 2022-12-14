"""Util objects"""
from typing import Callable, Any, Iterable, Mapping, Iterator, NewType

from atypes import Slab, Hunk, FiltFunc, MyType, Sliceable
from creek.util import to_iterator
from know.base import IteratorExit

SlabCallback = Callable[[Slab], Any]
Slabs = Iterable[Slab]
HunkerType = Iterable[Hunk]
Stream = Iterable
StreamId = str

SlabService = MyType(
    'Consumer', Callable[[Slab], Any], doc='A function that will call slabs iteratively'
)
Name = str
# BoolFunc = Callable[[...], bool]

SliceableFactory = NewType('SliceableFactory', Callable[..., Sliceable])


# def mk_audio_stream():
#     return LiveWf(
#         input_device_index=None,  # if None, will try to guess the device index
#         sr=44100,
#         sample_width=2,
#         chk_size=4096,
#         stream_buffer_size_s=60,
#     )
#

########################################################################################

from typing import Callable, ContextManager, Iterable
from i2 import Sig

# Note: Could re-use ContextFanout, but didn't because I'm not sure the extra
#  functionality is worth the extra complexity/dependence.
#  Notes on how it can be done here: https://github.com/otosense/know/issues/4
class ContextualFunc:
    """Wrap a function so that it's also a multi-context context manager.

    This class makes callable instances that are also context managers.

    This is useful when a function needs specific resources run, which are managed by
    some context managers. What ``ContextualFunc`` does is bring both in one place
    so that the callable is its own context manager instance which you can enter,
    call, and exit.

    Note: This doesn't mean that a ``ContextualFunc`` will enter the context
    automatically when you try to execute it. If this is needed, one can easily
    make such a function with ``ContextualFunc`` though.

    >>> from contextlib import contextmanager
    >>> from i2 import ContextFanout
    >>>
    >>> def mk_test_context(name, enter_obj=None, return_instance=True):
    ...     @contextmanager
    ...     def test_context():
    ...         print(f'entering {name} context')
    ...         yield enter_obj
    ...         print(f'exiting {name} context')
    ...     return test_context()
    >>> foo_context = mk_test_context('foo')
    >>>
    >>> contextual_func = ContextualFunc(
    ...     lambda x: x + 1,
    ...     foo_context
    ... )
    >>>
    >>> with contextual_func:
    ...     print(f"{contextual_func(2)=}")
    ...     print(f"{contextual_func(1414)=}")
    entering foo context
    contextual_func(2)=3
    contextual_func(1414)=1415
    exiting foo context
    >>>
    >>> bar_context = mk_test_context('bar')
    >>> baz_context = mk_test_context('baz')
    >>>
    >>> contextual_func = ContextualFunc(
    ...     lambda x: x + 1,
    ...     bar_context,
    ...     baz_context,
    ... )
    >>> with contextual_func:
    ...     print(f"{contextual_func(2)=}")
    ...     print(f"{contextual_func(1414)=}")
    entering bar context
    entering baz context
    contextual_func(2)=3
    contextual_func(1414)=1415
    exiting bar context
    exiting baz context

    See https://github.com/otosense/know/issues/4 for more info.

    """

    def __init__(
        self,
        func: Callable,
        *contexts: ContextManager,
        **named_contexts: ContextManager,
    ):
        self.func = func
        self.__signature__ = Sig(self.func)
        self.context = ContextFanout(*contexts, **named_contexts)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __enter__(self):
        self.context.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.context.__exit__(exc_type, exc_val, exc_tb)


########################################################################################


from itertools import tee, count
from i2 import ContextFanout, Pipe

apply = Pipe(map, tuple)


def pairwise(iterable):
    's -> (s0,s1), (s1,s2), (s2, s3), ...'
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def fixed_step_chunk_intervals(chk_size, chk_step=None, start=0):
    """A infinite generator of (bt, tt) intervals of fixed size and step.
    Fixed size means all bt - tt are equal and consecutive bts are equidistant.

    >>> chk_intervals = fixed_step_chunk_intervals(chk_size=2, chk_step=0.5, start=3)
    >>> assert [
    ...     next(chk_intervals), next(chk_intervals), next(chk_intervals)
    ... ] == [(3, 5), (3.5, 5.5), (4.0, 6.0)]
    """
    chk_step = chk_step or chk_size
    yield from zip(count(start, chk_step), count(start + chk_size, chk_step))


def slices_gen(sliceable: Sliceable, intervals):
    """Generate slabs by slicing sliceable with given intervals.

    >>> list(slices_gen(list(range(1, 100, 2)), [(1, 3), (2, 7)]))
    [[3, 5], [5, 7, 9, 11, 13]]

    Note that no matter how much data sliceable has, the generator will end once the
    intervals run out, but if we provide an infinite generator of intervals, we could
    get an infinite generator of slices. For example

    >>> alphabet = 'abcdefghijklmnopqrstuvwxyz'
    >>> alphabet[100:110]
    ''

    So

    >>> it = slices_gen(alphabet, fixed_step_chunk_intervals(3, 2, 20))
    >>> next(it), next(it), next(it), next(it), next(it)
    ('uvw', 'wxy', 'yz', '', '')

    If this needs to be avoided, one can use sentinels:

    >>> it = slices_gen(alphabet, fixed_step_chunk_intervals(3, 2, 20))
    >>> it_with_sentinel = iter(it.__next__, '')
    >>> list(iter(it_with_sentinel.__next__, ''))
    ['uvw', 'wxy', 'yz']
    """
    intervals = to_iterator(intervals)
    while (interval := next(intervals, None)) is not None:
        bt, tt = interval
        yield sliceable[bt:tt]


def source_slices(src_factory: SliceableFactory, intervals):
    """Makes a source by calling src_factory(), then slices it with intervals,
    creating an iterator of slabs"""
    src: Sliceable = src_factory()
    with ContextFanout(src, intervals):
        yield from slices_gen(src, intervals)


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
