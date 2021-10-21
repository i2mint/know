"""pieces of thing for inspiration"""
from itertools import takewhile as itertools_takewhile
from i2.multi_object import MultiObj
from typing import Callable, Iterable, Iterator
from i2 import Pipe


# Note: Strange to have iter_until instead of just using __iter__.
#  Tempted to delegate MultiObj instead, and use __iter__ (now used to list fields).
#  But
#    (1) should the `MultiIterator` object be both an iterator AND an iterable?
#    (2) need to fix stop_cond and include_last in init
# Note: Maybe iter_until and iter_while are better left as external funcs only?
class MultiIterator(MultiObj):
    def _gen_next(self):
        for name, iterator in self.objects.items():
            yield name, next(iterator, None)

    def __next__(self):
        return dict(self._gen_next())

no_more_data = type('no_more_data', (), {})


class MultiIterable:
    def __init__(self, *unnamed, **named):
        self.multi_iterator = MultiIterator(*unnamed, **named)
        self.objects = self.multi_iterator.objects

    def __iter__(self):
        while True:
            yield next(self.multi_iterator)
            # x = next(self.multi_iterator, no_more_data)
            # if x is no_more_data:
            #     break
            # yield x

    def takewhile(self, predicate=None):
        # yield from iterate(self.values())
        if predicate is None:
            predicate = lambda x: True  # always true
        return itertools_takewhile(predicate, self)

    # def iterate(self, stop_condition=lambda x: ):
    #     while True:
    #         items = apply(next, iterators)
    #         yield items
    #         if stop_condition(items):
    #             break


def iterate(
        iterators: Iterable[Iterator],
        stop_condition: Callable[[Iterable], bool] = lambda x: False,
):
    # TODO: Meant to ensure iterator, but not working. Repair:
    # iterators = apply(iter, iterators)
    while True:
        items = apply(next, iterators)
        yield items
        if stop_condition(items):
            break

apply = Pipe(map, tuple)


# def _ensure_predicate_is_callable(stop_cond):
#     if not isinstance(stop_cond, Callable):
#         stop_val = stop_cond
#         stop_cond = lambda item: item == stop_val
#     assert isinstance(stop_cond, Callable), f'stop_cond not callable: {stop_cond}'
#
#
# def iter_until_condition(iterator, stop_cond=None, include_last=False):
#     stop_cond = _ensure_predicate_is_callable(stop_cond)  # Pattern: Postel
#     while True:
#         item = next(iterator)
#         if stop_cond(item):
#             if include_last:
#                 yield item
#             break
#         yield item
#
#
# def iter_while_condition(iterator, stop_cond):
#     stop_cond = _ensure_predicate_is_callable(stop_cond)  # Pattern: Postel
#     while True:
#         item = next(iterator)
#         if stop_cond(item):
#             yield item
#         else:
#             break


def test_multi_iterator():
    get_multi_iterator = lambda: MultiIterator(
        audio=iter([1, 2, 3]), keyboard=iter([4, 5, 6])
    )

    m = get_multi_iterator()
    assert list(m.objects) == ['audio', 'keyboard']

    from functools import partial

    # gen is basically

    cond = lambda x: sum(x.values()) > 7

    m = get_multi_iterator()

    assert list(itertools_takewhile(m, cond)) == [
        {'audio': 1, 'keyboard': 4},
        {'audio': 2, 'keyboard': 5},
        # {'audio': 3, 'keyboard': 6}
    ]

    # iter_until was made to resemble the iter(callable, sentinel) use pattern
    # It would have been desirable to provide the tools to be able to use the above
    # pattern,
    # but the best I could do was below.
    # Required
    # - a multi_iter_zip (zip, for lists of dicts)
    # - a wrapper to produce a given sentinel when a given condition is met
    # - an object that makes a callable (yielding next item) from an iterable

    m = get_multi_iterator()
    assert list(zip(*m)) == [(1, 4), (2, 5), (3, 6)]

    from i2 import Pipe

    m = get_multi_iterator()
    dict_zip = Pipe(partial(zip, m.objects), dict)
    multi_iter_zip = lambda m: map(dict_zip, zip(*m))
    assert list(multi_iter_zip(m)) == [
        {'audio': 1, 'keyboard': 4},
        {'audio': 2, 'keyboard': 5},
        {'audio': 3, 'keyboard': 6},
    ]

    def sentinel_on_condition(x, bool_func, sentinel=None):
        if bool_func(x):
            return sentinel
        return x

    class Iter:
        def __init__(self, iterator):
            self.iterator = iterator

        def __call__(self):
            return next(self.iterator)

    none_on_cond = partial(sentinel_on_condition, bool_func=cond)

    m = get_multi_iterator()
    assert list(iter(Iter(map(none_on_cond, multi_iter_zip(m))), None)) == [
        {'audio': 1, 'keyboard': 4},
        {'audio': 2, 'keyboard': 5},
        # {'audio': 3, 'keyboard': 6}
    ]
