cmake_minimum_required( VERSION 3.9 )

PROJECT( gdb_python_api )

# for relax debug, try:
set( CMAKE_CXX_FLAGS_DEBUG "-g -Og -fno-omit-frame-pointer" )

if( NOT CMAKE_BUILD_TYPE )
  # for the purposes of gdb integration this is the right choice
  set( CMAKE_BUILD_TYPE Debug )
endif()

set( CMAKE_CXX_STANDARD 14 )

add_executable( ll lotsa_locals.cpp )
