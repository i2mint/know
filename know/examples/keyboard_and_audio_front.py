from know.examples.keyboard_and_audio import (
    keyboard_and_audio,
    keyboard_print,
    stop_if_audio_not_running,
    keyboard_stop,
    IteratorExit,
    LastCharPressed,
    audio_to_wf,
    print_samples,
)
from i2.wrapper import arg_val_converter
from i2 import Sig
import streamlit as st
from keyboardstream2py.keyboard_input import KeyboardInputSourceReader
from audiostream2py import PyAudioSourceReader, get_input_device_index
from know.base import SlabsIter, IteratorExit
from streamlitfront import mk_app, binder as b
from dataclasses import dataclass
from front import APP_KEY, RENDERING_KEY, ELEMENT_KEY, NAME_KEY
from streamlitfront.elements import TextInput, SelectBox
from front.elements import OutputBase, ExecContainerBase, InputBase


if not b.mall():
    # TODO: Maybe it's here that we need to use know.malls.mk_mall?
    b.mall = {'keyboard_event': dict()}
mall = b.mall()


def view_mall(x: int):
    st.write(mall)
    return x


# TODO: Generalize to a curriable alias handling function? It's a if_cond_val pattern.
def none_if_none_string(x):
    if isinstance(x, str) and x == 'None':
        return None
    return x


def none_if_none_string_for_all_none_defaulted(func, exception_argnames=()):
    none_defaulted_args = [
        name
        for name, default in Sig(func).defaults.items()
        if default == None and name not in exception_argnames
    ]
    if none_defaulted_args:
        return arg_val_converter(
            func, **{name: none_if_none_string for name in none_defaulted_args}
        )
    return func


def print_samples(wf, max_samples=11):
    if wf is not None:
        print(wf[:max_samples], end='\n\r')


def keyboard_print(keyboard):  # use logger=print
    if keyboard is not None:
        print(f'my {keyboard=}\n', end='\n\r')
        mall['keyboard_event'] = {'last': f'{keyboard=}'}
        st.warning(f'{keyboard=}')


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


@dataclass
class OutRenderer(OutputBase):
    def render(self):
        print(self.output)
        st.write(f'{self.output=}')


config = {
    APP_KEY: {'title': 'Funcs'},
    RENDERING_KEY: {
        '_keyboard_and_audio': {
            # NAME_KEY: "Identity Rendering",
            'execution': {
                # "inputs": {
                #     "func": {
                #         ELEMENT_KEY: SelectBox,
                #         "options": mall["func_choices"],
                #         "value": b.selected_func,
                #     },
                # },
                'output': {ELEMENT_KEY: OutRenderer},
            },
        }
    },
}
# config
if __name__ == '__main__':
    from functools import partial
    from streamlitfront import mk_app

    # keyboard_and_audio = partial(
    #     keyboard_and_audio, pipeline_commands=dflt_slab_iter_commands
    # )
    _keyboard_and_audio = none_if_none_string_for_all_none_defaulted(keyboard_and_audio)

    app = mk_app([_keyboard_and_audio], config=config)

    app()
    # st.write(mall)
