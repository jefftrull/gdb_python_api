# code to instrument std::sort for my custom type
# see examples/sort_random_sequence.cpp

import gdb
import tempfile
import os

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

# next, something to do when we swap
def _show_swap():
    frm = gdb.selected_frame()
    a = frm.read_var('a')
    b = frm.read_var('b')
    print('(PY) swapping values at %s (%s) and %s(%s)'%(
        a.address,a.referenced_value(),b.address,b.referenced_value()))


