# gdb_python_api
Experiments with the GDB Python API:

## Stack frame content display

This feature gives you a view of the contents of the current stack frame, showing arguments and local variables in their positions relative to the stack pointer and the beginning of the frame. You can use this to produce an updated display whenever the stack changes by "watching" the stack pointer:

~~~
(gdb) source ../gdb_util.py
(gdb) b main
(gdb) run
Breakpoint 1, main (argc=1, argv=0x7fffffffddf8) at...
(gdb) watch $rsp if $_regex($_as_string($rip), ".* <target_fn")
Watchpoint 2: $rsp
(gdb) continue
~~~

The stack pointer changes quite frequently so you will probably want to restrict it with a condition like I have above (to `target_fn` and its inlined children).
