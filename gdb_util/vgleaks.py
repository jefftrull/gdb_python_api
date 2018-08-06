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

# single step until Valgrind reports a leak (sloooowwww)
class StepToLeak(gdb.Command):
    """Step until valgrind reports a leak"""

    def __init__ (self):
        super (StepToLeak, self).__init__ ("stepl", gdb.COMMAND_BREAKPOINTS)

    def invoke(self, arg, from_tty):
        gdb.execute('set logging redirect on', to_string = True)
        result = gdb.execute('mo leak full', False, True)
        while result.find('are definitely lost in loss record') is -1:
            try:
                gdb.execute('step', to_string = True)  # QUIETLY step
            except gdb.error:
                print('some error in step')  # BOZO handle
                break
            result = gdb.execute('mo leak full', False, True)
        gdb.execute('set logging redirect off', to_string = True)
        print('loss report:\n%s'%result)

StepToLeak()
