cmake_minimum_required( VERSION 3.9 )

PROJECT( gdb_python_api )

set( CMAKE_CXX_STANDARD 14 )

# Find LLVM (for libClang's C API, not the Python bindings)
# Create a compilation database (compile_commands.json) for the use of Clang tools
set( CMAKE_EXPORT_COMPILE_COMMANDS ON )

# always use -fno-omit-frame-pointer because stack printing won't work otherwise ATM
add_compile_options( "-fno-omit-frame-pointer" )

# for relaxing debug, make it:
set( CMAKE_CXX_FLAGS_DEBUG "-g -Og" )

if( NOT CMAKE_BUILD_TYPE )
  # for the purposes of gdb integration this is the right choice
  set( CMAKE_BUILD_TYPE Debug )
endif()

# stack dump demonstration code
add_executable( ll lotsa_locals.cpp )

# navigation in templated code demo
add_executable( swl stl_with_lambda.cpp )

# experimenting directly with the C API
add_executable( le libclang_experiment.cpp )
target_link_libraries( le PUBLIC ${LLVM_ROOT}/lib/libclang.so )
target_include_directories( le PUBLIC ${LLVM_ROOT}/include )
