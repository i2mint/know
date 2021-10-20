"""Keyboard and audio acquisition"""


"""Example of processing audio and keyboard streams"""
from typing import Callable, NewType, Any
from stream2py.stream_buffer import StreamBuffer
from stream2py.sources.keyboard_input import KeyboardInputSourceReader
from stream2py.sources.audio import (
    PyAudioSourceReader,
    find_a_default_input_device_index,
)

from i2 import ContextFanout

AudioData = NewType('', Any)
KeyboardData = NewType('', Any)
AudioDataCallback = Callable[[AudioData], Any]
KeyboardDataCallback = Callable[[KeyboardData], Any]


def default_audio_callback(audio_data):
    if audio_data is not None:
        (audio_timestamp, waveform, frame_count, time_info, status_flags,) = audio_data
        print(
            f'   [Audio] {audio_timestamp}: {len(waveform)=} {type(waveform).__name__}',
            end='\n\r',
        )


def default_keyboard_event_callback(
    keyboard_data, stop_signal_chars=frozenset(['\x03', '\x04', '\x1b'])
):
    """The function will print the input character and ascii code, and return a positive
    stop signal (1) if the character is in the `stop_signal_chars` set.
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
        index, keyboard_timestamp, char = keyboard_data
        print(f'[Keyboard] {keyboard_timestamp}: {char=} ({ord(char)=})', end='\n\r')

        if char in stop_signal_chars:
            return f'ascii code: {ord(char)} (See https://theasciicode.com.ar/)'
        else:
            return False


def keyboard_and_audio(
    input_device_index=None,  # find index with PyAudioSourceReader.list_device_info()
    rate=44100,
    width=2,
    channels=1,
    frames_per_buffer=44100,  # same as sample rate for 1 second intervals
    seconds_to_keep_in_stream_buffer=60,
    audio_data_callback: AudioDataCallback = default_audio_callback,
    keyboard_data_callback: KeyboardDataCallback = default_keyboard_event_callback,
):
    """Starts two independent streams: one for audio and another for keyboard inputs.
    Prints stream type, timestamp, and additional info about data:
    Shows input key pressed for keyboard and byte count for audio

    Press Esc key to quit.

    :param input_device_index: find index with PyAudioSourceReader.list_device_info()
    :param rate: audio sample rate
    :param width: audio byte width
    :param channels: number of audio input channels
    :param frames_per_buffer: audio samples per buffer
    :param seconds_to_keep_in_stream_buffer: max size of audio buffer before data falls off
    :return: None
    """

    if input_device_index is None:
        input_device_index = find_a_default_input_device_index()

    selected_device_info = next(
        dev
        for dev in PyAudioSourceReader.list_device_info()
        if dev['index'] == input_device_index
    )
    print(f"Starting audio device: {selected_device_info['name']}\n")

    # converts seconds_to_keep_in_stream_buffer to max number of buffers of size frames_per_buffer
    maxlen = PyAudioSourceReader.audio_buffer_size_seconds_to_maxlen(
        buffer_size_seconds=seconds_to_keep_in_stream_buffer,
        rate=rate,
        frames_per_buffer=frames_per_buffer,
    )
    audio_source_reader = PyAudioSourceReader(
        rate=rate,
        width=width,
        channels=channels,
        unsigned=True,
        input_device_index=input_device_index,
        frames_per_buffer=frames_per_buffer,
    )

    audio_stream_buffer = StreamBuffer(source_reader=audio_source_reader, maxlen=maxlen)
    keyboard_stream_buffer = StreamBuffer(
        source_reader=KeyboardInputSourceReader(), maxlen=maxlen
    )

    # def buffer_to_reader_to_iterator():

    src = ContextFanout(audio_stream_buffer, keyboard_stream_buffer)
    with src as (audio_stream_buffer, keyboard_stream_buffer):
        audio_buffer_reader = audio_stream_buffer.mk_reader()
        keyboard_buffer_reader = keyboard_stream_buffer.mk_reader()

        print('getch! Press any key! Esc to quit!\n')

        # slabs = zip(keyboard_buffer_reader, audio_buffer_reader)

        def stop_criteria(items):
            return keyboard_data_callback(items[1])

        slabs = iterate((audio_buffer_reader, keyboard_buffer_reader),
                        stop_criteria)

        for keyboard_data, audio_data in slabs:
            try:
                #
                # should_quit = keyboard_data_callback(keyboard_data)
                # if should_quit:
                #     print(f'\n\nI got a signal ({should_quit}) to quit.')
                #     break
                # print(audio_data)
                audio_data_callback(audio_data)

            except KeyboardInterrupt as e:
                print(f'\n\nGot a {e}')
                break

        # This works:
        # while True:
        #     try:
        #         keyboard_data = next(keyboard_buffer_reader)
        #         audio_data = next(audio_buffer_reader)
        #
        #         should_quit = keyboard_data_callback(keyboard_data)
        #         if should_quit:
        #             print(f'\n\nI got a signal ({should_quit}) to quit.')
        #             break
        #
        #         audio_data_callback(audio_data)
        #
        #     except KeyboardInterrupt as e:
        #         print(f'\n\nGot a {e}')
        #         break

    print(f'\nQuitting the app...\n')

def never_stop(items):
    return False

from i2 import Pipe

apply = Pipe(map, tuple)


def iterate(iterators, stop_condition=lambda x: False):
    iterators = apply(iter, iterators)
    while True:
        items = apply(next, iterators)
        yield items
        if stop_condition(items):
            break


# NOTE: Just zip?
class MultiIter:
    def __init__(self, *iterables):
        self.iterables = iterables

    def __iter__(self):

        yield from self.iterables


# class LiveProcess:
#     slabs: Iterable[Slab]
#     slab_callback: SlabCallback
#
#     def __call__(self):
#         with ContextFanout(self.slabs, self.slab_callback):
#             for slab in self.slabs:
#                 callback_output = self.slab_callback(slab)
#
#         return callback_output

if __name__ == '__main__':
    keyboard_and_audio()
