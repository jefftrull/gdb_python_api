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
from gdb_util.leak_dfs import PointerGraph, LoopFindVisitor
from graph_tool.search import dfs_search, StopSearch

# single step until Valgrind reports a leak (sloooowwww)
class StepToLeak(gdb.Command):
    """Step until valgrind reports a leak"""

    def __init__ (self):
        super (StepToLeak, self).__init__ ("stepl", gdb.COMMAND_RUNNING)

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
class PrintPtrLoop(gdb.Command):
    """Find a reference loop in the leak report"""

    def __init__ (self):
        super (PrintPtrLoop, self).__init__ ("ppl", gdb.COMMAND_DATA)

    @staticmethod
    def _get_pointers(block_addr):
        """For a given address, find all pointers to it from other blocks

        Returns a dict of addresses (hex strings) to backtraces and internal
        pointers, for each allocation
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
                result[base] = trace   # TODO also store addresses
            wpaln = next(wpait, None)
        return result

    # utility functions for the DFS

    # we are doing an "implicit" graph here, i.e., we do not know all the vertices (blocks)
    # in advance. Accordingly our Visitor needs a function to insert the neighbors of any
    # newly arrived at vertices so the search can proceed.
    # This serves that role by asking Valgrind for all blocks with pointers to us

    @staticmethod
    def expand_vertex(g, u):
        addr = g.vaddr_pmap[u]
        ptr_dict = PrintPtrLoop._get_pointers(addr)
        for ptr in ptr_dict:
            if ptr not in g.addr2v:
                e = g.create_ptr_edge(ptr, u)
                g.backtraces[e.target()] = ptr_dict[ptr]
            else:
                # only add the edge
                g.add_edge(u, g.addr2v[ptr])

    # Action to take when we find a back edge to the starting point
    # We print out the block addresses and optional the backtraces of the allocation

    @staticmethod
    def report_backedge(g, e, pred):
        print('Pointer loop detected:')
        print_backtrace = gdb.parameter('ppl-backtrace')

        # e is the final edge that completes the loop
        # we want to display the previous edges, in order, followed by e
        # the predecessor map gives them to us in reverse
        path = [int(e.target()), int(e.source())]   # reversed path by vertex index
        v = int(e.source())
        while v is not int(e.target()):
            v = pred[v]
            path.append(v)
        # now print "path" by edge, reversed, followed by the final edge
        # zip (reversed) path with itself, offset, to get pairs of vertices
        # see "pairwise" recipe in itertools docs
        sources = iter(path)
        targets = iter(path)
        next(targets, None)     # shift targets by one so edges line up
        for u, v in zip(sources, targets):
            print('block %s has pointers to block %s'%(g.vaddr_pmap[u], g.vaddr_pmap[v]))
            if print_backtrace:
                print(g.backtraces[u])
        # terminate loop search
        raise StopSearch()

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

        # get the allocation backtrace for this initial block
        trace_re = re.compile('(at|by) 0x[0-9A-Fa-f]+: ')
        backtrace = ''
        for ln in bl_rpt.splitlines():
            if trace_re.search(ln):
                backtrace += ln + '\n'

        # extract the first block and call "who_points_at" to get pointers
        # key part is the single indentation - the first entry:
        blre = re.compile('=+[0-9]+=+ (0x[0-9A-F]+)\[')
        m = blre.search(bl_rpt)

        g = PointerGraph(m.group(1))
        g.backtraces = g.new_vertex_property('string')
        g.backtraces[g.root] = backtrace
        pred = g.new_vertex_property('int64_t')
        vis = LoopFindVisitor(g, pred, PrintPtrLoop.expand_vertex, PrintPtrLoop.report_backedge)
        dfs_search(g, g.root, vis)

PrintPtrLoop()

# Let users specify the display of tracebacks for allocations in pointer loops
class PtrLoopBacktrace(gdb.Parameter):
    """Enable printing of allocation backtraces"""

    set_doc = "True to get (verbose) backtraces for each block allocated in a loop"
    show_doc = "Show whether we display allocation backtraces for blocks in a loop"

    def __init__(self):
        super(PtrLoopBacktrace, self).__init__("ppl-backtrace",
                                               gdb.COMMAND_DATA,
                                               gdb.PARAM_BOOLEAN)
        PtrLoopBacktrace.printBacktrace = False

    def get_set_string(self):
        PtrLoopBacktrace.printBacktrace = self.value
        return 'on' if self.value else 'off'

    def get_show_string(self, svalue):
        return svalue

PtrLoopBacktrace()
