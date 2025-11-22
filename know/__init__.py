"""
Build live stream tools

The tools are made to be able to create live streams of data
(e.g. from sensors) and funnel them into proceses with a consistent interfaces.
One important process being the process that will store all or part of
the data, through a simple storage-system-agnositic facade.

Note: Core streaming functionality (SlabsIter) has moved to the meshed package.
This package now focuses on providing utility tools for context management
and data processing.

Main exports:
- ContextualFunc: Wrap functions as context managers
- any_value_is_none: Check if any mapping value is None
- ContextFanout: Multi-context manager (from i2)
"""

from know.util import ContextFanout, any_value_is_none, ContextualFunc
