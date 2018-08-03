# code to instrument std::sort for my custom type
# see examples/sort_random_sequence.cpp

import gdb
import tempfile
import os
from threading import Thread
from queue import Queue

# animated display of operation
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer

class SwapAnimation(QMainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()

        self.setStyleSheet('background-color: yellow')
        self.timer = QTimer()
        self.timer.timeout.connect(self._timeout)
        self.timer.start(1000)


    def _timeout(self):
        self.setStyleSheet('background-color: brown')


class GuiThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.commands = Queue()

    def _check_for_commands(self):
        # poll command queue
        # not ideal but safe. OK for now.
        if not self.commands.empty():
            cmd = self.commands.get()
            print('got command %s'%cmd)

    def run(self):
        # a warning message about not being run in the main thread gets printed
        # everything I can find suggests this is not a real issue, so long as
        # all QObject access happens in the same thread, which it is.
        self.app = QApplication([])

        # periodically poll command queue
        self.cmd_poll_timer = QTimer()
        self.cmd_poll_timer.timeout.connect(self._check_for_commands)
        self.cmd_poll_timer.start(100)   # 100ms doesn't seem too terrible *shrug*

        self.top = SwapAnimation()
        self.top.show()
        self.app.exec_()


# first, two breakpoints
# my special swap, initially disabled to avoid the call to std::shuffle
swap_bp = gdb.Breakpoint('swap(int_wrapper_t&, int_wrapper_t&)')
swap_bp.enabled = False
# we need the whole thing including template parameters here:
sort_bp = gdb.Breakpoint('std::sort<std::vector<int_wrapper_t, std::allocator<int_wrapper_t> >::iterator>')

# next prepare to enable and execute the swap display commands

# breakpoint's commands property was made writable too recently for me to use:
# https://sourceware.org/bugzilla/show_bug.cgi?id=22731
# instead we have to write out a script to a tempfile... groan...
tf = tempfile.NamedTemporaryFile(mode='w', delete=False)
tf.write('commands %d\nenable %d\nc\nend\n'%(sort_bp.number, swap_bp.number))
tf.write('commands %d\npy gdb_util.instrument_srs._show_swap()\nc\nend\n'%swap_bp.number)
tf.flush()
tf.close()
gdb.execute('source %s'%tf.name)
os.unlink(tf.name)

gui = GuiThread()
gui.start()

# next, something to do when we swap
def _show_swap():
    frm = gdb.selected_frame()
    a = frm.read_var('a')
    b = frm.read_var('b')
    # notify GUI of swap event
    gui.commands.put('swapping values at %s (%s) and %s(%s)'%(
        a.address,a.referenced_value(),b.address,b.referenced_value()))


