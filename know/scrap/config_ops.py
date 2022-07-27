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
    print("Before ops", c, '', sep='\n')

    # And now, edit the convention (copy) to make the specs/configs
    # change title:
    c.app.title = 'My own title'

    # remove description
    del c.rendering.Callable.description

    # See the changed specs
    print("After ops", c, '', sep='\n')

