cmake_minimum_required( VERSION 3.9 )

PROJECT( gdb_python_api )

set( CMAKE_CXX_STANDARD 17 )

# Create a compilation database (compile_commands.json) for the use of Clang tools
set( CMAKE_EXPORT_COMPILE_COMMANDS ON )

# always use -fno-omit-frame-pointer because stack printing won't work otherwise ATM
add_compile_options( "-fno-omit-frame-pointer" )

set( CMAKE_CXX_FLAGS "-Wall -Wextra -Werror" )

# for relaxing debug, make it:
set( CMAKE_CXX_FLAGS_DEBUG "-g -Og" )

if( NOT CMAKE_BUILD_TYPE )
  # for the purposes of gdb integration this is the right choice
  set( CMAKE_BUILD_TYPE Debug )
endif()

# if using Clang, also use libc++
if (CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
  add_definitions(-stdlib=libc++)
  set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -stdlib=libc++")
endif()

#
# Code we will be operating on
#

# stack dump demonstration code
add_executable( ll examples/lotsa_locals.cpp )

# navigation in templated code demo
add_executable( swl examples/stl_with_lambda.cpp )
target_compile_options( swl PRIVATE -std=c++17 )

# code with a leak
add_executable( leak examples/leaker2.cpp )

# using std::sort
add_executable( srs examples/sort_random_sequence.cpp )

#
# libClang stuff
#

# libClang via the C API
add_executable( le libclang_test.cpp )

find_package( Boost 1.65 REQUIRED )

# libClang via Python
# In Ubuntu python-clang package is only in Python 2.7 search paths, while gdb uses Python 3
# You can get it in python3 as well by:
# sudo apt-get install python3-pip
# sudo pip3 install clang

if( LLVM_ROOT )
  # using a custom build of LLVM. We need to do two things:
  # 1) pick up the appropriate libclang.so
  set( CLANG_LIB_DIR ${LLVM_ROOT}/build/lib )
  target_link_libraries( le PUBLIC ${CLANG_LIB_DIR}/libclang.so )
  target_include_directories( le PUBLIC ${LLVM_ROOT}/tools/clang/include )
  # 2) ensure analysis is done with the path to stddef.h (compiler-supplied) added
  target_compile_definitions( le PUBLIC "-DLLVM_ROOT=${LLVM_ROOT}" )
else()
  # Look for an installed version
  # Works for Ubuntu, others...?
  find_file( INDEX_PATH "clang-c/Index.h"
    HINTS /usr/lib/llvm-5.0/include /usr/lib/llvm-4.0/include /usr/lib/llvm-3.8/include )
  if( NOT INDEX_PATH )
    message( FATAL_ERROR "cannot find libClang headers" )
  endif()
  get_filename_component( CLANG_INCLUDE_DIR ${INDEX_PATH} DIRECTORY )        # remove "Index.h"
  get_filename_component( CLANG_INCLUDE_DIR ${CLANG_INCLUDE_DIR} DIRECTORY ) # remove "clang-c"
  target_include_directories( le PUBLIC ${CLANG_INCLUDE_DIR} )
  get_filename_component( LLVM_BASE_DIR ${CLANG_INCLUDE_DIR} DIRECTORY )     # remove "include"

  set( CLANG_LIB_DIR ${LLVM_BASE_DIR}/lib )
  target_link_libraries( le PUBLIC ${CLANG_LIB_DIR}/libclang.so )
endif()

target_link_libraries( le PRIVATE Boost::boost -lstdc++fs )

# some "tests" that just exercise the libClang users enough to show they are working
# (and to provide usage examples)

enable_testing()

add_test( NAME libclang_via_python
  COMMAND ../libclang_test.py ${CMAKE_CURRENT_SOURCE_DIR}/stl_with_lambda.cpp ./compile_commands.json )
add_test( NAME libclang_via_c
  COMMAND ./le ${CMAKE_CURRENT_SOURCE_DIR}/stl_with_lambda.cpp ./compile_commands.json )

# Python scripts aren't linked against dynamic libraries so we specify them this way:
set_tests_properties( libclang_via_python PROPERTIES
  ENVIRONMENT "LD_LIBRARY_PATH=${CLANG_LIB_DIR}" )
