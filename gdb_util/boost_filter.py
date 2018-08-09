# Frame filter example: remove Boost from stack trace
import gdb
import re

# Python 2/3 way to get "imap", suggested by SO
try:
    from itertools import imap
except ImportError:
    # Python3
    imap = map

# Create and register filter that uses it
class BoostFilter:
    def __init__(self):
        # set required attributes
        self.name = 'BoostFilter'
        self.enabled = True
        self.priority = 0

        # register with current program space
        gdb.current_progspace().frame_filters[self.name] = self

    def filter(self, frame_iter):
        # compose new iterator that excludes Boost function frames
        return filter(lambda f : re.match(r"^boost::", f.function()) is None,
                      frame_iter)

BoostFilter()
