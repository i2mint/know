"""pieces of thing for inspiration

"""
from itertools import takewhile as itertools_takewhile
from i2 import MultiObj
from typing import Callable, Iterable, Iterator
from i2 import Pipe


class MultiIterator(MultiObj):
    def _gen_next(self):
        for name, iterator in self.objects.items():
            yield name, next(iterator, None)

    def __next__(self) -> dict:
        return dict(self._gen_next())


no_more_data = type('no_more_data', (), {})


class DictZip:
    def __init__(self, *unnamed, takewhile=None, **named):
        self.multi_iterator = MultiIterator(*unnamed, **named)
        self.objects = self.multi_iterator.objects
        self.takewhile = takewhile

    def __iter__(self):
        while True:
            x = next(self.multi_iterator)
            if not self.takewhile(x):
                break
            yield x


class MultiIterable:
    def __init__(self, *unnamed, **named):
        self.multi_iterator = MultiIterator(*unnamed, **named)
        self.objects = self.multi_iterator.objects

    def __iter__(self):
        while True:
            yield next(self.multi_iterator)

    def takewhile(self, predicate=None):
        """itertools.takewhile applied to self, with a bit of syntactic sugar
        There's nothing to stop the iteration"""
        if predicate is None:
            predicate = lambda x: True  # always true
        return itertools_takewhile(predicate, self)


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

    #
    # get_multi_iterable = lambda: DictZip(
    #     audio=iter([1, 2, 3]),
    #     keyboard=iter([4, 5, 6]),
    #     takewhile=lambda x: x is not None
    # )
    #
    # m = get_multi_iterable()
    # assert list(m.objects) == ['audio', 'keyboard']
    #
    # from functools import partial
    #
    # def if_then_else(x, then_func, else_func, if_func):
    #     if if_func(x):
    #         return then_func(x)
    #     else:
    #         return else_func(x)
    #
    # call_if_not_none = partial(
    #     if_then_else, if_func=lambda x: x is not None, else_func=lambda x: None
    # )
    #
    # predicate = partial(call_if_not_none, then_func=lambda x: sum(x.values()) < 7)
    #
    # def predicate(x):
    #     if x is not None:
    #         return any(v is not None for v in x.values())
    #     else:
    #         return False
    #
    # m = get_multi_iterable()
    # assert list(m) == [
    #     {'audio': 1, 'keyboard': 4},
    #     {'audio': 2, 'keyboard': 5},
    #     {'audio': 3, 'keyboard': 6},
    # ]
    #
    # # iter(callable, sentinel) use pattern
    # # It would have been desirable to provide the tools to be able to use
    # # more known iter(callable, sentinel) pattern, but I had difficulty squeezing
    # # my use case into it. The best I could do was below.
    # # Required:
    # # - a multi_iter_zip (zip, for lists of dicts)
    # # - a wrapper to produce a given sentinel when a given condition is met
    # # - an object that makes a callable (yielding next item) from an iterable
    #
    # get_multi_iterator = lambda: MultiIterator(
    #     audio=iter([1, 2, 3]), keyboard=iter([4, 5, 6])
    # )
    #
    # m = get_multi_iterator()
    # assert list(zip(*m)) == [(1, 4), (2, 5), (3, 6)]
    #
    # from i2 import Pipe
    #
    # m = get_multi_iterator()
    # dict_zip = Pipe(partial(zip, m.objects), dict)
    # multi_iter_zip = lambda m: map(dict_zip, zip(*m))
    # assert list(multi_iter_zip(m)) == [
    #     {'audio': 1, 'keyboard': 4},
    #     {'audio': 2, 'keyboard': 5},
    #     {'audio': 3, 'keyboard': 6},
    # ]
    #
    # def sentinel_on_condition(x, bool_func, sentinel=None):
    #     if bool_func(x):
    #         return sentinel
    #     return x
    #
    # class Iter:
    #     def __init__(self, iterator):
    #         self.iterator = iterator
    #
    #     def __call__(self):
    #         return next(self.iterator)
    #
    # none_on_cond = partial(sentinel_on_condition, bool_func=cond)
    #
    # m = get_multi_iterator()
    # assert list(iter(Iter(map(none_on_cond, multi_iter_zip(m))), None)) == [
    #     {'audio': 1, 'keyboard': 4},
    #     {'audio': 2, 'keyboard': 5},
    #     # {'audio': 3, 'keyboard': 6}
    # ]


# test_multi_iterator()

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

# def iterate(
#         iterators: Iterable[Iterator],
#         stop_condition: Callable[[Iterable], bool] = lambda x: False,
# ):
#     # TODO: Meant to ensure iterator, but not working. Repair:
#     # iterators = apply(iter, iterators)
#     while True:
#         items = apply(next, iterators)
#         yield items
#         if stop_condition(items):
#             break
#
# apply = Pipe(map, tuple)
#
#
