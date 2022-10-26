from know.examples.keyboard_and_audio import keyboard_and_audio


if __name__ == '__main__':
    from streamlitfront import mk_app

    app = mk_app([keyboard_and_audio])
    app()


