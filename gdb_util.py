# Some utility functions for working with gdb
import gdb
from gdb.FrameDecorator import FrameDecorator
from collections import defaultdict

class StackPrinter:
    """Make ASCII art from a stack frame"""

    def __init__(self, frame):
        self._frame = frame
        self._decorator = FrameDecorator(self._frame)

    def __str__(self):
        if not self._frame.is_valid():
            return "<invalid>"
        result = ""
        # some basic frame stats
        if self._frame.function() is not None:
            result = result + "in " + self._frame.function().name
        else:
            result = result + "<unknown function>"
        if not self._frame.type() == gdb.NORMAL_FRAME:
            # IDK what to do
            return result
        result = result + "\npc = " + '{:02X}'.format(self._frame.pc())
        result = result + "\nsp = " + str(self._frame.read_register('sp'))

        locls = self.__stackmap(self._decorator.frame_locals())

        result = result + "\nLOCALS"
        for addr,symlist in locls.items():
            result = result + "\n" + '0x{:02x}'.format(addr)
            result = result + ",".join([" " + str(sym.name) + " (" + str(sym.type.sizeof) + ")" for sym in symlist])

        args = self.__stackmap(self._decorator.frame_args())

        result = result + "\nARGS"
        for addr,symlist in args.items():
            result = result + "\n" + '0x{:02x}'.format(addr)
            result = result + ",".join([" " + str(sym.name) + " (" + str(sym.type.sizeof) + ")" for sym in symlist])

        # assuming we are built with -fno-omit-frame-pointer here.  Not sure how to access
        # debug info that could tell us more, otherwise. More info is clearly present in C
        # (otherwise "info frame" could not do its job).

        # *(rbp+0x8) is the stored old IP
        result = result + "\n" + str(self._frame.read_register('rbp')+0x8) + " return address"
        voidstarstar = gdb.lookup_type("void").pointer().pointer()
        result = result + " (" + str((self._frame.read_register('rbp')+0x8).cast(voidstarstar).dereference()) + ")"

        # *(rbp) is the old RBP
        result = result + "\n" + str(self._frame.read_register('rbp')+0x0) + " saved rbp"

        # print rest of stack, displaying locals
        for addr in range(self._frame.read_register('rbp')-0x8,
                          self._frame.read_register('sp')-0x8,
                          -0x8):
            addr_hex = '0x{:02x}'.format(addr)
            result = result + "\n" + addr_hex
            # Is this address associated with a local?
            if addr in locls:
                result = result + " " + ",".join([sym.name for sym in locls[addr]])

        return result

    # produce a dict mapping addresses to symbol lists
    # for a given list of items (args or locals)
    def __stackmap(self, frame_items):
        symbolmap = defaultdict(list)
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
