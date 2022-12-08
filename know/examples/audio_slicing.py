"""Simple audio examples"""

from taped import LiveWf
from know.util import pairwise, source_slices
from functools import partial


mk_audio_stream = partial(
    LiveWf,
    input_device_index=None,  # if None, will try to guess the device index
    sr=44100,
    sample_width=2,
    chk_size=4096,
    stream_buffer_size_s=60,
)


def get_some_audio_chunks(intervals_size=2048 * 21, n_chks=3, **audio_stream_kwargs):
    total_size = n_chks * n_chks
    intervals = pairwise(range(0, total_size + 1, intervals_size))
    _mk_audio_stream = partial(mk_audio_stream, **audio_stream_kwargs)
    return list(source_slices(_mk_audio_stream, intervals=intervals))
