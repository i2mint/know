"""
Example of processing audio and keyboard streams
"""
import json
from stream2py.stream_buffer import StreamBuffer
from keyboardstream2py.keyboard_input import KeyboardInputSourceReader
from audiostream2py import PyAudioSourceReader, get_input_device_index
from know.base import SlabsIter, IteratorExit


def keyboard_and_audio(
    input_device=None,
    rate=44100,
    width=2,
    channels=1,
    frames_per_buffer=44100,  # same as sample rate for 1 second intervals
    seconds_to_keep_in_stream_buffer=60,
    launch=True,
    pipeline_commands=None,
):
    """Make an app that does something with live audio and keyboard event streams.

    The app will start two independent streams:
    one for audio and another for keyboard inputs.
    Prints stream type, timestamp, and additional info about data:
    Shows input key pressed for keyboard and byte count for audio

    Press Esc key to quit.

    :param input_device: Input device (index, name, pattern...)
    :param rate: audio sample rate
    :param width: audio byte width
    :param channels: number of audio input channels
    :param frames_per_buffer: audio samples per buffer
    :param seconds_to_keep_in_stream_buffer: max size of audio buffer before data falls off
    :param launch: If True (default) will launch the app. If False, will just return the
    app object.
    :return: None
    """
    input_device_index = get_input_device_index(input_device=input_device)
    pipeline_commands = pipeline_commands or dflt_slab_iter_commands

    # converts seconds_to_keep_in_stream_buffer to max number of buffers of size
    # frames_per_buffer
    maxlen = PyAudioSourceReader.audio_buffer_size_seconds_to_maxlen(
        buffer_size_seconds=seconds_to_keep_in_stream_buffer,
        rate=rate,
        frames_per_buffer=frames_per_buffer,
    )

    audio_reader = PyAudioSourceReader(
        rate=rate,
        width=width,
        channels=channels,
        unsigned=True,
        input_device_index=input_device_index,
        frames_per_buffer=frames_per_buffer,
    ).stream_buffer(maxlen)

    from stream2py.util import contextualize_with_instance
    from functools import partial

    app = SlabsIter(
        # source the data
        audio=audio_reader,
        # _print_info=partial(print, '', end='\n\r'),  # TODO: Address no_sig_kwargs err
        keyboard=KeyboardInputSourceReader().stream_buffer(maxlen),
        # check audio and keyboard for stopping signals
        audio_reader_instance=lambda: audio_reader,  # to give access to the audio_reader
        **pipeline_commands,
    )

    if not launch:
        return app
    else:
        app()
        print(f'\nYour session is now over.\n')


# ---------------------------------------------------------------------------------------
# Example functions to use in a pipeline


def lite_audio_callback(audio):
    if audio is not None:
        (audio_timestamp, waveform, frame_count, time_info, status_flags,) = audio
        print(
            f'   [Audio] {audio_timestamp}: {len(waveform)=} {type(waveform).__name__}',
            end='\n\r',
        )


def full_audio_print(audio):
    if audio is not None:
        (audio_timestamp, waveform, frame_count, time_info, status_flags,) = audio
        # print(f"{type(audio_data)=}")
        print(
            f'   [Audio] {audio_timestamp=}: {len(waveform)=} {type(waveform).__name__}'
            f' {frame_count=}, {time_info=}, {status_flags=}',
            end='\n\r',
        )


def keyboard_data_signals_an_interrupt(
    keyboard_data, stop_signal_chars=frozenset(['\x03', '\x04', '\x1b'])
):
    """The function returns a positive stop signal (1) if the character is in the
    `stop_signal_chars` set.
    By default, the `stop_signal_chars` contains:
    * \x03: (ascii 3 - End of Text)
    * \x04: (ascii 4 - End of Trans)
    * \x1b: (ascii 27 - Escape)
    (See https://theasciicode.com.ar/ for ascii codes.)

    (1) in the form of a string specifying what the ascii code of the input character was

    :param keyboard_data: Input character
    :param stop_signal_chars: Set of stop characters
    :return:
    """
    if keyboard_data is not None:
        # print(f"{type(keyboard_data)=}, {len(keyboard_data)=}")
        index, keyboard_timestamp, char = keyboard_data
        # print(f'[Keyboard] {keyboard_timestamp}: {char=} ({ord(char)=})', end='\n\r')

        if char in stop_signal_chars:
            return f'ascii code: {ord(char)} (See https://theasciicode.com.ar/)'
        else:
            return False


