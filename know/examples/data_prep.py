"""An app ot make data prep tools"""


from know.boxes import *

dflt_store_contents = dict(
    object_transformation=dict(default_wav_bytes_reader=read_wav_bytes),
    aggregator=dict(counter=Counter),
)

factories = dict(
    source_reader=dict(
        files_of_folder=FuncFactory(Files),
        files_of_zip=FuncFactory(FilesOfZip),
    ),
    store_transformers=dict(
        key_transformer=key_transformer,
        val_transformer=val_transformer,
        key_filter=filt_iter,
        extract_extension=FuncFactory(extract_extension),
    ),
    object_transformation=dict(
        make_codec=make_decoder,
    ),
    boolean_functions=dict(
        regular_expression_filter=regular_expression_filter,
    ),
)
# mall = dict(object_transformation=DillFiles())

from know.malls import mk_mall


mall = mk_mall(dflt_store_contents=dflt_store_contents, factories_for_store=factories)

