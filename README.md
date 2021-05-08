# gdb_python_api
Experiments with the GDB Python API

Usage: `PYTHONPATH=/path/to/gdb_python_api gdb ...`


## Note: libClang version 11.0 has a bug - don't use it

For detailed information see [this commit](https://github.com/llvm/llvm-project/commit/bbdbd020d2c2f315ed1545b23c23ec6ff1abc022), which fixed the problem and was released in 11.1. Please use that version instead.

## Backtrace Cleanup for C++ template libraries

Backtraces from heavily templated library code can be tough for users to understand. Through the use of the [frame filter](https://sourceware.org/gdb/onlinedocs/gdb/Frame-Filter-API.html#Frame-Filter-API) and [frame decorator](https://sourceware.org/gdb/onlinedocs/gdb/Frame-Decorator-API.html#Frame-Decorator-API) APIs we can filter out library internals and display more readable aliases for common types.

When the `backtrace` module is imported, future backtraces are controlled by the `backtrace-strip-regex` parameter. Any sequence of frames with matching function names will be trimmed to just the bottom (highest numbered) one. This has the effect of showing only the *call* into library code, and not the subsequent library internals.

In addition, the display of each frame is trimmed by using common type aliases. For example, `std::__cxx11::basic_string<char>` is replaced by `std::string`.

~~~
(gdb) python import gdb_util.backtrace
(gdb) b main
(gdb) run
(gdb) show backtrace-strip-regex
^(std::|__gnu)
step into some function
(gdb) backtrace
~~~

### Compressing Related Frames
`backtrace-strip-regex` combines all consecutive frames that match it. You can also separately combine groups using `backtrace-strip-regexes`:

~~~
(gdb) set backtrace-strip-regexes (^std::)|(^boost::)
~~~

Now a backtrace from the `std::` namespace followed immediately by frames from the `boost::` namespace will display the last frame from each. Parentheses are used to identify separate groups. If your regex requires subgroups, use a *non-capturing* group starting with `(?:`.

`backtrace-strip-regexes` overrides `backtrace-strip-regex`.

## Stepping only into user code

Another challenge with using template libraries is in stepping through code execution. Particularly in debug builds, such libraries may make a lot of calls that are hard to understand, before reaching any user code. Users can work around this by looking up line numbers and setting breakpoints, but that's tedious.

The `stepu` command steps only into *user* code, by skipping functions matching the `stepu-ignore-regex` parameter. It examines the AST at the current line using [libClang](https://clang.llvm.org/doxygen/group__CINDEX.html)'s Python API, and advances execution until a user function is hit.

The `finishu` command returns you to the point right after where `stepu` was executed, as though you had typed `next` instead.

Due to the use of libClang, an extra environment variable is required:

~~~
PYTHONPATH=/path/to/gdb_python_api LD_LIBRARY_PATH=/usr/lib/llvm-5.0/lib gdb ...
(gdb) python import gdb_util.stepping
(gdb) show stepu-ignore-regex
^(std::|__gnu)
(gdb) b main
(gdb) run
step to a std library function call
(gdb) stepu
~~~

You should now be in the first non-library function called (a plain function, lambda, or object method called by library code).

## Stack frame content display

The command `pframe` gives you a view of the contents of the current (x86) stack frame, showing arguments and local variables in their positions relative to the stack pointer and the beginning of the frame. You can use this to produce an updated display whenever the stack changes by "watching" the stack pointer:

~~~
(gdb) python import gdb_util.stackframe
(gdb) b main
(gdb) run
Breakpoint 1, main (argc=1, argv=0x7fffffffddf8) at...
(gdb) watch $rsp if $_regex($_as_string($rip), ".* <target_fn")
Watchpoint 2: $rsp
(gdb) commands 2
Type commands for breakpoint(s) 2, one per line.
End with a line saying just "end".
>pframe
>end
(gdb) continue
~~~

The stack pointer changes quite frequently so you will probably want to restrict it with a condition like I have above (to `target_fn` and its inlined children).

## Pointer Loop Finding

In combination with valgrind, the command `ppl` ("print pointer loops") gives you a view of any pointer loops between allocated blocks that might be causing memory leaks. To run:

- launch valgrind in gdbserver mode
- launch gdb as a client (follow directions printed by valgrind)
- import `gdb_util.vgleaks`
- when `monitor leak_check` shows you have a leak, run `ppl` and it will print out any circular references it found among the leaked blocks
- `set ppl-backtrace on` will give you backtraces for the point each block was allocated, as well
