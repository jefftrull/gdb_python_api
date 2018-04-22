# Some utility functions for working with gdb
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
from gdb.FrameDecorator import FrameDecorator
from collections import defaultdict
import sys
import re
from os import path
sys.path.append(path.dirname(__file__))   # look in *this* directory for others
from libclang_helpers import getASTNode, getASTSibling, getFuncName
from clang.cindex import CursorKind

class FramePrinter:
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

# Set breakpoints on "downstream" user code, continue until you reach one, then remove breakpoints
class StepUser (gdb.Command):
    """Step to the next user code"""

    def __init__ (self):
        super (StepUser, self).__init__ ("stepu", gdb.COMMAND_BREAKPOINTS)

    # class globals
    finishBP = None       # for remembering where to resume
    stepRegex = None      # for identifying "library" (skippable) calls

    def invoke (self, arg, from_tty):
        parent = None
        try:
            # find the AST node closest to the beginning of the current line
            line = gdb.newest_frame().find_sal().line
            node = getASTNode(gdb.newest_frame().find_sal().symtab.filename,
                              line, 1)
            # If the location of this node is prior to the current line, it probably represents
            # the parent to our desired node. Find the first child at or after our desired location.
            if node.location.line < line:
                parent = node
                node = next(cur for cur in node.get_children() if cur.location.line >= line)
            elif node.kind == CursorKind.FUNCTION_DECL:
                # the body is a compound statement at the end of the children
                parent = node
                node = list(parent.get_children())[-1]
                if node.kind == CursorKind.COMPOUND_STMT and len(list(node.get_children())) > 0:
                    # grab the first statement
                    parent = node
                    node = next(parent.get_children())

            # Flag error if none
            if node is None:
                raise RuntimeError('Cannot find breakpoint location for line %d'%line)

            breakpoints = self._breakInFunctions(node)

        except gdb.error:
            print("gdb got an error trying to find our location. Maybe we are not currently running?")

        # ensure we don't duplicate any breakpoints
        breakpoints = list(set(breakpoints))

        # turn them into gdb breakpoints
        breakpoints = [gdb.Breakpoint('%s:%d'%x, internal=True) for x in breakpoints]

        # set a "finish" breakpoint for the node following ours in the AST
        # i.e., the next child of the CompoundStmt
        # or the end of the frame, if we are the last
        nextStmt = getASTSibling(parent, node)
        if nextStmt is None:
            if not gdb.selected_frame() == gdb.newest_frame():
                # create default finish breakpoint
                StepUser.finishBP = gdb.FinishBreakpoint(internal=True)  # on by default in case no other breakpoints happen
            else:
                # no point in doing finish breakpoint in main (or top level thread fn)
                StepUser.finishBP = None
        else:
            # use nextStmt info to set breakpoint
            StepUser.finishBP = gdb.Breakpoint('%s:%d'%(nextStmt.location.file.name, nextStmt.location.line), internal=True)

        # continue until breakpoint hit
        err = None
        try:
            gdb.execute("continue")
        except gdb.error as e:
            err = e

        # delete our breakpoints
        for bp in breakpoints:
            bp.delete()

        if StepUser.finishBP and StepUser.finishBP.is_valid():
            # disable "finish" breakpoint
            StepUser.finishBP.enabled = False
        else:
            # we must have hit this guard breakpoint
            # there is nowhere to continue to
            StepUser.finishBP = None

        # rethrow any errors
        if err:
            raise err

    # call expressions are a bit funny
    # I experimented with the AST a bit to come up with these:

    @staticmethod
    def _getMemberBody(node):
        # member function calls have a weird structure:
        # the CALL_EXPR has one UNEXPOSED_EXPR child, which in turn has a CALL_EXPR child
        # which has a MEMBER_REF_EXPR child
        if node.kind is not CursorKind.CALL_EXPR:
            return None
        if len(list(node.get_children())) != 1 or next(node.get_children()).kind != CursorKind.UNEXPOSED_EXPR:
            return None
        unexp_node = next(node.get_children())
        if len(list(unexp_node.get_children())) != 1 or next(unexp_node.get_children()).kind != CursorKind.CALL_EXPR:
            return None
        gchild_node = next(unexp_node.get_children())
        # now we have a CALL_EXPR. The first child should be information about the function itself
        if len(list(gchild_node.get_children())) != 1 or next(gchild_node.get_children()).kind != CursorKind.MEMBER_REF_EXPR:
            return None

        # Now we want this CALL_EXPR's referenced definition (which we know is a member function)
        if not gchild_node.referenced or len(list(gchild_node.referenced.get_children())) != 2:
            return None
        child_it = gchild_node.referenced.get_children()
        next(child_it)     # discard declaration stuff, for now
        body = next(child_it)
        if body.kind is not CursorKind.COMPOUND_STMT:
            return None

        return body     # got it!

    @staticmethod
    def _getLambdaBody(node):
        # CALL_EXPR with one UNEXPOSED_EXPR child, which in turn has a LAMBDA_EXPR child
        if node.kind is not CursorKind.CALL_EXPR:
            return None
        if len(list(node.get_children())) != 1 or next(node.get_children()).kind is not CursorKind.UNEXPOSED_EXPR:
            return None
        unexp_node = next(node.get_children())
        if len(list(unexp_node.get_children())) != 1 or next(unexp_node.get_children()).kind is not CursorKind.LAMBDA_EXPR:
            return None
        lexpr = next(unexp_node.get_children())
        # the *last* child should be the body
        body = list(lexpr.get_children())[-1]
        if body.kind is not CursorKind.COMPOUND_STMT:
            return None
        return body

    @staticmethod
    def _getFunctionBody(node):
        # a regular named function seems to get the simplest treatment:
        # you can use "referenced" to get the definition
        if not node.referenced:
            return None

        if len(list(node.referenced.get_children())) == 0:
            return None   # we at least need a body node

        body = list(node.referenced.get_children())[-1]
        if body.kind is not CursorKind.COMPOUND_STMT:
            return None   # not sure why this would ever be true but...

        return body

    @staticmethod
    def _getMethodBodies(node):
        methods = []
        for m in node.get_children():
            if m.kind is CursorKind.CXX_METHOD:
                body = next(m.get_children())
                if body.kind is CursorKind.COMPOUND_STMT:
                    methods.append(body)

        return methods


    # set breakpoints on downstream
    @staticmethod
    def _breakInFunctions(node):
        breakpoints = []

        # If the child is an "unexposed expression" find its child.
        if node.kind.is_unexposed():
            # Flag error if none or more than one
            if len(list(node.get_children())) != 1:
                raise RuntimeError('Unexposed expression at line %d has more than one child, unsure how to handle'%node.location.line)
            node = next(node.get_children())

        if node.kind.is_unexposed():
            raise RuntimeError('parent and child AST nodes both unexposed at line %d'%node.location.line)

        if node.kind == CursorKind.CALL_EXPR:
            # check for member function call
            body = StepUser._getMemberBody(node)
            if body is None:
                # maybe it's a plain function
                body = StepUser._getFunctionBody(node)

            if body:
                # implement breakpoint pattern match here:
                if re.match(StepUser.stepRegex, getFuncName(body.semantic_parent)):
                    body = None
            else:
                # try lambda
                body = StepUser._getLambdaBody(node)

            if body:
                first_stmt = next(body.get_children())
                breakpoints.append((first_stmt.location.file.name, first_stmt.location.line))

            # walk through the children
            for arg in node.get_arguments():
                breakpoints = breakpoints + StepUser._breakInFunctions(arg)

        if node.kind == CursorKind.DECL_REF_EXPR:
            # probably an object argument
            # check type against regex
            decl = node.referenced.type.get_declaration()
            if not re.match(StepUser.stepRegex, getFuncName(decl)):
                # locate member function bodies and breakpoint
                members = [next(x.get_children()) for x in StepUser._getMethodBodies(decl)]
                breakpoints = breakpoints + [(x.location.file.name, x.location.line) for x in members]

        return breakpoints
