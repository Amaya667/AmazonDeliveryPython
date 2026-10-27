"""
pairing_heap_node.py
---------------------------------------------------------------
One node of the Pairing Heap.

The heap is stored as a multi-way tree using the classic
"left-child / right-sibling" representation:
  - child   : the FIRST child of this node (its most recently linked child)
  - sibling : the next child of this node's parent

The heap-order rule is: a parent is never LESS urgent than its children
(urgency is decided by Package.compare_urgency()).
"""

from __future__ import annotations

from package import Package


class PairingHeapNode:
    def __init__(self, pkg: Package):
        """Creates a single node holding one package. Time: O(1)."""
        # The package stored in this node.
        self.pkg = pkg

        # First child (None if this node is a leaf).
        self.child = None

        # Next sibling in the parent's child list (None at the end).
        self.sibling = None
