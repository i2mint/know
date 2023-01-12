"""A module to jot down ideas around configuration operations"""
import pprint
from typing import Mapping, Callable
from dol.sources import AttrContainer, AttrDict
from i2 import Sig

from streamlitfront.spec_maker import DFLT_CONVENTION_DICT


def _transformed_items(
    d: Mapping, trans: Callable, trans_condition: Callable[..., bool]
):
    for k, v in d.items():
        if trans_condition(v):
            v = trans(v)
        yield k, v


class Box(AttrDict):
    def __repr__(self):
        return repr(self._source)

    def _dict_items(self):
        for k, v in self.items():
            if isinstance(v, Box):
                v = v._to_dict()
            yield k, v

    @classmethod
    def _from_dict(cls, d: Mapping):
        d_type = type(d)
        d = dict(
            _transformed_items(
                d, trans=cls._from_dict, trans_condition=lambda x: isinstance(x, d_type)
            )
        )
        return cls(**d)

    def _to_dict(self):
        cls = type(self)
        return dict(
            _transformed_items(
                self, trans=cls._to_dict, trans_condition=lambda x: isinstance(x, cls)
            )
        )

    def __str__(self):
        return pprint.pformat(self._to_dict())


def insert_attrs_in_box_subclass(b: Box):
    kwargs = dict(b)
    B = type('B', (Box,), kwargs)
    return B(**kwargs)


class FactoryDictSpec:
    """Make dict specifications of partial functions"""

    def __init__(self, func, func_field, allow_partial=True):
        self.func = func
        self.func_field = func_field
        self.allow_partial = allow_partial
        self._sig = Sig(func)
        self._sig(self)

    def __call__(
        self, *args, **kwargs,
    ):
        _kwargs = self._sig.kwargs_from_args_and_kwargs(
            args, kwargs, allow_partial=self.allow_partial
        )
        return dict({self.func_field: self.func}, **_kwargs)


def get_streamlitfront_convention():
    from streamlitfront.spec_maker import TextSection, ExecSection, App, ELEMENT_KEY

    return Box(
        app=Box(title='My Streamlit Front Application'),
        rendering=Box(
            element=App,
            Callable=Box(
                description=Box(_front_element=TextSection),
                execution=FactoryDictSpec(ExecSection, func_field=ELEMENT_KEY),
            ),
        ),
    )


def test_streamlitfront_convention_ops():
    c = get_streamlitfront_convention()
    c = insert_attrs_in_box_subclass(c)  # (bad) hack to make pycharm see the attrs
    # TODO: Change this bad hack (use __getattr__? descriptor?)
    print('Before ops', c, '', sep='\n')

    # And now, edit the convention (copy) to make the specs/configs
    # change title:
    c.app.title = 'My own title'

    # remove description
    del c.rendering.Callable.description

    # See the changed specs
    print('After ops', c, '', sep='\n')


# ---------------------------------------------------------------------------------------
# Alternatives to mappings for front configs.

from i2.deco import FuncFactory
from i2 import LiteralVal
from typing import Any

from streamlitfront.elements import ExecSection
from streamlitfront.spec_maker import (
    APP_KEY,
    ELEMENT_KEY,
    RENDERING_KEY,
    App,
    View,
    TextSection,
    IntInput,
    FloatInput,
    TextInput,
    TextOutput,
)


_DFLT_CONVENTION_DICT = {
    APP_KEY: {'title': 'My Streamlit Front Application'},
    RENDERING_KEY: {
        ELEMENT_KEY: App,
        Callable: {
            ELEMENT_KEY: View,
            'description': {ELEMENT_KEY: TextSection,},
            'execution': {
                ELEMENT_KEY: ExecSection,
                'inputs': {
                    int: {ELEMENT_KEY: IntInput,},
                    float: {ELEMENT_KEY: FloatInput,},
                    Any: {ELEMENT_KEY: TextInput,},
                },
                'output': {ELEMENT_KEY: TextOutput,},
            },
        },
    },
}
# Can use partials
from functools import partial