def stop_if_audio_not_running(audio_reader_instance):
    if audio_reader_instance is not None and not audio_reader_instance.is_running:
        raise IteratorExit("audio isn't running anymore!")


def audio_print(audio):
    full_audio_print(audio)


def keyboard_stop(keyboard):
    if keyboard_data_signals_an_interrupt(keyboard):
        print('\nI feel a disturbance in the keyboard...')
        raise KeyboardInterrupt('You keyed an exit combination. You want to stop.')


def keyboard_print(keyboard):
    if keyboard is not None:
        print(f'{keyboard=}\n', end='\n\r')


class LastCharPressed:
    key = '*'

    def __call__(self, keyboard):
        if keyboard is not None:
            idx, timestamp, key = keyboard
            self.key = key
        return self.key


from recode import mk_codec

codec = mk_codec('h')


def wf_to_print(wf, bar_char=';)'):
    from statistics import stdev

    if wf is not None:
        vol = stdev(wf) / 200
        n_bars = 1 + int(vol)
        print(bar_char * n_bars, end='\n\r')


def audio_to_wf(audio):
    from statistics import stdev

    if audio is not None:
        _, wf_bytes, *_ = audio
        wf = codec.decode(wf_bytes)
        return wf

        # vol = stdev(wf) / 200
        # n_bars = 1 + int(vol)
        # print(bar_char * n_bars, end='\n\r')


def only_if(locals_condition, sentinel=None):
    """Convenience wrapper to condition a function call on some function of it's inputs.

    Important: The signature of locals_condition matter: It's through the names of it's arguments that ``only_if``
    knows what values to extract from the inputs to compute the condition.

    >>> @only_if(lambda x: x > 0)
    ... def foo(x, y=1):
    ...     return x + y
    >>>
    >>> foo(1, y=2)
    3
    >>> assert foo(-1, 2) is None

    ``None`` is just the default sentinel. You can specify your own:

    >>> @only_if(lambda y: (y % 2) == 0, sentinel='y_is_not_even')
    ... def foo(x, y=1):
    ...     return x + y
    >>> foo(x=1, y=2)
    3
    >>> foo(1, y=3)
    'y_is_not_even'

    """
    from functools import wraps
    from i2 import Sig, call_forgivingly

    def wrapper(func):
        sig = Sig(func)

        @wraps(func)
        def locals_conditioned_func(*args, **kwargs):
            _kwargs = sig.kwargs_from_args_and_kwargs(args, kwargs)
            if call_forgivingly(locals_condition, **_kwargs):
                return func(*args, **kwargs)
            else:
                return sentinel

        return locals_conditioned_func

    return wrapper


def print_samples(wf, max_samples=11):
    if wf is not None:
        print(wf[:max_samples], end='\n\r')


# ---------------------------------------------------------------------------------------

dflt_slab_iter_commands = dict(
    # # # The app will provide the three following variables to build on:
    # # source the data
    # audio=audio_reader,
    # keyboard=KeyboardInputSourceReader().stream_buffer(maxlen),
    # audio_reader_instance=lambda: audio_reader,  # to give access to the audio_reader
    # # # Here's an example of what we can do in the pipeline
    # check audio and keyboard for stopping signals
    _audio_stop=stop_if_audio_not_running,
    _keyboard_stop=keyboard_stop,
    # handle signals
    handle_exceptions=(IteratorExit, KeyboardInterrupt),
    # do stuff
    # audio_print=audio_print,
    keyboard_print=keyboard_print,
    bar_char=LastCharPressed(),
    wf=audio_to_wf,
    # __1=wf_to_print,
    __2=print_samples,
)


if __name__ == '__main__':
    # TODO: When wrappers.py ready for it, use argh, preprocessing the function so that:
    #   specific (int expected) transformed to int (argname, annotation, or default)
    #   functional args removed, or {str: func} map provided, or inject otherwise?
    keyboard_and_audio()
