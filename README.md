# know

Build live stream tools

To install:	```pip install know```

The tools are made to be able to create live streams of data
(e.g. from sensors) and funnel them into proceses with a consistent interfaces.
One important process being the process that will store all or part of
the data, through a simple storage-system-agnositic facade.

> **Note on Package Evolution**: Core streaming functionality (including `SlabsIter`) has been moved to the [`meshed`](https://github.com/i2mint/meshed) package (formerly in [`creek`](https://github.com/i2mint/creek)). The `know` package now focuses on providing utility tools for context management and data processing. For slab iteration and stream processing, please use `meshed.slabs`.

## Main Exports

The `know` package currently exports the following main utilities:

### `ContextualFunc`

Wrap a function so that it's also a multi-context context manager. This is useful when a function needs specific resources managed by context managers.

```python
from know import ContextualFunc
from contextlib import contextmanager

@contextmanager
def my_resource():
    print('Setting up resource')
    yield
    print('Cleaning up resource')

# Wrap your function with the context
def process_data(x):
    return x * 2

contextual_process = ContextualFunc(process_data, my_resource())

# Use it as a context manager
with contextual_process:
    result = contextual_process(21)  # prints: Setting up resource
    print(result)  # 42
# prints: Cleaning up resource
```

### `any_value_is_none`

Simple utility to check if any value in a mapping is None:

```python
from know import any_value_is_none

any_value_is_none({'a': 1, 'b': 2})        # False
any_value_is_none({'a': 1, 'b': None})     # True
```

### `ContextFanout`

Multi-context manager (imported from `i2` package) for managing multiple contexts at once.


# Historical Examples

> **Note**: The following examples demonstrate audio recording and storage capabilities that were part of earlier versions of `know`. These examples still work but represent functionality that may be better suited for specialized packages. The examples are kept here for reference and backward compatibility.

## Recording Audio

```python
from know.audio_to_store import *

wfs = demo_live_data_acquisition(chk_size=100_000, end_idx=300_000, logger=print)
print(f"{len(wfs)=}")
```

The `end_idx=300_000` is there to automatically stop the demo after 300 thousand bytes are acquired 
(at the default rates that's about 1.5 seconds). 

If you specify `end_idx=None`, the process will run until you interrupt it.

## Recording Audio, with more control

Here's what's actually being fed to the demo when you don't specify any explicit `live_source` or `store`. 
You can use this to try different combinations of specs out:

```python
from know.audio_to_store import *

wfs = demo_live_data_acquisition(
    live_source=LiveWf(
        input_device_index=None,  # if None, will try to guess the device index
        sr=44100,
        sample_width=2,
        chk_size=4096,
        stream_buffer_size_s=60,
    ),
    store=mk_session_block_wf_store(
        rootdir=None,  # will choose one for you
        # template examples: '{session}_{block}.wav' '{session}/d/{block}.pcm', '{session}/{block}', 'demo/s_{session}/blocks/{block}.wav'
        template='{session}/d/{block}.pcm',  # 
        pattern=r'\d+',
        value_trans=int
    ),
    chk_size=100_000,
    end_idx=300_000,
    logger=print
)
print(f"{len(wfs)=}")
```

What you want to see above, is how you can easily change the folder/file template you use to store data. 

Below, we'll also show how you can change the data storage system backend completely, 
using a mongo database instead!


## 

Here, see how you can use MongoDB to store your data. 
For this, you'll need to have a [mongoDB](https://www.mongodb.com/) server running locally, 
and [mongodol](https://pypi.org/project/mongodol/) installed (`pip install mongodol`). 

```python

from know.audio_to_store import mk_mongo_single_data


def _cast_data_field_to_json_list(d):
    return list(map(int, d))


play_nice_with_json = wrap_kvs(data_of_obj=_cast_data_field_to_json_list)

mongo_store = play_nice_with_json(
    mk_mongo_single_data(
        mgc='mongodol/test',  # enter here, the `db_name/collection_name` you want to use (uses local mongo client)
        key_fields=('session', 'block'),
        data_field='data'
    )
)

wfs = demo_live_data_acquisition(
    live_source=LiveWf(
        input_device_index=None,  # if None, will try to guess the device index
        sr=44100,
        sample_width=2,
        chk_size=4096,
        stream_buffer_size_s=60,
    ),
    store=mongo_store,
    chk_size=100_000,
    end_idx=300_000,
    logger=print
)
print(f"{len(wfs)=}")
```







