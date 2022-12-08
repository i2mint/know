"""Generally useful stuff"""

# --------------------------------------------------------------------------------------
# General
from typing import Callable
from i2 import Pipe
from i2.deco import FuncFactory
from collections import Counter, ChainMap

# from i2.wrapper import include_exclude

# The following is just so linting does complain about the imports of the these objects,
# which might lead to their inadvertent deletion.
_ = FuncFactory, ChainMap, Counter


def identity(x):
    return x


def mk_pipe(
    name: str = '',
    doc: str = '',
    f1: Callable = identity,
    f2: Callable = identity,
    f3: Callable = identity,
    f4: Callable = identity,
    f5: Callable = identity,
    f6: Callable = identity,
):
    """
    The only purpose for this function is to enable Pipe instances to be
    created in front since we don't have *args handling yet (well... anymore).
    """
    return Pipe(f1, f2, f3, f4, f5, f6, __name__=name, __doc__=doc)
