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
class Rot13Filter:
    def __init__(self):
        # set required attributes
        self.name = 'Rot13Filter'
        self.enabled = True
        self.priority = 0

        # register with current program space
        gdb.current_progspace().frame_filters[self.name] = self

    def filter(self, frame_iter):
        return imap(Rot13Decorator, frame_iter)

Rot13Filter()
