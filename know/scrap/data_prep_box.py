"""A toolbox to make data preparation pipelines"""

from functools import partial
from operator import itemgetter
from collections import Counter
import re
import os

from dol import wrap_kvs, filt_iter, FilesOfZip, Files, Pipe
import recode

from know.scrap.mesh_composer import Box, box_items
from dol.sources import AttrContainer
from tested import validate_codec
from i2.deco import FuncFactory, postprocess

from collections import ChainMap

from i2 import wrap, Sig

# from i2.multi_object import
from i2.wrapper import include_exclude


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
    return func1(*args, **kwargs) & func2(*args, **kwargs)


def make_function_conjunction(func1, func2):
    return partial(_function_conjunction, func1=func1, func2=func2)


read_wav_bytes = Pipe(recode.decode_wav_bytes, itemgetter(0))


dflt_store_contents = dict(
    object_transformation=dict(default_wav_bytes_reader=read_wav_bytes),
    aggregator=dict(counter=Counter),
)

factories = dict(
    source_reader=dict(
        files_of_folder=FuncFactory(Files), files_of_zip=FuncFactory(FilesOfZip),
    ),
    store_transformers=dict(
        key_transformer=key_transformer,
        val_transformer=val_transformer,
        key_filter=filt_iter,
        extract_extension=FuncFactory(extract_extension),
    ),
    object_transformation=dict(
        make_codec=make_decoder,
    ),
    boolean_functions=dict(regular_expression_filter=regular_expression_filter, ),
)
# mall = dict(object_transformation=DillFiles())

from know.scrap.mall_making import mk_mall


mall = mk_mall(
    dflt_store_contents=dflt_store_contents,
    factories_for_store=factories
)

# dflt_store_contents = dict(
#     files_of_folder=FuncFactory(Files),
#     files_of_zip=FuncFactory(FilesOfZip),
#     key_transformer=key_transformer,
#     val_transformer=val_transformer,
#     key_filter=filt_iter,
#     extract_extension=FuncFactory(extract_extension),
#     make_codec=make_decoder,
#     make_wav_bytes_reader=FuncFactory(read_wav_bytes),
#     regular_expression_filter=regular_expression_filter,
#     counter=Counter,
# )

d = dict(
    kv_reader=dict(
        files_of_folder=FuncFactory(Files), files_of_zip=FuncFactory(FilesOfZip),
    ),
    kv_trans=dict(
        key_transformer=key_transformer,
        val_transformer=val_transformer,
        key_filter=filt_iter,
        extract_extension=FuncFactory(extract_extension),
    ),
    obj_trans=dict(
        make_codec=make_decoder, make_wav_bytes_reader=FuncFactory(read_wav_bytes)
    ),
    bool_funcs=dict(regular_expression_filter=regular_expression_filter,),
    aggregator=dict(counter=FuncFactory(Counter),),
)


# ---------- Box -------------------
# Experimenting with backend containers for pipeline ingredients

# ---------- First way: With a Box class -------------------
class DataPrepBox(Box):
    kv_reader = AttrContainer(
        files_of_folder=FuncFactory(Files), files_of_zip=FuncFactory(FilesOfZip),
    )
    kv_trans = AttrContainer(
        key_transformer,
        val_transformer,
        key_filter=filt_iter,
        #         key_transformer = key_transformer,
        #         val_transformer = val_transformer,
        extract_extension=FuncFactory(extract_extension),
    )
    obj_trans = AttrContainer(
        make_codec=make_decoder, make_wav_bytes_reader=FuncFactory(read_wav_bytes)
    )
    bool_funcs = AttrContainer(regular_expression_filter=regular_expression_filter,)
    aggregator = AttrContainer(counter=FuncFactory(Counter),)


def _test_box(box):
    assert set(box) == {
        'kv_reader',
        'kv_trans',
        'obj_trans',
        'bool_funcs',
        'aggregator',
    }
    assert set(box.kv_reader) == {'files_of_folder', 'files_of_zip'}
    assert isinstance(box.kv_reader.files_of_zip, FuncFactory)
    assert box.kv_reader.files_of_zip.func is FilesOfZip


box = DataPrepBox()
_test_box(box)


# ---------- Second way: With AttrContainer only -------------------

box = AttrContainer(
    kv_reader=AttrContainer(
        files_of_folder=FuncFactory(Files), files_of_zip=FuncFactory(FilesOfZip),
    ),
    kv_trans=AttrContainer(
        key_transformer,
        val_transformer,
        key_filter=filt_iter,
        extract_extension=FuncFactory(extract_extension),
    ),
    obj_trans=AttrContainer(
        make_codec=make_decoder, make_wav_bytes_reader=FuncFactory(read_wav_bytes)
    ),
    bool_funcs=AttrContainer(regular_expression_filter=regular_expression_filter,),
    aggregator=AttrContainer(counter=FuncFactory(Counter),),
)


_test_box(box)

# ---------- Third way: from dict -------------------


def _dict_to_box(d: dict):
    def gen():
        for k, v in d.items():
            if isinstance(v, dict):
                v = _dict_to_box(v)
            yield k, v

    return AttrContainer(**dict(gen()))


d = dict(
    kv_reader=dict(
        files_of_folder=FuncFactory(Files), files_of_zip=FuncFactory(FilesOfZip),
    ),
    kv_trans=dict(
        key_transformer=key_transformer,
        val_transformer=val_transformer,
        key_filter=filt_iter,
        extract_extension=FuncFactory(extract_extension),
    ),
    obj_trans=dict(
        make_codec=make_decoder, make_wav_bytes_reader=FuncFactory(read_wav_bytes)
    ),
    bool_funcs=dict(regular_expression_filter=regular_expression_filter,),
    aggregator=dict(counter=FuncFactory(Counter),),
)

box = _dict_to_box(d)

_test_box(box)
