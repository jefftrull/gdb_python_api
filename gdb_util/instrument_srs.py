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
    def __init__(self, vec):
        Thread.__init__(self)
        self.vec = vec              # the vector we are monitoring
        self.messages = Queue()     # cross-thread communication

    # next, something to do when we swap
    def show_swap(self, a, b):  # Python values being swapped
        # notify GUI of swap event
        self._send_message('swapping values at %s (%s) and %s(%s)'%(
            a.address,a.referenced_value(),b.address,b.referenced_value()))

    def _send_message(self, msg): # for talking to our thread
        self.messages.put(msg)   # contents are swap info

    def _check_for_messages(self):
        # poll command queue
        # not ideal but safe. OK for now.
        if not self.messages.empty():
            cmd = self.messages.get()
            print('got command %s'%cmd)

    def run(self):
        # a warning message about not being run in the main thread gets printed
        # everything I can find suggests this is not a real issue, so long as
        # all QObject access happens in the same thread, which it is.
        self.app = QApplication([])

        # periodically poll command queue
        self.cmd_poll_timer = QTimer()
        self.cmd_poll_timer.timeout.connect(self._check_for_messages)
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

# actions for when we arrive at std::sort
# TODO is there a way to improve this formatting?
tf.write(("commands %d\n"
          "py gdb_util.instrument_srs.gui = gdb_util.instrument_srs.GuiThread(gdb.selected_frame().older().read_var('A'))\n"
          "py gdb_util.instrument_srs.gui.start()\n"
          "enable %d\n"
          "c\n"
          "end\n")%(sort_bp.number, swap_bp.number))

# actions for each swap()
tf.write(("commands %d\n"
          "py gdb_util.instrument_srs.gui.show_swap(gdb.selected_frame().read_var('a'), gdb.selected_frame().read_var('b'))\n"
          "c\n"
          "end\n")%swap_bp.number)
tf.flush()
tf.close()
gdb.execute('source %s'%tf.name)
os.unlink(tf.name)



