cmake_minimum_required( VERSION 3.9 )

PROJECT( gdb_python_api )

# always use -fno-omit-frame-pointer because we can't work otherwise ATM
add_compile_options( "-fno-omit-frame-pointer" )

# for relaxing debug, make it:
set( CMAKE_CXX_FLAGS_DEBUG "-g -Og" )

if( NOT CMAKE_BUILD_TYPE )
  # for the purposes of gdb integration this is the right choice
  set( CMAKE_BUILD_TYPE Debug )
endif()

add_executable( ll lotsa_locals.cpp )
