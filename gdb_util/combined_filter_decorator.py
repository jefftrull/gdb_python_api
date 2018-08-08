# Frame filter example: remove Boost from stack trace
import gdb
import re
import codecs
# Python 2/3 way to get "imap", suggested by SO
try:
    from itertools import imap
except ImportError:
    # Python3
    imap = map

class Rot13Decorator(gdb.FrameDecorator.FrameDecorator):
    def __init__(self, fobj):
        super(Rot13Decorator, self).__init__(fobj)

    # boilerplate omitted...
    def function(self):
        name = self.inferior_frame().name()
        return codecs.getencoder('rot13')(name)[0]

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
        f_iter = filter(lambda f : re.match(r"^boost::", f.function()) is None,
                        frame_iter)
        # wrap that in our decorator
        return imap(Rot13Decorator, f_iter)

BoostFilter()
