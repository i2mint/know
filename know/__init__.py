"""
Build live stream tools

Essentially being able to do this:

The tools are made to be able to create live streams of data
(e.g. from sensors) and funnel them into proceses with a consistent interfaces.
One important process being the process that will store all or part of
the data, through a simple storage-system-agnositic facade.

```python
proc = LiveProc(
   source=Sources(  # make a multi-source object (which will manage buffering and timing)
       audio=AudioSource(...),
       plc=PlcSource(...),
       video=VideoSource(...),
   ),
   consumers=Consumers(  # make a multi-data consumer (and/or writer/transformer) object
       storage=Store(...),
       notifications=Notif(...),
       live_viz=LiveViz(...),
   ),
   ...  # other settings for the process (logging, etc.)
)

proc()  # run the process
```

With a variety of sources, target storage systems, etc.


"""

from know.util import ContextFanout, FuncFanout, MultiIterable, any_value_is_none
