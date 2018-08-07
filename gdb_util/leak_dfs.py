# Looking for reference loops via graph_tool
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

from graph_tool import Graph
from graph_tool.search import DFSVisitor, dfs_search

class PointerGraph(Graph):
    """wrapper for the graph of memory block pointers"""
    def __init__(self, start):
        super(PointerGraph, self).__init__()
        # the block base address (as a string) for each vertex
        self.vaddr_pmap = self.new_vertex_property('string')
        self.addr2v = {}
        self.root = self.create_ptr(start)

    # create just the vertex representing a particular pointer
    def create_ptr(self, addr):
        v = self.add_vertex()
        self.addr2v[addr] = v
        self.vaddr_pmap[v] = addr
        return v

    # create a new vertex for a pointer to an existing block
    # notice our edges go in the opposite "direction" of a pointer
    # edges are from pointee to point-er, or from the block being
    # referenced, to the block that is doing the referencing
    def create_ptr_edge(self, addr, u):
        v = self.create_ptr(addr)   # the referencer
        return self.add_edge(u, v)

class LoopFindVisitor(DFSVisitor):
    def __init__(self, g, pred, expand_vertex, backedge_action):
        super(LoopFindVisitor, self).__init__()
        self.g = g
        self.pred = pred
        self.expand_vertex = expand_vertex
        self.backedge_action = backedge_action

    def discover_vertex(self, u):
        # having arrived here for the first time, we need to add any out edges
        # add bogus additional vertex and edge
        self.expand_vertex(self.g, u)

    def tree_edge(self, e):
        # this is where we update the predecessor map
        self.pred[e.target()] = int(e.source())

    def back_edge(self, e):
        # the money method. This is where we detect loops
        
        # for now I'm only interested in loops that go back to the root
        if e.target() == self.g.root:
            self.backedge_action(self.g, e, self.pred)
