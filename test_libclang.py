#!/usr/bin/python
# to run this from gdb:
# python
# > import sys
# > sys.argv=['../test_libclang.py', '/home/jet/oss/gdb_python_api/stl_with_lambda.cpp', './compile_commands.json']
# > exec(open('../test_libclang.py').read())

# this code was inspired/copied from a lot of places but most notably
# https://stackoverflow.com/questions/36652540/how-to-use-compile-commands-json-with-clang-python-bindings
# and then I hacked it.

from clang import cindex
from argparse import ArgumentParser, FileType
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
    cmds = compdb.getCompileCommands(source_file_path)

except cindex.CompilationDatabaseError:
    print ('Could not load compilation flags for', source_file_path)

# assuming only one command is required to build
cmd = cmds.__getitem__(0)

# filter irrelevant command line components
args = []
arg_gen = cmd.arguments
next(arg_gen)            # remove compiler executable path
for arg in arg_gen:
    if arg == '-c':
        # if we don't drop the -c input filename we get a TU parse error...
        next(arg_gen)    # drop input filename
    elif arg == '-o':
        next(arg_gen)    # drop output filename
    else:
        args.append(arg)

translation_unit = index.parse(source_file_path, args)

if (len(translation_unit.diagnostics) > 0):
    print(['%s:%s'%(x.category_name, x.spelling) for x in translation_unit.diagnostics])

# Step 3: print AST starting at our target

# we can go from TU's primary cursor to a specific file location with:
cur = cindex.Cursor.from_location(translation_unit,
                                  cindex.SourceLocation.from_position(translation_unit,
                                                                      translation_unit.get_file(source_file_path),
                                                                      26, 1))  # hardcoded to my point of interest
AST_from_node(cur)
