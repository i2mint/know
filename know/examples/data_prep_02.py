"""
An app to take care of the initial 'sourcing' part of the data prep of audio ML
"""
from typing import Mapping
from know.boxes import *
from functools import partial
from typing import Callable, Iterable
from front import APP_KEY, RENDERING_KEY, ELEMENT_KEY, NAME_KEY
from i2 import Pipe, Sig
from front.crude import Crudifier, prepare_for_crude_dispatch

from streamlitfront import mk_app, binder as b
from streamlitfront.elements import (
    SelectBox,
    SuccessNotification,
    KwargsInput,
    PipelineMaker,
)


def mk_pipeline_maker_app_with_mall(
    mall: Mapping,
    *,
    step_factories: str = 'step_factories',
    steps: str = 'steps',
    steps_store=None,
    pipelines: str = 'pipelines',
    pipelines_store=None,
):
    # TODO: Like to not have this binder logic involving streamlit state here! Contain it!
    if not b.mall():
        # TODO: Maybe it's here that we need to use know.malls.mk_mall?
        b.mall = mall
    mall = b.mall()
    if not b.selected_step_factory():
        b.selected_step_factory = 'files_of_folder'

    crudifier = partial(Crudifier, mall=mall)

    steps_store = steps_store or steps
    pipelines_store = pipelines_store or pipelines

    @crudifier(
        param_to_mall_map=dict(step_factory=step_factories), output_store=steps_store
    )
    def mk_step(step_factory: Callable, kwargs: dict):
        return partial(step_factory, **kwargs)

    #
    @crudifier(
        # TODO: Want to be able to do this and this only to have the effect
        # param_to_mall_map=dict(steps=steps),
        output_store=pipelines_store
    )
    def mk_pipeline(steps: Iterable[Callable]):
        print(type(steps))
        return Pipe(*steps)

    @crudifier(
        # TODO: Does this work if pipelines_store is a mapping instead of a string?
        param_to_mall_map=dict(pipeline=pipelines_store),
        # output_store='exec_outputs'
    )
    def exec_pipeline(pipeline: Callable, kwargs):
        pipe = pipeline(**kwargs)
        return pipe

    # NOTE: Just ideas. call_func not used:
    # @crudifier(
    #     param_to_mall_map=dict(pipeline='pipelines'),
    #     # output_store='exec_outputs'
    # )
    def call_func(func: Callable, *args, **kwargs):
        return func(*args, **kwargs)

    def get_step_name(step):
        return [k for k, v in mall[steps].items() if v == step][0]

    def get_selected_pipeline_sig():
        if not b.selected_pipeline():
            return Sig()
        return Sig(mall[pipelines][b.selected_pipeline()])

    config = {
        APP_KEY: {'title': 'Data Preparation'},
        RENDERING_KEY: {
            'mk_step': {
                NAME_KEY: 'Pipeline Step Maker',
                'execution': {
                    'inputs': {
                        'step_factory': {'value': b.selected_step_factory,},
                        'kwargs': {
                            'func_sig': Sig(
                                mall[step_factories][b.selected_step_factory()]
                            ),
                        },
                    },
                    'output': {
                        ELEMENT_KEY: SuccessNotification,
                        'message': 'The step has been created successfully.',
                    },
                },
            },
            'mk_pipeline': {
                NAME_KEY: 'Pipeline Maker',
                'execution': {
                    'inputs': {
                        steps: {
                            ELEMENT_KEY: PipelineMaker,
                            'items': list(mall[steps].values()),
                            'serializer': get_step_name,
                        },
                    },
                    'output': {
                        ELEMENT_KEY: SuccessNotification,
                        'message': 'The pipeline has been created successfully.',
                    },
                },
            },
            'exec_pipeline': {
                NAME_KEY: 'Pipeline Executor',
                'execution': {
                    'inputs': {
                        'pipeline': {'value': b.selected_pipeline,},
                        'kwargs': {
                            ELEMENT_KEY: KwargsInput,
                            'func_sig': get_selected_pipeline_sig(),
                        },
                    }
                },
            },
        },
    }

    funcs = [mk_step, mk_pipeline, exec_pipeline]
    app = mk_app(funcs, config=config)

    return app


if __name__ == '__main__':
    # TODO: Try with know.malls.mk_mall:

    mall = dict(
        # Factory Input Stores
        # TODO: Feed the following stores with real objects,
        # I'll let them empty for now.
        # This is clearly an ugly way to crudify params of functions that are part of
        # the same mall. Let's think about a better solution.
        # Source Readers
        # files_of_folder
        pattern_for_field=dict(),  # dicts
        # files_of_zip
        open_kws=dict(),  # dicts
        # Store Transformers
        # key_transformer
        key_of_id=dict(),  # functions
        id_of_key=dict(),  # functions
        # val_transformer
        obj_of_data=dict(),  # functions
        # key_filter
        filt=dict(),  # Union[Callable, Iterable]
        # extract_extension (nothing to crudify)
        # Object Transformation
        # make_codec (nothing to crudify)
        # Boolean Functions
        # regular_expression_filter (nothing to crudify)
        # make_function_conjunction
        func1=dict(),  # functions
        func2=dict(),  # functions
        # Output Store
        steps=dict(),
        pipelines=dict(),
        # exec_outputs=dict(),
    )

    crudifier = partial(prepare_for_crude_dispatch, mall=mall)

    step_factories = dict(
        # Source Readers
        files_of_folder=crudifier(
            FuncFactory(Files), param_to_mall_map=['pattern_for_field']
        ),
        files_of_zip=crudifier(FuncFactory(FilesOfZip), param_to_mall_map=['open_kws']),
        # Store Transformers
        key_transformer=crudifier(
            key_transformer, param_to_mall_map=['key_of_id', 'id_of_key']
        ),
        val_transformer=crudifier(val_transformer, param_to_mall_map=['obj_of_data']),
        key_filter=crudifier(filter_keys, param_to_mall_map=['filt']),
        extract_extension=FuncFactory(extract_extension),
        # Object Transformation
        make_codec=make_decoder,
        # Boolean Functions
        regular_expression_filter=regular_expression_filter,
        make_function_conjunction=crudifier(
            make_function_conjunction, param_to_mall_map=['func1', 'func2']
        ),
    )

    mall['step_factories'] = step_factories

    app = mk_pipeline_maker_app_with_mall(
        mall, step_factories='step_factories', steps='steps', pipelines='pipelines'
    )

    app()
