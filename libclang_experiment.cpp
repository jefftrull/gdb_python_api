/*
 * Copyright (c) 2018 Jeff Trull
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:

 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include <iostream>
#include <vector>
#include <memory>

#include <clang-c/CXCompilationDatabase.h>
#include <clang-c/Index.h>

struct AutoDisposedString
{
    AutoDisposedString(CXString s) : s_(s) {}

    operator char const * () { return clang_getCString(s_); }

    ~AutoDisposedString() { clang_disposeString(s_); }

private:
    CXString s_;
};

int main() {
    CXCompilationDatabase_Error err;
    CXCompilationDatabase cdb = clang_CompilationDatabase_fromDirectory("/home/jet/oss/gdb_python_api/build", &err);
    if (err) {
        std::cerr << "failed to load compilation database\n";
        exit(1);
    }
    char const * ourfn = "/home/jet/oss/gdb_python_api/stl_with_lambda.cpp";
    CXCompileCommands cmds = clang_CompilationDatabase_getCompileCommands(cdb, ourfn);
    // fill out the array of char ptrs clang_parseTranslationUnit wants to see
    CXCompileCommand cmd = clang_CompileCommands_getCommand(cmds, 0);   // assuming there is only one
    std::vector<const char *> cmdstrs(clang_CompileCommand_getNumArgs(cmd));
    std::cerr << "args from compilation db:\n";
    for (auto i = 0; i < clang_CompileCommand_getNumArgs(cmd); ++i) {
        cmdstrs[i] = clang_getCString(clang_CompileCommand_getArg(cmd, i));
        std::cerr << cmdstrs[i] << "\n";
    }
    std::cerr << "=================\n";

    CXIndex index = clang_createIndex(0, 1);
    CXTranslationUnit tu;
    // somehow, supplying the original compile command arguments here causes downstream code to generate two compile "jobs"
    // with the same arguments
    // not sure why and it may be an issue later
    cmdstrs.clear();
    // this is required in the Python version but not here (!)
    // cmdstrs.push_back("-std=c++11");
    cmdstrs.push_back("-isystem/usr/lib/gcc/x86_64-linux-gnu/7/include");
    CXErrorCode errc = clang_parseTranslationUnit2(index, ourfn,
                                                   cmdstrs.data(),
                                                   cmdstrs.size(),
                                                   nullptr, 0,
                                                   CXTranslationUnit_None,
                                                   &tu);
    if (errc) {
        std::cerr << "parse failed\n";
        exit(errc);
    }

    auto diagCount = clang_getNumDiagnostics(tu);
    if (diagCount) {
        std::cerr << "parsing flagged " << diagCount << " diagnostics\n";
    }

    CXSourceLocation startloc = clang_getLocation(tu, clang_getFile(tu, ourfn), 26, 5);
    CXCursor cur = clang_getCursor(tu, startloc);
    // If we want to do the whole file
    // CXCursor cur = clang_getTranslationUnitCursor(tu);
    auto kindName = AutoDisposedString(clang_getCursorKindSpelling(cur.kind));
    std::cout << "top level cursor is of kind " << kindName << "\n";

    // visit its direct children
    clang_visitChildren(cur,
                        [](CXCursor cursor,
                           CXCursor parent,
                           CXClientData data) {
                            CXString fn;
                            unsigned line;
                            unsigned column;
                            CXSourceLocation loc = clang_getCursorLocation(cursor);
                            clang_getPresumedLocation(loc, &fn, &line, &column);
                            std::cout << "kind " << AutoDisposedString(clang_getCursorKindSpelling(cursor.kind));
                            std::cout << " @ (" << line << ", " << column << ") ";
                            std::cout << AutoDisposedString(clang_getCursorSpelling(cursor)) << "\n";

                            return CXChildVisit_Recurse;
                        },
                        nullptr);   // client_data

    // clean up resources
    clang_disposeTranslationUnit(tu);
    clang_disposeIndex(index);
    clang_CompileCommands_dispose(cmds);
    clang_CompilationDatabase_dispose(cdb);

}
