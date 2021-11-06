r"""Audio to store experimentation

Example use:

```
from omisc.audio_to_store import *

wfs = demo_live_data_acquisition(
    live_source=LiveWf(
        input_device_index = None,  # if None, will try to guess the device index
        sr = 44100,
        sample_width = 2,
        chk_size = 4096,
        stream_buffer_size_s = 60,
    ),
    store=mk_session_block_wf_store(
        rootdir=None,  # will choose one for you
        # template examples: '{session}_{block}.wav' '{session}/d/{block}.pcm',
        #    '{session}/{block}', 'demo/s_{session}/blocks/{block}.wav'
        template='{session}_{block}.wav',  #
        pattern=r'\d+',
        value_trans=int
    ),
    chk_size=100_000,
    end_idx=300_000,
    logger=print
)
print(f"{len(wfs)=}")
```
"""

from time import time
from typing import Protocol, Tuple, NewType, Any, Callable, Union
from operator import itemgetter

from atypes import WaveformBytes, Waveform, IntervalSlice, Segment
from recode import mk_encoder_and_decoder

from dol import StrTupleDict, wrap_kvs
from dol.filesys import RelPathFileBytesPersister
from dol.paths import mk_dirs_if_missing
from lined import Pipe

from taped import LiveWf, chunk_indices
from i2 import Sig


def print_signature(func):
    for p in Sig(func).params:
        print(f"{p.name}{'=' + str(p.default) if p.default is not Sig.empty else ''},")


SessionId = NewType('SessionId', int)
BlockId = NewType('BlockId', int)
SessionBlockTuple = NewType('SessionBlockTuple', Tuple[SessionId, BlockId])


class LiveDataSingleSourceType(Protocol):
    def __getitem__(self, k: IntervalSlice) -> Segment:
        """Get a segment of data from a [bt, tt] interface"""


class SessionBlockStoreType(Protocol):
    """The protocol for SessionBlockStores"""

    def __setitem__(self, k: SessionBlockTuple, v: Segment):
        """Takes a (session: int, block: int) pair and segment, and stores them"""


class SessionBlockBytesStoreType(Protocol):
    """The protocol for SessionBlockStores"""

    def __setitem__(self, k: SessionBlockTuple, v: WaveformBytes):
        """Takes a (session: int, block: int) pair and waveform bytes, and stores them"""


class SessionBlockWaveformStoreType(Protocol):
    """The protocol for SessionBlockStores"""

    def __setitem__(self, k: SessionBlockTuple, v: Waveform):
        """Takes a (session: int, block: int) pair and waveform, and stores them"""


def get_resource(resource, dflt_callback: Callable):
    if resource is None:
        resource = dflt_callback
    if callable(resource):
        resource = resource()
    return resource


def demo_audio_to_file(rootdir=None, chk_size=100_000, end_idx=300_000):
    session_id = int(time() * 1000)
    wfs = mk_session_block_wf_store(rootdir)

    with LiveWf() as live_wf:
        for bt, tt in chunk_indices(chk_size=chk_size, end_idx=end_idx):
            print(f'{bt=}, {tt=}')
            wfs[session_id, bt] = live_wf[bt:tt]


def get_root_dir(rootdir=None):
    """get a rootdir (a default one, or validate the one given etc.)"""
    if rootdir is not None:
        return rootdir
    else:
        import os

        rootdir = os.path.join(os.path.expanduser('~'), 'tmp', 'qchack')
        if not rootdir.startswith(os.path.sep):
            rootdir += os.path.sep

        os.makedirs(rootdir, exist_ok=True)
        return rootdir


# chk_format='h' is equivalent to a PCM16 codec
pcm16_encode, pcm16_decode = mk_encoder_and_decoder(chk_format='h')


def wf_to_pcm16_bytes(wf):
    return pcm16_encode(wf)


def pcm16__bytes_to_wf(b: bytes):
    return pcm16_decode(b)

    # import soundfile as sf
    # return sf.read(BytesIO(b), dtype='int16')


import struct

DFLT_SR = 44100
DFLT_SAMPLE_WIDTH = 2


