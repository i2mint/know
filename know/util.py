"""Util objects"""


def merge_unnamed_and_named(*unnamed, **named):
    """To merge unnamed and named arguments into a single (named) dict of arguments

    >>> merge_unnamed_and_named(10, 20, thirty=30, fourty=40)
    {'_0': 10, '_1': 20, 'thirty': 30, 'fourty': 40}
    """
    named_unnamed = {f'_{i}': obj for i, obj in enumerate(unnamed)}
    if not named_unnamed.keys().isdisjoint(named):
        raise ValueError(
            f"Some of your objects' names clashed: "
            f'{named_unnamed.keys() & named.keys()}'
        )
    return dict(named_unnamed, **named)


class ContextFanout:
    """Encapsulates multiple objects into a single context manager that will enter and
    exit all objects that are context managers themselves.

    Context managers show up in situations where you need to have some setup and tear
    down before performing some tasks. It's what you get when you open a file to read
    or write in it, or open a data-base connection, etc.

    Sometimes you need to perform a task that involves more than one context managers,
    or even some objects that may or may not be context managers.
    What `ContextFanout` does for you is allow you to bundle all those (perhaps)
    context managers together, and use them as one single context manager.

    In python 3.10+ you can bundle contexts together by specifying a tuple of context
    managers, as such:

    ```python
    with (open('file.txt'), another_context_manager):
        ...
    ```

    But
    - Python will complain if one of the members of the tuple is not a context manager.
    - A tuple of context managers is not a context manager itself, it's just understood
    by the with (in python 3.10+).

    As an example, let's take two objects. One is a context manager, the other not.

    >>> from contextlib import contextmanager
    >>> @contextmanager
    ... def some_context_manager(x):
    ...     print('open')
    ...     yield f'x + 1 = {x + 1}'
    ...     print('close')
    ...
    >>> def not_a_context_manager(x):
    ...     return x - 1
    ...


    >>> c = ContextFanout(
    ...     some_context_manager=some_context_manager(2),
    ...     not_a_context_manager=not_a_context_manager
    ... )

    See from the prints that "with-ing" c triggers the enter and exit of
    `some_context_manager`:

    >>> with c:
    ...     pass
    open
    close

    Further, know that within (and only within) the context's scope, a `ContextFanout`
    instance will have the context managers it contains available, and having the
    value it is supposed to have "under context".

    >>> c = ContextFanout(
    ...     some_context_manager=some_context_manager(2),
    ...     not_a_context_manager=not_a_context_manager
    ... )
    >>> # first c doesn't have the some_context_manager attribute
    >>> assert not hasattr(c, 'some_context_manager')
    >>> with c:
    ...     # inside the context, c indeed has the attribute, and it has the expected value
    ...     assert c.some_context_manager == 'x + 1 = 3'
    open
    close
    >>> # outside the context, c doesn't have the some_context_manager attribute any more again
    >>> assert not hasattr(c, 'some_context_manager')

    If you don't specify a name for a given context manager, you'll still have access
    to it via a hidden attribute ("_i" where i is the index of the object when
    the `ContextFanout` instance was made.

    >>> c = ContextFanout(some_context_manager(10), not_a_context_manager)
    >>> with c:
    ...     assert c._0 == 'x + 1 = 11'
    open
    close

    """

    def __init__(self, *unnamed_objects, **objects):
        self.objects = merge_unnamed_and_named(*unnamed_objects, **objects)

    def __enter__(self):
        for name, obj in self.objects.items():
            if hasattr(obj, '__enter__'):
                setattr(self, name, obj.__enter__())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for name, obj in self.objects.items():
            if hasattr(obj, '__exit__'):
                obj.__exit__(exc_type, exc_val, exc_tb)
                delattr(self, name)


class FuncFanout:
    """Applies multiple functions to the same argument(s) and returns a dict of results.

    >>> def foo(a):
    ...     return a + 2
    ...
    >>> def bar(a):
    ...     return a * 2
    ...
    >>> def groot(a):
    ...     return 'I am groot'
    ...
    >>> m = FuncFanout(foo, bar, groot)
    >>>
    >>> m(3)
    {'_0': 5, '_1': 6, '_2': 'I am groot'}
    >>>

    If you specify names to the input functions, they'll be used in the dict

    >>> m = FuncFanout(foo, bar_results=bar, groot=groot)
    >>> m(10)
    {'_0': 12, 'bar_results': 20, 'groot': 'I am groot'}
    """

    def __init__(self, *unnamed_consumers, **named_consumers):
        self.consumers = merge_unnamed_and_named(*unnamed_consumers, **named_consumers)

    def call_generator(self, *args, **kwargs):
        for name, consumer in self.consumers.items():
            yield name, consumer(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return dict(self.call_generator(*args, **kwargs))
