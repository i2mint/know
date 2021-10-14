"""
Build live stream tools

Essentially being able to do this:

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
