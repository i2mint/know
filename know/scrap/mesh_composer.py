"""
This module experiments with ways to compose signal ML systems from a gallery of
parametrizable components.

The intent is to offer a python interface to the process that emulates the user
experience of a drag and drop GUI.

"""

from dol.sources import AttrContainer
from operator import itemgetter
import numpy as np
from typing import Any, Iterable, Tuple, Optional, Callable
from inspect import signature

from slang.chunkers import fixed_step_chunker, mk_chunker
from slang.featurizers import mk_wf_to_spectr
from slang.spectrop import (
    logarithmic_bands_matrix,
    GeneralProjectionLearner,
    SpectralProjectorSupervisedFitter,
    SpectralProjectorUnsupervisedFitter,
)

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, IncrementalPCA
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.cluster import KMeans
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import Pipeline


from i2.deco import FuncFactory


def identity(obj):
    return obj


from atypes import WfStore


def _attr_name_and_obj_pairs(
    o: Any, obj_filt: Optional[Callable] = None
) -> Iterable[Tuple[str, Any]]:
    obj_filt = obj_filt or (lambda x: True)
    for attr_name in dir(o):
        attr_obj = getattr(o, attr_name)
        if obj_filt(attr_obj):
            yield attr_name, attr_obj


def flat_options(box):
    for kind in box:
        options = getattr(box, kind)
        for option in options:
            yield kind, option


flat_options.dot_string = lambda box: map('.'.join, flat_options(box))


class Box:
    """Experimental container, meant to evolve into something that has some dynamic,
    context-based help (such as wrapping functions with defaults that are changed
    according to the context, filtering the function proposals according to the
    context (e.g. the functions already used in a pipeline) etc.

    Note: Most of the time, making a AttrContainer instance is good enough.
    In fact, at the point of writing this, Box does nothing extra (no data binding).

    """

    def __iter__(self):
        yield from map(
            itemgetter(0),
            _attr_name_and_obj_pairs(
                self, obj_filt=lambda x: isinstance(x, AttrContainer)
            ),
        )


def box_items(box, path=()):
    """Creates items of a flat mapping of the input box,
    where keys are key tuples and values are the leafs of the input box
    """
    for k in box:
        v = getattr(box, k)
        if isinstance(v, (AttrContainer, Box)):
            yield from box_items(v, path)
        else:
            yield path + (k,), v


# def kv_to_box(kv_items):
#     for k, v in kv_items:
#         pass


class MyBox(Box):
    wf_store = AttrContainer()
    chunker = AttrContainer(fixed_step=mk_chunker)
    featurizer = AttrContainer(
        fft=mk_wf_to_spectr,
        # we need no parametrization, so we use FuncFactory.func_returning_obj to wrap
        # std in a factory:
        vol=FuncFactory.func_returning_obj(np.std),
    )
    learner = AttrContainer(
        # Note that none of these have names. We use AttrContainer's auto namer here
        StandardScaler,
        MinMaxScaler,
        PCA,
        IncrementalPCA,
        LinearRegression,
        LogisticRegression,
        KMeans,
        LinearDiscriminantAnalysis,
        logarithmic_bands_matrix,
        GeneralProjectionLearner,
        SpectralProjectorSupervisedFitter,
        SpectralProjectorUnsupervisedFitter,
    )


def test_mybox():
    assert list(MyBox.featurizer) == ['fft', 'vol']
    assert 'StandardScaler' in MyBox.learner
    assert MyBox.learner.StandardScaler == StandardScaler


test_mybox()


# ---------------------------------------------------------------------------------------


import wrapt
from i2 import Sig, call_forgivingly
from functools import partial

#
# def with_keyword_only_arguments(*, validator=None):
#     @wrapt.decorator
#     def wrapper(wrapped, instance, args, kwargs):
#         sig = Sig(wrapped)
#         call_forgivingly(validator, *args, **kwargs)
#         return wrapped(*args, **kwargs)
#
#     return wrapper
#
#
# def raise_if_false(*, validator=None):
#     @wrapt.decorator
#     def wrapper(wrapped, instance, args, kwargs):
#         sig = Sig(wrapped)
#         call_forgivingly(validator, *args, **kwargs)
#         return wrapped(*args, **kwargs)
#
#     return wrapper


class ValidationError(ValueError, TypeError):
    """To be raised when there's a validation error"""


# Works, but not picklable
# Due to https://github.com/GrahamDumpleton/wrapt/issues/102 still open?
def add_validation(*, validator=None, raise_obj=ValidationError('Validation error')):
    @wrapt.decorator
    def raise_if_false(wrapped, instance, args, kwargs):
        output = wrapped(*args, **kwargs)
        if not validator(output):
            raise raise_obj
        return output

    return raise_if_false


from i2 import wrap


def _validation_ingress(*args, validator, raise_obj, **kwargs):
    if validator is not None:
        is_valid = call_forgivingly(validator, *args, **kwargs)
        if not is_valid:
            raise raise_obj
    return args, kwargs


# Works, but not picklable
def add_validation(*, validator=None, raise_obj=ValidationError('Validation error')):
    return partial(
        wrap,
        ingress=partial(_validation_ingress, validator=validator, raise_obj=raise_obj),
    )


def test_validator():
    def my_validator(x):
        return len(x) == 3

    @add_validation(validator=my_validator)
    def foo(x):
        return x

    assert foo([1, 2, 3]) == [1, 2, 3]

    import pytest

    with pytest.raises(ValidationError):
        foo([1, 2])  # not of size 3 so should fail

    # TODO: Make pickling work!!!
    # from tested import validate_codec

    import pickle

    pickle.dumps(foo)
