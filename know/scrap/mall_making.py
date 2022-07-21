"""Tools to make malls"""

import os
from functools import partial
from typing import Iterable, Mapping, Union, Callable
from tempfile import gettempdir
from dol import Files, wrap_kvs
from dol.filesys import ensure_dir, mk_dirs_if_missing
import dill

_DFLT_ROOT_DIR = ensure_dir(gettempdir())
DFLT_STORE_ROOT_FOLDER = os.path.join(_DFLT_ROOT_DIR, 'tmp_data_prep_stores')

# @mk_dirs_if_missing
@wrap_kvs(data_of_obj=dill.dumps, obj_of_data=dill.loads)
class DillFiles(Files):
    """Serializes and deserializes with dill"""


def _dflt_name_to_store(name: str, rootdir: str = DFLT_STORE_ROOT_FOLDER):
    """The default way to make a store based on a name"""
    # TODO: Wanted to use mk_dirs_if_missing, but issues with it.
    #  https://github.com/i2mint/dol/issues/14
    dirpath = ensure_dir(os.path.join(rootdir, name))
    return DillFiles(dirpath)


def mk_mall(
    stores: Mapping = (),
    dflt_store_contents: Mapping = (),
    factories_for_store: Mapping = (),
    name_to_store: Union[Callable, str] = _dflt_name_to_store,
):
    """

    :param stores: A ``{name: store, ...}`` mapping or iterable of names
    :param dflt_store_contents: Some contents that the stores should be prepopulated with
    :param factories_for_store: A mapping
    :param name_to_store: A function to create a store for a given name.
        Note: This is to be able make default stores for the lazy user.
    :return:
    """
    stores, dflt_store_contents, factories_for_store = map(
        dict, [stores, dflt_store_contents, factories_for_store]
    )
    stores = dict(  # merge in keys that are not in stores (defaulting to None value)
        dict.fromkeys(dflt_store_contents),
        **dict.fromkeys(factories_for_store),
        **stores
    )
    if isinstance(name_to_store, str):
        # if name_to_store is a str, assume it's the rootdir we want
        rootdir = name_to_store
        name_to_store = partial(_dflt_name_to_store, rootdir=rootdir)
    stores = dict(_fill_missing_stores_with_default_store(stores, name_to_store))
    _insert_content_in_stores(stores, dflt_store_contents)
    for name in stores:
        stores[name].factories = factories_for_store.get(name, [])
    return stores


def _insert_content_in_stores(stores, store_contents):
    for k, v in store_contents.items():
        if isinstance(v, Mapping):
            stores[k] = _insert_content_in_stores(stores.get(k, {}), v)
        else:
            stores[k] = v
    return stores


def _fill_missing_stores_with_default_store(stores, name_to_store):
    stores = _ensure_mapping(stores)
    for store_name, store_obj in stores.items():
        if store_obj is None:
            store_obj = name_to_store(store_name)
        yield store_name, store_obj


def _ensure_mapping(x):
    if _is_non_mapping_iterable(x):
        x = dict.fromkeys(x)
    return x


def _is_non_mapping_iterable(x):
    return isinstance(x, Iterable) and not isinstance(x, Mapping)
