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
#include <filesystem>

#include <boost/preprocessor/stringize.hpp>

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

// stateful visitor for displaying hierarchy
struct PrintingVisitor {
    PrintingVisitor(unsigned depth = 0) : depth_(depth) {}

    static CXChildVisitResult
    visit(CXCursor cursor,
          CXCursor /* parent */,
          CXClientData data) {
        // rebind "this" from c-style client data
        auto visitor = reinterpret_cast<PrintingVisitor*>(data);
        visitor->print(cursor);

        PrintingVisitor child_vis(visitor->depth_+1);
        clang_visitChildren(cursor,
                            &PrintingVisitor::visit,
                            &child_vis);
        return CXChildVisit_Continue;
    }

    void print(CXCursor cursor) {
        // get location in file
        CXString fn;
        unsigned line;
        unsigned column;
        CXSourceLocation loc = clang_getCursorLocation(cursor);
        clang_getPresumedLocation(loc, &fn, &line, &column);
        std::cout << std::string(depth_, '-') << ' ';
        std::cout << "CursorKind." << AutoDisposedString(clang_getCursorKindSpelling(cursor.kind));
        std::cout << ':' << AutoDisposedString(clang_getCursorSpelling(cursor));
        std::cout << "@(" << line << "," << column << ")\n";
    }

private:

    unsigned depth_;
};

int main() {
    namespace fs = std::filesystem;

    CXCompilationDatabase_Error err;
    CXCompilationDatabase cdb = clang_CompilationDatabase_fromDirectory(".", &err);
    if (err) {
        std::cerr << "failed to load compilation database\n";
        exit(1);
    }
    // get absolute path to source file
    auto ourpath = fs::path("../examples/stl_with_lambda.cpp");
    auto abspath = fs::absolute(ourpath);
    std::string ourfn = abspath.string();
    CXCompileCommands cmds = clang_CompilationDatabase_getCompileCommands(cdb, ourfn.c_str());
    // fill out the array of char ptrs clang_parseTranslationUnit wants to see
    CXCompileCommand cmd = clang_CompileCommands_getCommand(cmds, 0);   // assuming there is only one
    std::vector<const char *> cmdstrs;

#ifdef LLVM_ROOT
    // add include path to the (compiler-defined) headers like stddef.h
    cmdstrs.push_back( "-isystem" BOOST_PP_STRINGIZE(LLVM_ROOT) "/tools/clang/lib/Headers" );
#endif

    for (unsigned cmdno = 1; cmdno < clang_CompileCommand_getNumArgs(cmd); ++cmdno) {
        std::cerr << clang_getCString(clang_CompileCommand_getArg(cmd, cmdno)) << ", ";
        if (std::string(clang_getCString(clang_CompileCommand_getArg(cmd, cmdno))) == "-c") {
            // skip input filename
            ++cmdno;
        } else if (std::string(clang_getCString(clang_CompileCommand_getArg(cmd, cmdno))) == "-o") {
            // skip output filename
            ++cmdno;
        } else {
            cmdstrs.push_back(clang_getCString(clang_CompileCommand_getArg(cmd, cmdno)));
        }
    }
    std::cerr << "\n";

    CXIndex index = clang_createIndex(0, 1);
    CXTranslationUnit tu;
    CXErrorCode errc = clang_parseTranslationUnit2(index, ourfn.c_str(),
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
        exit(1);
    }

    CXSourceLocation startloc = clang_getLocation(tu, clang_getFile(tu, ourfn.c_str()), 26, 1);
    CXCursor cur = clang_getCursor(tu, startloc);
    // If we want to do the whole file
    // CXCursor cur = clang_getTranslationUnitCursor(tu);

    // print hierarchy from this point
    PrintingVisitor().print(cur);
    PrintingVisitor vis(1);
    clang_visitChildren(cur,
                        &PrintingVisitor::visit,
                        &vis);

    // clean up resources
    clang_disposeTranslationUnit(tu);
    clang_disposeIndex(index);
    clang_CompileCommands_dispose(cmds);
    clang_CompilationDatabase_dispose(cdb);

}
