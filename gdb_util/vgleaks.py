# Utilities for finding leaks in code via Valgrind's gdb extensions
# Copyright (c) 2018 Jeff Trull

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gdb
import re


# single step until Valgrind reports a leak (sloooowwww)
class StepToLeak(gdb.Command):
    """Step until valgrind reports a leak"""

    def __init__ (self):
        super (StepToLeak, self).__init__ ("stepl", gdb.COMMAND_BREAKPOINTS)

    def invoke(self, arg, from_tty):
        result = gdb.execute('mo leak full', False, True)
        while result.find('are definitely lost in loss record') is -1:
            try:
                gdb.execute('step', to_string = True)  # QUIETLY step
            except gdb.error:
                print('error while stepping')  # BOZO handle
                break
            result = gdb.execute('mo leak full', False, True)
        print('loss report:\n%s'%result)
        print('leak first noticed at:\n')
        gdb.execute('bt')

StepToLeak()

# when you've found a leak this will look for reference loops
class PrintRefLoop(gdb.Command):
    """Find a reference loop in the leak report"""

    def __init__ (self):
        super (PrintRefLoop, self).__init__ ("frl", gdb.COMMAND_BREAKPOINTS)   # BOZO what is right category?

    @staticmethod
    def _get_pointers(block_addr):
        """For a given address, find all pointers to it from other blocks

        Returns a dict of addresses (hex strings) to backtraces, for each allocation
        """

        wpatxt = gdb.execute('monitor who_points_at %s'%block_addr, to_string = True)

        addr_re  = re.compile('^ Address (0x[0-9A-Fa-f]+) is ([0-9]+) bytes inside a block.*')
        trace_re = re.compile('(at|by) 0x[0-9A-Fa-f]+: ')
        wpait = iter(wpatxt.splitlines())
        result = {}
        wpaln = next(wpait, None)
        while wpaln is not None:
            m = addr_re.match(wpaln)
            if m:
                ptr = m.group(1)
                ofs = int(m.group(2))
                # calculate the base of its block
                base = '0x{:02X}'.format(int(ptr, 0)-ofs)
                if base == block_addr:
                    wpaln = next(wpait, None)
                    continue
                # suck in the backtrace associated with the allocation for this block
                trace = ''
                wpaln = next(wpait, None)
                while wpaln is not None and trace_re.search(wpaln):
                    trace += wpaln + '\n'
                    wpaln = next(wpait, None)
                result[ptr] = trace
            wpaln = next(wpait, None)
        return result

    def invoke(self, arg, from_tty):
        leak_rpt = gdb.execute('monitor leak_check full any', to_string = True)

        # extract the loss record number from the leak report
        rx = re.compile('are definitely lost in loss record ([0-9]+) of')
        m = rx.search(leak_rpt)
        if not m:
            print('no loops found')
            return

        # request block list for that record number
        blockno = m.group(1)
        bl_rpt = gdb.execute('monitor block_list %s'%blockno, to_string = True)

        # extract the first block and call "who_points_at" to get pointers
        # key part is the single indentation - the first entry:
        blre = re.compile('=+[0-9]+=+ (0x[0-9A-F]+)\[')
        m = blre.search(bl_rpt)
        wpa_dict = PrintRefLoop._get_pointers(m.group(1))

        for addr, bt in wpa_dict.items():   # "viewitems" in Python 2.7
            print('for address %s we have the following backtrace:'%addr)
            print(bt)

        # commence DFS based on that vertex and edges

PrintRefLoop()