StepUser ()

# Continue to the end of the expression stepped into by the last StepUser
class FinishUser (gdb.Command):
    """Run forward to the end of the expression stepped into with stepu"""

    def __init__ (self):
        super (FinishUser, self).__init__ ("finishu", gdb.COMMAND_BREAKPOINTS)

    def invoke (self, arg, from_tty):
        if StepUser.finishBP and StepUser.finishBP.is_valid():
            StepUser.finishBP.enabled = True
            gdb.execute("continue")
        else:
            print('no previous stepu command found')
FinishUser()

# Allow users to specify regex used in stepping
class StepUserIgnoreRegex (gdb.Parameter):
    """Regex for functions/classes to skip through when stepping"""

    set_doc = "set this to skip different library namespaces etc."
    show_doc = "show this to see the currently skipped library namespaces etc."

    def __init__ (self):
        super (StepUserIgnoreRegex, self).__init__ ("stepu-ignore-regex",
                                                    gdb.COMMAND_BREAKPOINTS,
                                                    gdb.PARAM_STRING_NOESCAPE)
        StepUser.stepRegex = '^std::'   # default

    # required API
    def get_set_string(self):
        StepUser.stepRegex = self.value
        return StepUser.stepRegex

    def get_show_string(self, svalue):
        return StepUser.stepRegex

StepUserIgnoreRegex()

# define a stack frame filter
class UserFilter:
    """Filter library functions out of stack trace"""

    def __init__(self):
        # set required attributes
        self.name = 'UserFilter'
        self.enabled = True
        self.priority = 0

        # register with current program space
        # (manual suggests avoiding global filter list; this seems appropriate)
        gdb.current_progspace().frame_filters[self.name] = self

    @staticmethod
    def __cond_squash(iterable, squashfn):
        """wrap iterator to compress subsequences for which a predicate is true, keeping only the *last* of each"""
        last = None              # we have to buffer 1 item
        for item in iterable:
            if squashfn(item):
                last = item
            else:
                if last is not None:
                    yield last   # empty buffer this time
                    last = None
                yield item       # resume un-squashed iteration
        if last is not None:
            yield last           # in case we end in "squashed" mode

    def filter(self, frame_iter):
        # wrap the current iterator in a squash-matching-subsequences iterator
        # with the predicate "function name matches regex"
        return UserFilter.__cond_squash(frame_iter, lambda x : re.match(StepUser.stepRegex, x.function()))

UserFilter()
