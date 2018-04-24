# utilities for visualizing x86 stack frames
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
from collections import defaultdict

class FramePrinter:
    """Make ASCII art from a stack frame"""

    def __init__(self, frame):
        self._frame = frame
        self._decorator = gdb.FrameDecorator.FrameDecorator(self._frame)

    def __str__(self):
        if not self._frame.is_valid():
            return "<invalid>"
        result = ""
        # some basic frame stats
        if self._frame.function() is not None:
            result = result + "in " + self._frame.function().name
            if self._frame.type() is gdb.INLINE_FRAME:
                # recursively show inlining until we find a "real" parent frame
                result = result + "\ninlined with" + str(FramePrinter(self._frame.older()))
        else:
            result = result + "<unknown function>"
        if (self._frame.type() != gdb.NORMAL_FRAME):
            # IDK what else to do
            return result

        locls = self.__stackmap(self._decorator.frame_locals())
        args = self.__stackmap(self._decorator.frame_args())

        # assuming we are built with -fno-omit-frame-pointer here.  Not sure how to access
        # debug info that could tell us more, otherwise. More info is clearly present in C
        # (otherwise "info frame" could not do its job).

        # Display args
        yellow = "\u001b[33m"
        reset_color = "\u001b[0m"

        # find the address range of our args
        # from there to *(rbp+0x8), exclusive, is the range of possible args
        if args.keys():
            first_arg_addr = max(args.keys())    # the one with the highest address
            result = result + self.__subframe_display(first_arg_addr,
                                                      self._frame.read_register('rbp')+0x8,
                                                      args,
                                                      yellow)

        # *(rbp+0x8) is the stored old IP
        cyan = "\u001b[36m"
        result = result + "\n" + str(self._frame.read_register('rbp')+0x8) + " return address"
        voidstarstar = gdb.lookup_type("void").pointer().pointer()
        old_ip = (self._frame.read_register('rbp')+0x8).cast(voidstarstar).dereference()
        result = result + cyan + " (" + str(old_ip) + ")" + reset_color

        # *(rbp) is the old RBP
        result = result + "\n" + str(self._frame.read_register('rbp')+0x0) + " saved rbp"

        # print rest of stack, displaying locals
        green = "\u001b[32m"
        result = result + self.__subframe_display(self._frame.read_register('rbp')-0x8,
                                                  self._frame.read_register('sp')-0x8,
                                                  locls,
                                                  green)

        result = result + cyan + " <<< top of stack" + reset_color

        return result

    # display a range of stack addresses with colors, and compression of unknown contents as "stuff"
    def __subframe_display(self,
                           start, end,   # range of addresses to display
                           frame_items,  # map from addresses to lists of symbols
                           col):         # color to use for the symbols
        magenta = "\u001b[35m"
        reset_color = "\u001b[0m"
        empty_start = None
        result = ""
        for addr in range(start, end, -0x8):
            addr_hex = '0x{:02x}'.format(addr)
            if addr in frame_items:
                if empty_start:
                    # we just completed an empty range
                    if empty_start != (addr+0x8):
                        result = result + magenta + ' (through 0x{:02x})'.format(addr+0x8) + reset_color
                    empty_start = None
                result = result + "\n" + addr_hex
                result = result + " " + col + ",".join([sym.name for sym in frame_items[addr]]) + reset_color
            elif empty_start is None:
                # we are starting an empty range
                empty_start = addr
                result = result + "\n" + addr_hex + magenta + " stuff" + reset_color

        if empty_start and (empty_start != end+0x8):
            # the empty range has more than one dword and extended through the end of the subframe
            result = result + magenta + ' (through ' + str(end+0x8) + ')' + reset_color

        return result


    # produce a dict mapping addresses to symbol lists
    # for a given list of items (args or locals)
    def __stackmap(self, frame_items):
        symbolmap = defaultdict(list)
        if not frame_items:
            return symbolmap

        for i in frame_items:
            name = i.symbol().name
            addr = self._frame.read_var(name).address
            if not addr == None:
                # gdb.Value is not "hashable"; keys must be something else
                # so here we use addr converted to int
                sz = i.symbol().type.sizeof
                # mark all dwords in the stack with this symbol
                addr = addr.cast(gdb.lookup_type("void").pointer()) # cast to void*
                # handle sub-dword quantities by just listing everything that overlaps
                for saddr in range(addr, addr+sz, 0x8):
                    symbolmap[int(saddr)].append(i.symbol())
        return symbolmap

# Now create a gdb command that prints the current stack:
class PrintFrame (gdb.Command):
    """Display the stack memory layout for the current frame"""

    def __init__ (self):
        super (PrintFrame, self).__init__ ("pframe", gdb.COMMAND_STACK)

    def invoke (self, arg, from_tty):
        try:
            print(FramePrinter(gdb.newest_frame()))
        except gdb.error:
            print("gdb got an error. Maybe we are not currently running?")

PrintFrame ()

