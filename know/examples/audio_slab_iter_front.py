from know.examples.keyboard_and_audio import keyboard_and_audio
from i2.wrapper import arg_val_converter
from i2 import Sig

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


# config
if __name__ == '__main__':
    from streamlitfront import mk_app

    _keyboard_and_audio = none_if_none_string_for_all_none_defaulted(keyboard_and_audio)

    app = mk_app([_keyboard_and_audio])
    app()