def wav_header(n_bytes, sr=DFLT_SR, n_channels=1, sample_width_bytes=DFLT_SAMPLE_WIDTH):
    WAVE_FORMAT_PCM = 0x0001
    bytes_to_add = b'RIFF'

    _nframes = n_bytes // (n_channels * sample_width_bytes)
    _datalength = _nframes * n_channels * sample_width_bytes

    bytes_to_add += struct.pack(
        '<L4s4sLHHLLHH4s',
        36 + _datalength,
        b'WAVE',
        b'fmt ',
        16,
        WAVE_FORMAT_PCM,
        n_channels,
        sr,
        n_channels * sr * sample_width_bytes,
        n_channels * sample_width_bytes,
        sample_width_bytes * 8,
        b'data',
    )

    bytes_to_add += struct.pack('<L', _datalength)

    return bytes_to_add


def wf_to_wav_bytes(wf, sr=DFLT_SR, sample_width_bytes=DFLT_SAMPLE_WIDTH):
    return wav_header(
        len(wf) * sample_width_bytes, sr=sr, sample_width_bytes=sample_width_bytes
    ) + pcm16_encode(wf)


def wav_bytes_to_wf(b: bytes):
    # TODO: Be safer; use wave package to parse header and decode accordingly
    return pcm16_decode(b[44:])


def _wrap_in_tuple(x):
    return (x,)


def _all_but_last(x):
    return x[:-1]


def mk_key_trans(template, pattern=None, value_trans=None, key_type: Any = tuple):
    from string import Formatter

    format_dict, process_info_dict = {}, {}  # defaults
    str_formatter = Formatter()
    str_formatter.parse(template)
    names = list(filter(None, map(itemgetter(1), str_formatter.parse(template))))
    if pattern is not None:
        format_dict = {name: pattern for name in names}
    if value_trans is not None:
        process_info_dict = {name: value_trans for name in names}
    converter = StrTupleDict(
        template, format_dict=format_dict, process_info_dict=process_info_dict
    )
    if key_type is tuple:
        return wrap_kvs(
            key_of_id=converter.str_to_tuple, id_of_key=converter.tuple_to_str
        )
    elif key_type == 'single':
        return wrap_kvs(
            key_of_id=Pipe(converter.str_to_tuple, itemgetter(0)),
            id_of_key=Pipe(_wrap_in_tuple, converter.tuple_to_str),
        )


def mk_session_store(rootdir=None):

    rootdir = get_root_dir(rootdir)

    from dol.filesys import DirCollection, mk_relative_path_store

    key_trans = mk_key_trans(
        template='{session}/',
        pattern=r'\d+',  # for extra format protection
        value_trans=int,
        key_type='single',
    )

    @key_trans
    @mk_relative_path_store(prefix_attr='rootdir')
    class SessionStore(DirCollection):
        def __getitem__(self, k):
            return mk_block_store(k)

        def __repr__(self):
            return f"{type(self).__name__}('{self.rootdir}', ...)"

    s = SessionStore(rootdir, max_levels=0)

    return s


def mk_block_store(rootdir=None):

    rootdir = get_root_dir(rootdir)

    wrapper = Pipe(
        mk_dirs_if_missing,
        mk_key_trans(
            template='d/{block}.pcm',
            pattern=r'\d+',  # for extra format protection
            value_trans=int,
            key_type='single',
        ),
        wrap_kvs(data_of_obj=wf_to_pcm16_bytes, obj_of_data=pcm16__bytes_to_wf),
    )

    @wrapper
    class BlockStore(RelPathFileBytesPersister):
        """Block reader store"""

    s = BlockStore(rootdir)

    return s


def mk_session_block_wf_store(
    rootdir=None, template='{session}/d/{block}.pcm', pattern=r'\d+', value_trans=int
) -> SessionBlockWaveformStoreType:

    rootdir = get_root_dir(rootdir)
    key_trans = mk_key_trans(
        template=template,
        pattern=pattern,  # for extra format protection
        value_trans=value_trans,
    )

    if template.endswith('.wav'):
        wf_to_bytes = wf_to_wav_bytes
        bytes_to_wf = wav_bytes_to_wf
    else:
        wf_to_bytes = wf_to_pcm16_bytes
        bytes_to_wf = pcm16__bytes_to_wf

    wrapper = Pipe(
        mk_dirs_if_missing,
        key_trans,
        wrap_kvs(data_of_obj=wf_to_bytes, obj_of_data=bytes_to_wf),
    )

    @wrapper
    class PcmPersister(RelPathFileBytesPersister):
        """Persist pcm audio bytes"""

    s = PcmPersister(rootdir)

    return s


