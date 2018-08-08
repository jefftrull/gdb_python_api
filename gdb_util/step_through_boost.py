import gdb
import re
class StepThroughBoost(gdb.Command):
    """Steps forward until we are not in a Boost library"""

    def __init__(self):
        super(StepThroughBoost, self).__init__("step-through-boost",
                                               gdb.COMMAND_RUNNING)

    def invoke(self, arg, from_tty):
        frame = gdb.selected_frame()
        while re.match('boost::', frame.name()):
            gdb.execute('step', to_string=True)
            frame = gdb.selected_frame()

StepThroughBoost()   # registers command
