"""An app ot make data prep tools"""


from know.boxes import *

# TODO: make a different mk_pipe (maybe using meshed or lined.ParametrizedLine)
dflt_store_contents = dict(
    object_transformation=dict(default_wav_bytes_reader=read_wav_bytes),
    aggregator=dict(counter=Counter, mk_pipe=mk_pipe),
    stuff_we_made=dict(),
)

factories = dict(
    source_reader=dict(
        files_of_folder=FuncFactory(Files), files_of_zip=FuncFactory(FilesOfZip),
    ),
    store_transformers=dict(
        key_transformer=key_transformer,
        val_transformer=val_transformer,
        key_filter=filter_keys,
        extract_extension=FuncFactory(extract_extension),
    ),
    object_transformation=dict(make_codec=make_decoder,),
    boolean_functions=dict(
        regular_expression_filter=regular_expression_filter,
        make_function_conjunction=make_function_conjunction,
    ),
)
# mall = dict(object_transformation=DillFiles())

from know.malls import mk_mall


mall = mk_mall(dflt_store_contents=dflt_store_contents, factories_for_store=factories)


def exectute_func(func):
    pass


def mk_app_from_mall(mall):
    from streamlitfront import mk_app

    return mk_app()
