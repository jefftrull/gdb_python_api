#!/usr/bin/python
# to run this from gdb:
# python
# > import sys
# > sys.argv=['../test_libclang.py', '/home/jet/oss/gdb_python_api/stl_with_lambda.cpp', './compile_commands.json']
# > exec(open('../test_libclang.py').read())

# this code was inspired/copied from a lot of places but most notably
# https://stackoverflow.com/questions/36652540/how-to-use-compile-commands-json-with-clang-python-bindings
# and then I hacked it.

from argparse import ArgumentParser, FileType
from libclang_helpers import getASTNode

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

cur = getASTNode(args.source_file.name, 26, 1)

# print AST starting at our target

AST_from_node(cur)
