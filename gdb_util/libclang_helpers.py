# Some utility functions for working with libclang
# Copyright (c) 2018 Jeff Trull

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from clang import cindex
from os import path

# CompilationDatabase.getCompileCommands() will try to "infer" build commands
# for files that are not present in the compilation database - including headers,
# surprisingly. See https://bugs.llvm.org/show_bug.cgi?id=50249
# We don't want this, so here's our alternative implementation:

def _getCompileCommands(compdb, fname):
    """Return a list of commands to build fname. If fname is not found in compdb, return None"""

    all_cmds = compdb.getAllCompileCommands()
    cmds = [cmd for cmd in all_cmds if cmd.filename == path.abspath(fname)]
    return cmds if len(cmds) > 0 else None


def getASTNode(fname, line, column, tu_fname = None, compdb_fname = './compile_commands.json'):
    """Find the enclosing AST node of a given location

    Keyword arguments:
    fname        -- the file containing the desired node
    line         -- the line of the node
    column       -- the column of the node
    tu_fname     -- the source file containing the compiled translation unit, if different (i.e. if fname was included)
    compdb_fname -- the file containing the compilation database
    """

    compilation_database_path = path.dirname(compdb_fname)
    index = cindex.Index.create()

    # Step 1: load the compilation database
    try:
        compdb = cindex.CompilationDatabase.fromDirectory(compilation_database_path)
    except cindex.CompilationDatabaseError:
        raise RuntimeError('Could not load compilation database for %s'%compilation_database_path)

    # Step 2: query compilation flags
    if tu_fname is None:        # indicates file is the translation unit
        tu_fname = fname
    cmds = _getCompileCommands(compdb, tu_fname)

    # getCompileCommands signals "not found" with None result
    if cmds is None:
        raise RuntimeError('No compilation flags found for %s'%tu_fname)

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


    try:
        translation_unit = index.parse(tu_fname, args)

        # TODO: this would be an excellent place to cache the parse results
        # compilation could take a noticeable amount of time

        if (len(translation_unit.diagnostics) > 0):
            print(['%s:%s'%(x.category_name, x.spelling) for x in translation_unit.diagnostics])
            raise RuntimeError('Failure during libclang parsing')

        # we can go from TU's primary cursor to a specific file location with:
        loc = cindex.SourceLocation.from_position(translation_unit,
                                                  translation_unit.get_file(fname),
                                                  line, column)
        cur = cindex.Cursor.from_location(translation_unit, loc)

        return cur

    except cindex.TranslationUnitLoadError as e:
        print('TranslationUnitLoadError while parsing %s with args:' % tu_fname)
        print(args)
        raise


# supply the next sibling of a statement (for e.g. implementing "next")
def getASTSibling(parent, node):
    """Return the next sibling of a node in the AST, if present"""

    if not parent or parent.kind is not cindex.CursorKind.COMPOUND_STMT:
        # don't know what to do here
        raise RuntimeError('AST node on line %d is not a child of a compound statement - cannot determine next statement'%node.location.line)
    sibling = None
    child_it = parent.get_children()
    for child in child_it:
        if child == node:
            try:
                sibling = next(child_it)
            except StopIteration:
                pass   # just means there is no next sibling
            break
    return sibling

def getFuncName(node):
    """Return the namespace-qualified name of the function in a CALL_EXPR"""

    nm = node.spelling
    node = node.referenced   # jump to function definition
    while node and node.semantic_parent and node.semantic_parent.kind is not cindex.CursorKind.TRANSLATION_UNIT and node.semantic_parent.spelling:
        # accumulate namespaces ("semantic parents" of definition, until TU reached)
        nm = '%s::%s'%(node.semantic_parent.spelling, nm)
        node = node.semantic_parent
    return nm

def findFirstTU(files, compdb_fname='./compile_commands.json'):
    """Return the first file found within the compilation database"""

    compilation_database_path = path.dirname(compdb_fname)

    try:
        compdb = cindex.CompilationDatabase.fromDirectory(compilation_database_path)
    except cindex.CompilationDatabaseError:
        raise RuntimeError('Could not load compilation database for %s'%compilation_database_path)

    for fn in files:
        cmds = _getCompileCommands(compdb, fn)
        if cmds is not None:
            return fn
    return None