render_1 = partial(
    View,
    description=partial(TextSection),
    execution=partial(
        ExecSection,
        inputs={
            int: partial(IntInput),
            float: partial(IntInput),
            Any: partial(TextInput),
        },
        output=partial(TextOutput),
    ),
)

# If you want to have signature help when making your partials, you can use
# FuncFactory instead.
from i2.deco import FuncFactory

render_2 = FuncFactory(View)(
    description=FuncFactory(TextSection),
    execution=FuncFactory(ExecSection)(
        inputs={
            int: partial(IntInput),
            float: partial(IntInput),
            Any: partial(TextInput),
        },
        output=partial(TextOutput),
    ),
)


# TODO: To make into a plugin where other conditions/types can be registered
# TODO: To align with execution of factory (for custom factories)
def _is_factory(obj):
    return callable(obj) and hasattr(obj, 'func')


def _is_instance(obj, class_or_tuple):
    """Same as isinstance, but partializable"""
    return isinstance(obj, class_or_tuple)


def _ensure_factory_if_callable(
    obj, is_factory=partial(_is_instance, class_or_tuple=partial)
):
    if isinstance(obj, LiteralVal):
        return obj.get_val()  # we want the literal value, get it
    elif callable(obj) and not is_factory(obj):
        return FuncFactory(obj)  # make the callable into a factory if it's not
    else:
        return obj  # just return the object (it's already a factory, or not a callable)


render_3 = FuncFactory(View)(
    description=TextSection,  # factory will be made from callable
    execution=FuncFactory(ExecSection)(
        # Literal: we actually want a function, not a factory here
        inputs={
            int: IntInput,  # factory will be made from callable
            float: IntInput,  # factory will be made from callable
            Any: TextInput,  # factory will be made from callable
        },
        output=TextOutput,
    ),
)

from operator import attrgetter, methodcaller, or_
from functools import reduce
from typing import Iterable

disjunction = partial(reduce, or_)
disjunction = '''disjunction([a, b, ...]) is equivalent to (a or b or ...)

>>> assert disjunction([False, True, False]) == True
>>> assert disjunction([False, False, False]) == False
'''


def get_mapping(obj):
    if isinstance(obj, Mapping):
        return obj
    elif isinstance(obj, partial):
        return obj.keywords
    return None


# TODO: Wait a minute! What about i2.flatten_dict!?
def key_path_and_val_pairs(obj, get_mapping=get_mapping, path=()):
    mapping = get_mapping(obj)
    if mapping is not None:
        for k, v in mapping.items():
            yield from key_path_and_val_pairs(v, get_mapping, path + (k,))
    else:
        yield path, obj


def path_set(d: dict, path: Iterable, val):
    """Sets a val to a path of keys. ``d[(k1, k2)] = 42`` is equivalent to path_set(d,
    (k1, k2), 42)

    >>> d = {'a': 1, 'b': {'c': 2}}
    >>> path_set(d, ['b', 'e'], 42)
    >>> d
    {'a': 1, 'b': {'c': 2, 'e': 42}}
    """
    t = d
    for k in path[:-1]:
        if k in t:
            t = t[k]
        else:
            t[k] = {}
    t[path[-1]] = val


def gather_in_nested_dict(path_val_pairs):
    d = dict()
    for path, val in path_val_pairs:
        path_set(d, path, val)
    return d


def test_ensure_factory_on_render_3():
    print(*key_path_and_val_pairs(render_3), sep='\n')

    from creek.tools import apply_func_to_index

    ensure_factory = partial(
        apply_func_to_index, apply_to_idx=1, func=_ensure_factory_if_callable
    )
    d = gather_in_nested_dict(map(ensure_factory, key_path_and_val_pairs(render_3)))
    return d
