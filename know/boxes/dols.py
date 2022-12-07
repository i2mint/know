"""
Tools to make dols (data object layers).

That is, to make objects that manage the reading and/or writing of persisted data.

"""
from typing import Callable, Iterable, Union
from functools import partial
from operator import itemgetter
import re
import os

import recode
from dol import wrap_kvs, filt_iter, FilesOfZip, Files, Pipe

# The following is just so linting does complain about the imports of the these objects,
# which might lead to their inadvertent deletion.
_ = filt_iter, FilesOfZip, Files


def filter_keys(filt: Union[Callable, Iterable]):
    return filt_iter(filt=filt)


def make_decoder(chk_format='d'):
    encoder, decoder = recode.mk_codec(chk_format)
    return decoder


def key_transformer(key_of_id=None, id_of_key=None):
    return wrap_kvs(key_of_id=key_of_id, id_of_key=id_of_key)


def extract_extension(string):
    _, ext = os.path.splitext(string)
    return ext


def val_transformer(obj_of_data=None):
    return wrap_kvs(obj_of_data=obj_of_data)


def regular_expression_filter(regular_expression: str = '.*'):
    return re.compile(regular_expression).search


def _function_conjunction(*args, func1, func2, **kwargs):
    return func1(*args, **kwargs) and func2(*args, **kwargs)


def make_function_conjunction(func1, func2):
    return partial(_function_conjunction, func1=func1, func2=func2)


read_wav_bytes = Pipe(recode.decode_wav_bytes, itemgetter(0))
