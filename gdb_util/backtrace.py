# Utilities for scrubbing/filtering stack traces
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
# Python 2/3 way to get "imap", suggested by SO
try:
    from itertools import imap
except ImportError:
    # Python3
    imap = map

# define a stack frame decorator to make them less verbose
class CommonAliasDecorator(gdb.FrameDecorator.FrameDecorator):
    def __init__(self, fobj):
        super(CommonAliasDecorator, self).__init__(fobj)

    # rewrite the function name to make it a bit less ugly:
    def function(self):
        name = self.inferior_frame().name()
        if name.startswith("<lambda"):
            # this starts with an angle bracket but won't have any template parameters
            return name
        # rename std::string
        orig = name
        name = re.sub('std::__cxx11::basic_string<char>', 'std::string', name)
        name = re.sub('std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >', 'std::string', name)
        # turn std::vector<T, std::allocator<T>> into std::vector<T>
        name = re.sub(r"std::vector<([^<>]*), std::allocator<\1 > >", r"std::vector<\1 >", name)
        # turn __gnu_cxx::__normal_iterator<T*, std::vector<T > > into std::vector<T>::iterator
        name = re.sub(r"__gnu_cxx::__normal_iterator<(.*)\*, std::vector<\1 > >", r"std::vector<\1 >::iterator", name)
        name = re.sub(r"__gnu_cxx::__normal_iterator<(.*)\*, std::vector<\1, std::allocator<\1 > > >", r"std::vector<\1 >::iterator", name)

        return name

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

    @staticmethod
    def __adjacent_squash(iterable, squashfn):
        """wrap iterator to compress subsequences with a binary predicate

        This adapter will drop all but the last of any sequence for which
        squashfn(prev, current) is true
        """

        last = None
        for item in iterable:
            if last is None:
                last = item
            else:
                if squashfn(last, item):
                    # discard previous
                    last = item
                else:
                    yield last
                    last = item
        if last is not None:
            yield last

    @staticmethod
    def __same_cgroup(prog, a, b):
        """return true if a and b match the same capture group of prog"""

        if (a.function() == a.address()) or (b.function() == b.address()):
            # we don't know the function name for at least one of the frames
            return False
        if not prog.match(str(a.function())) or not prog.match(str(b.function())):
            # at least one doesn't match at all
            return False
        a_match = prog.match(a.function())
        b_match = prog.match(b.function())
        if a_match.lastindex is None or b_match.lastindex is None:
            # no capture group matched in one or both
            return False
        # figure out if there are any matching capture groups
        # "groups" will give us a tuple of all the capture groups
        # and None if the particular group did not match
        for a, b in zip(a_match.groups(), b_match.groups()):
            if a is not None and b is not None:
                return True

        return False


    def filter(self, frame_iter):
        # first check for multi-regex option
        squash_regexes = gdb.parameter('backtrace-strip-regexes')
        # If present we compress stack frames with matching capture groups
        if squash_regexes:
            prog = re.compile(squash_regexes)
            # if there are no (or one) capture groups, treat this like squash_regex
            if prog.groups < 2:
                squash_regex = squash_regexes
            else:
                # wrap the current iterator in a squash-matching-subsequences iterator
                # with the predicate "function name matches same regex"
                ufi = UserFilter.__adjacent_squash(frame_iter,
                                                   lambda a, b : UserFilter.__same_cgroup(prog, a, b))
                # further wrap in a decorator and return
                return imap(CommonAliasDecorator, ufi)
        else:
            # single regex is simpler - we compress based on match/nomatch
            squash_regex = gdb.parameter('backtrace-strip-regex')

        if squash_regex:
            ufi = UserFilter.__cond_squash(frame_iter,
                                           lambda x : ((x.function() != x.address()) and
                                                       re.match(squash_regex, x.function())))
            return imap(CommonAliasDecorator, ufi)
        else:
            # just add the decorator to the original iterator
            return imap(CommonAliasDecorator, frame_iter)

UserFilter()

# Allow users to specify regex used in stepping
class BacktraceStripRegex (gdb.Parameter):
    """Regex for function names to skip through in backtrace"""

    set_doc = "set this to consolidate library namespaces etc. in the backtrace"
    show_doc = "show this to see the currently skipped library namespaces etc."

    def __init__ (self):
        super (BacktraceStripRegex, self).__init__ ("backtrace-strip-regex",
                                                    gdb.COMMAND_STACK,
                                                    gdb.PARAM_STRING_NOESCAPE)
        self.value = '^(std::|__gnu)'   # default

    # required API
    def get_set_string(self):
        return self.value

    def get_show_string(self, svalue):
        return self.value

BacktraceStripRegex()

class BacktraceStripRegexes (gdb.Parameter):
    """Regexes for function names to skip through in backtrace

    Put each regex in its own capture group and the backtrace will skip
    only matches from the same capture group.

    Example: '(^std::)|(^boost::)' will group by std and boost namespaces separately.

    If you need to use subgroups within each group, try a "non-capturing"
    group (?:...) to avoid confusing which frames you want compressed.

    If multiple capture groups match, the first one is used.

    If present, this setting overrides backtrace-strip-regex
    """

    set_doc = "set this to consolidate frames by matching regex group"
    show_doc = "show this to see the current frame regex groups"

    def __init__ (self):
        super (BacktraceStripRegexes, self).__init__ ("backtrace-strip-regexes",
                                                      gdb.COMMAND_STACK,
                                                      gdb.PARAM_STRING_NOESCAPE)
        self.value = None   # default: no frame grouping

    # required API
    def get_set_string(self):
        return self.value

    def get_show_string(self, svalue):
        return self.value

BacktraceStripRegexes()
