"""
pairing_heap.py
---------------------------------------------------------------
Min-heap (most urgent package on top) implemented as a Pairing Heap.

Ordering : Package.compare_urgency()
           (class -> deadline -> request time -> id)

Costs    : insert O(1), peek O(1), meld O(1),
           extract_min O(log n) amortized.

extract_min uses the standard TWO-PASS pairing:
  pass 1: link the children in pairs from left to right,
  pass 2: link the resulting trees from right to left.
Both passes are iterative (no recursion), so a very large heap can
never cause a stack overflow. No built-in heap / container is used
(no heapq, no deque).
"""

from package import Package
from pairing_heap_node import PairingHeapNode
from interval_tree_node import IntervalTreeNode


class PairingHeap:
    def __init__(self):
        """Creates an empty heap. Time: O(1)."""
        # Root of the heap = most urgent package (None when empty).
        self._root = None

        # Number of packages stored.
        self._size = 0

    # =====================================================================
    # Basic queries
    # =====================================================================

    def is_empty(self):
        """True when the heap holds no package. Time: O(1)."""
        return self._root is None

    def size(self):
        """Number of packages in the heap. Time: O(1)."""
        return self._size

    def peek(self):
        """Returns the most urgent package WITHOUT removing it (None if empty). O(1)."""
        return None if self._root is None else self._root.pkg

    # =====================================================================
    # Core operations
    # =====================================================================

    def insert(self, p):
        """Adds a package to the heap. Time: O(1)."""
        if p is None:
            return
        node = PairingHeapNode(p)
        self._root = node if self._root is None else self._link(self._root, node)
        self._size += 1

    def meld(self, other):
        """
        Merges ALL packages of 'other' into this heap in O(1).
        After the call 'other' is empty (its nodes now belong to this heap).
        """
        if other is None or other is self or other._root is None:
            return
        self._root = other._root if self._root is None else self._link(self._root, other._root)
        self._size += other._size
        other._root = None
        other._size = 0

    def extract_min(self):
        """
        Removes and returns the most urgent package (None if the heap is empty).
        Time: O(log n) amortized.
        """
        if self._root is None:
            return None
        top = self._root.pkg
        first = self._root.child
        self._root.child = None
        self._size -= 1

        # ---- Pass 1: link children in pairs, left to right ----
        # The merged pairs are collected in a list that ends up in REVERSE
        # order (last pair first), which is exactly what pass 2 needs.
        reversed_list = None
        while first is not None:
            a = first
            b = a.sibling
            rest = None if b is None else b.sibling
            a.sibling = None
            if b is None:
                merged = a
            else:
                b.sibling = None
                merged = self._link(a, b)
            merged.sibling = reversed_list
            reversed_list = merged
            first = rest

        # ---- Pass 2: link the pair-trees, right to left ----
        result = None
        while reversed_list is not None:
            nxt = reversed_list.sibling
            reversed_list.sibling = None
            result = reversed_list if result is None else self._link(result, reversed_list)
            reversed_list = nxt
        self._root = result
        return top

    def _link(self, a, b):
        """
        Links two heap-ordered trees: the more urgent root becomes the parent,
        the other root becomes its first child. Both roots must have
        sibling == None. Returns the new root. Time: O(1).
        """
        if b.pkg.compare_urgency(a.pkg) < 0:      # b is more urgent: swap roles
            t = a
            a = b
            b = t
        b.sibling = a.child
        a.child = b
        return a

    def clear(self):
        """Removes every package. Time: O(1)."""
        self._root = None
        self._size = 0

    # =====================================================================
    # Snapshot and display
    # =====================================================================

    def to_array(self):
        """
        Returns all packages as a list in UNSPECIFIED order (a snapshot;
        the heap itself is not changed). Time: O(n).
        """
        result = [None] * self._size
        if self._root is None:
            return result
        stack = [None] * (self._size + 1)
        top = 0
        n = 0
        stack[top] = self._root
        top += 1
        while top > 0:
            top -= 1
            node = stack[top]
            result[n] = node.pkg
            n += 1
            if node.sibling is not None:
                stack[top] = node.sibling
                top += 1
            if node.child is not None:
                stack[top] = node.child
                top += 1
        return result

    def display(self):
        """
        Builds an indented text picture of the heap (root first, children
        indented below their parent) for the GUI. Time: O(n).
        """
        sb = []
        sb.append("Pairing Heap (waiting packages): size = " + str(self._size) + "\n")
        if self._root is None:
            sb.append("   (empty)\n")
            return "".join(sb)
        top = self._root.pkg
        sb.append("   most urgent: P" + str(top.package_id) + "\n")

        node_stack = [None] * (self._size + 1)
        depth_stack = [0] * (self._size + 1)
        sp = 0
        node_stack[sp] = self._root
        depth_stack[sp] = 0
        sp += 1
        while sp > 0:
            sp -= 1
            node = node_stack[sp]
            depth = depth_stack[sp]

            sb.append("   ")
            for _ in range(depth):
                sb.append("    ")
            sb.append("* " if depth == 0 else "+- ")
            sb.append(self._describe(node.pkg) + "\n")

            if node.sibling is not None:          # same depth, visited after the child subtree
                node_stack[sp] = node.sibling
                depth_stack[sp] = depth
                sp += 1
            if node.child is not None:
                node_stack[sp] = node.child
                depth_stack[sp] = depth + 1
                sp += 1
        return "".join(sb)

    def _describe(self, p):
        """Short one-line description of a package inside the heap picture."""
        return ("P" + str(p.package_id) + " [" + Package.priority_name(p.priority) + "]"
                + " deadline " + IntervalTreeNode.format_time(p.window_end)
                + " requested " + IntervalTreeNode.format_time(p.request_time)
                + " (" + Package.status_name(p.status) + ")")
