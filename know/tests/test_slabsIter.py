from know.base import SlabsIter
from py2store import wrap_kvs, filt_iter, FilesOfZip
import soundfile as sf
import io
from graze import Graze
from typing import Mapping, Callable, Any, Protocol, runtime_checkable
import pytest
import logging
import pandas as pd


@wrap_kvs(obj_of_data=lambda b: sf.read(io.BytesIO(b), dtype='int16')[0])
@wrap_kvs(
    key_of_id=lambda _id: _id[len('sounds/') :], id_of_key=lambda key: f'sounds/{key}'
)
@filt_iter(filt=lambda x: x.endswith('.wav'))
class WfStore(FilesOfZip):
    """Waveform access. Keys are .wav filenames and values are numpy arrays of int16 waveform."""

    pass


WfStoreType = Mapping
WfStoreFactory = Callable[[Any], WfStoreType]


@runtime_checkable
class WfStoreFactoryGetter(Protocol):
    def __call__(self, *args, **kwargs) -> WfStoreFactory:
        """Returns a WfStoreFactory, that is, a callable that makes wf stores"""


get_wf_store_cls: WfStoreFactoryGetter  # This "declares" the coming function's "type"


def get_wf_store_cls(
    key_prefix_for_sounds: str = 'sounds/',
    audio_file_extension='.wav',
    dtype='int16',
    other_soundfile_kwargs=None,
):
    other_soundfile_kwargs = other_soundfile_kwargs or {}

    @wrap_kvs(
        key_of_id=lambda _id: _id[len(key_prefix_for_sounds) :],
        id_of_key=lambda key: f'{key_prefix_for_sounds}{key}',
        obj_of_data=lambda b: sf.read(
            io.BytesIO(b), dtype=dtype, **other_soundfile_kwargs
        )[0],
    )
    @filt_iter(filt=lambda x: x.endswith(audio_file_extension))
    class WfStore(FilesOfZip):
        """Waveform access. Keys are .wav filenames and values are numpy arrays of
        int16 waveform."""

        pass

    return WfStore


def data_for_url(
    url: str,
    get_wf_store_factory: WfStoreFactoryGetter = get_wf_store_cls,
    key_to_annots_csv='plc_0.csv',
):
    g = Graze()[url]
    z = FilesOfZip(g)
    annotations = pd.read_csv(io.BytesIO(z[key_to_annots_csv]), header=0)
    wf_store_factory = get_wf_store_factory()
    wf_store = wf_store_factory(io.BytesIO(g))
    return annotations, wf_store


test_1 = dict(
    url='https://www.dropbox.com/s/qsht8p0frl49njy/data_zipped.zip?dl=0',
    project_sref_name='filename',
)


@pytest.mark.parametrize(
    'test_params', [test_1,],
)
def test_slabsiter(test_params):
    # get the data from a dropbox url
    annotations, wf_store = data_for_url(
        test_params['url'],
        get_wf_store_factory=get_wf_store_cls,
        key_to_annots_csv='plc_0.csv',
    )

    # Make all the iterators needed. They are aligned in the sense that each "next" yields aligned data
    wf_iter = (wf_store[store_key] for store_key in pd.unique(annotations['filename']))

    def iter_per_file(col='channel'):
        for filename in pd.unique(annotations['filename']):
            df_filename = annotations[annotations['filename'] == filename]
            yield list(df_filename[col])

    phase_iter = iter_per_file('phase')
    channel_iter = iter_per_file('channel')
    session_iter = iter_per_file('session')

    # Making a slabs iter object
    def make_a_slabs_iter():
        # Mocking the sensor readers
        audio_sensor_read = wf_iter.__next__
        channel_read = channel_iter.__next__
        session_read = session_iter.__next__
        phase_read = phase_iter.__next__

        return SlabsIter(
            audio=audio_sensor_read,
            channel=channel_read,
            phase=phase_read,
            session=session_read,
            # The next
            check_single_channel=lambda channel: len(set(channel)) == 1,
            n_sessions=lambda session: len(set(session)),
            log_something=lambda phase: logging.info(
                f'N phases found {len(set(phase))}'
            ),
        )

    si = make_a_slabs_iter()

    first = next(si)
    second = next(si)

    # check that the dictionaries we get all contain the correct fields
    expected_keys = {
        k: None
        for k in [
            'audio',
            'channel',
            'phase',
            'session',
            'check_single_channel',
            'n_sessions',
            'log_something',
        ]
    }.keys()
    assert first.keys() == second.keys() == expected_keys

    # check that each slab contains a single channel
    assert first['check_single_channel'] == second['check_single_channel'] == True

    # check that each slab contains 100 sessions
    assert first['n_sessions'] == second['n_sessions'] == 100
