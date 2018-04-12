#!/usr/bin/python2
# python-clang package is only in Python 2.7 search paths...
# gdb supports both IIRC

# this code was inspired/copied from a lot of places but most notably
# https://stackoverflow.com/questions/36652540/how-to-use-compile-commands-json-with-clang-python-bindings
# and then I hacked it.

from argparse import ArgumentParser, FileType
from clang import cindex
from os import path

def AST_from_node(node, lvl=0):
    # DFS with hierarchy display
    print('-' * lvl + ' %s:%s@(%d,%d)'%(node.kind, node.spelling, node.location.line, node.location.column))
    for n in node.get_children():
        AST_from_node(n, lvl+1)

arg_parser = ArgumentParser()
arg_parser.add_argument('source_file', type=FileType('r+'),
                        help='C++ source file to parse.')
arg_parser.add_argument('compilation_database', type=FileType('r+'),
                        help='The compile_commands.json to use to parse the source file.')
args = arg_parser.parse_args()

compilation_database_path = path.dirname(args.compilation_database.name)
source_file_path = args.source_file.name
index = cindex.Index.create()

# Step 1: load the compilation database
compdb = cindex.CompilationDatabase.fromDirectory(compilation_database_path)

# Step 2: query compilation flags
try:
    file_args = compdb.getCompileCommands(source_file_path)

except cindex.CompilationDatabaseError:
    print ('Could not load compilation flags for', source_file_path)

# print out loaded flags

# For some reason clang on Ubuntu 17.04 cannot find stddef.h when using libstdc++
# This workaround was plucked from gcc's default include paths:
file_args = ['-isystem/usr/lib/gcc/x86_64-linux-gnu/7/include',
             '-std=c++11']     # support lambdas
translation_unit = index.parse(source_file_path, file_args)
if (len(translation_unit.diagnostics) > 0):
    print(['%s:%s'%(x.category_name, x.spelling) for x in translation_unit.diagnostics])
# we can go from TU's primary cursor to a specific file location with:
cur = cindex.Cursor.from_location(translation_unit,
                                  cindex.SourceLocation.from_position(translation_unit,
                                                                      translation_unit.get_file(source_file_path),
                                                                      26, 5))
AST_from_node(cur)


# ACTION PLAN
# Deal with options properly
# produce identical output from both Python and C++ versions
