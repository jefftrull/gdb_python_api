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
            for addr in range(first_arg_addr,
                              self._frame.read_register('rbp')+0x8,
                              -0x8):
                addr_hex = '0x{:02x}'.format(addr)
                result = result + "\n" + addr_hex
                # Is this address associated with an arg?
                if addr in args:
                    result = result + " " + yellow + ",".join([sym.name for sym in args[addr]]) + reset_color

        # *(rbp+0x8) is the stored old IP
        cyan = "\u001b[36m"
        result = result + "\n" + str(self._frame.read_register('rbp')+0x8) + " return address"
        voidstarstar = gdb.lookup_type("void").pointer().pointer()
        result = result + cyan + " (" + str((self._frame.read_register('rbp')+0x8).cast(voidstarstar).dereference()) + ")" + reset_color

        # *(rbp) is the old RBP
        result = result + "\n" + str(self._frame.read_register('rbp')+0x0) + " saved rbp"

        # print rest of stack, displaying locals
        green = "\u001b[32m"
        for addr in range(self._frame.read_register('rbp')-0x8,
                          self._frame.read_register('sp')-0x8,
                          -0x8):
            addr_hex = '0x{:02x}'.format(addr)
            result = result + "\n" + addr_hex
            if addr in locls:
                result = result + " " + green + ",".join([sym.name for sym in locls[addr]]) + reset_color
        result = result + cyan + " <<< top of stack" + reset_color

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
            print(StackPrinter(gdb.newest_frame()))
        except gdb.error:
            print("gdb got an error. Maybe we are not currently running?")

PrintFrame ()