def mk_mongo_single_data(
    mgc='mongodol/test', key_fields=('session', 'block'), data_field: str = 'data'
):
    """s[session, block] waveform store with a mongoDB backend"""
    from operator import itemgetter
    from functools import partial

    from mongodol.stores import MongoTupleKeyStore
    from dol import wrap_kvs

    def itemsetter(item, key, container_factory=dict):
        """A (single item) dual of itemgetter. To call repeatedly on the same container, use lambda: mutable_container_reference"""
        container = container_factory()
        container[key] = item
        return container

    # Note: Could also add input type validation in data_of_obj
    wrapper = wrap_kvs(
        data_of_obj=partial(itemsetter, key=data_field),
        obj_of_data=itemgetter(data_field),
    )
    db_name, col_name = mgc.split('/')

    return wrapper(
        MongoTupleKeyStore(
            db_name, col_name, key_fields=key_fields, data_fields=(data_field,)
        )
    )


def mk_session_block_bytes_store(rootdir=None) -> SessionBlockBytesStoreType:

    rootdir = get_root_dir(rootdir)

    wrapper = Pipe(
        mk_dirs_if_missing,
        mk_key_trans(
            template='{session}/d/{block}.pcm',
            pattern=r'\d+',  # for extra format protection
            value_trans=int,
        ),
    )

    @wrapper
    class PcmPersister(RelPathFileBytesPersister):
        """Persist pcm audio bytes"""

    s = PcmPersister(rootdir)

    return s


def persistence_demo(rootdir=None):
    s = mk_session_block_bytes_store(rootdir)
    # delete if present
    if (298094, 343) in s:
        del s[298094, 343]
    if (298094, 998) in s:
        del s[298094, 998]
    # write to these keys
    s[298094, 343] = b'298094_343'
    s[298094, 998] = b'298094_998'
    # see that these keys now exist
    assert (298094, 343) in s and (298094, 998) in s  # verify that these keys exist
    # ... and have the desired data
    assert s[298094, 343] == b'298094_343'
    assert s[298094, 998] == b'298094_998'


def demo_live_data_acquisition(
    live_source=LiveWf,
    store: Union[
        SessionBlockStoreType, Callable[[], SessionBlockStoreType]
    ] = mk_session_block_wf_store,
    chk_size=100_000,
    end_idx=300_000,
    logger=None,
):
    live_source = get_resource(live_source, dflt_callback=LiveWf)
    store = get_resource(store, dflt_callback=mk_session_block_wf_store)

    session_id: SessionId = int(time() * 1000)
    with live_source:
        # range(start, stop, step)
        for i, (bt, tt) in enumerate(chunk_indices(chk_size=chk_size, end_idx=end_idx)):
            if logger:
                logger(f'{i=}: {bt=}, {tt=}')
            block: BlockId = bt
            store[session_id, block] = live_source[bt:tt]  # <-- The important part
            # store.add(live_source[bt:tt])

    return store


def iterate_chunks(src, chk_size, chk_step=None, start_idx=0, end_idx=None):
    intervals = chunk_indices(
        chk_size=chk_size, chk_step=chk_step, start_idx=start_idx, end_idx=end_idx
    )


def audio_only_live_process(
    live_source=LiveWf,
    store: Union[
        SessionBlockStoreType, Callable[[], SessionBlockStoreType]
    ] = mk_session_block_wf_store,
    chk_size=100_000,
    end_idx=300_000,
    logger=None,
):
    live_source = get_resource(live_source, dflt_callback=LiveWf)
    store = get_resource(store, dflt_callback=mk_session_block_wf_store)

    session_id: SessionId = int(time() * 1000)
    with live_source:
        # range(start, stop, step)
        for i, (bt, tt) in enumerate(chunk_indices(chk_size=chk_size, end_idx=end_idx)):
            if logger:
                logger(f'{i=}: {bt=}, {tt=}')
            block: BlockId = bt
            store[session_id, block] = live_source[bt:tt]  # <-- The important part
            # store.add(live_source[bt:tt])

    return store


# TODOs:
# multichannel: keyboard + audio
# nice to have (for testing): Emulate sensors with data generators
