class IntervalTreeNode:
    """
    Represents a single node in the augmented AVL Interval Tree.
    """
    def __init__(self, start, end, package_id):
        self.start = start            # Key for BST ordering (start time)
        self.end = end                # End time of the interval
        self.package_id = package_id  # Associated data / package identifier
        self.height = 1               # AVL tree height
        self.max_end = end            # Augmented field: max end time in subtree
        self.left = None              # Left child node
        self.right = None             # Right child node

from interval_tree_node import IntervalTreeNode

INT_MIN = -2147483648
INT_MAX = 2147483647


class IntervalTree:
    NEG_INF = INT_MIN

    def __init__(self):
        """Creates an empty tree. Time: O(1)."""
        self._root = None
        self._size = 0

        # Helper fields used by recursive routines
        self._deleted_flag = False
        self._cursor = 0
        self._gap_found = False
        self._gap_duration = 0

        self._report_buffer = None
        self._report_count = 0

    def _height(self, n):
        return 0 if n is None else n.height

    def _max_end(self, n):
        return IntervalTree.NEG_INF if n is None else n.max_end

    def _update(self, n):
        n.height = 1 + max(self._height(n.left), self._height(n.right))
        n.max_end = max(n.end, max(self._max_end(n.left), self._max_end(n.right)))

    def _balance_factor(self, n):
        return 0 if n is None else self._height(n.left) - self._height(n.right)

    def _rotate_right(self, y):
        x = y.left
        y.left = x.right
        x.right = y
        self._update(y)
        self._update(x)
        return x

    def _rotate_left(self, x):
        y = x.right
        x.right = y.left
        y.left = x
        self._update(x)
        self._update(y)
        return y

    def _rotate_left_right(self, n):
        n.left = self._rotate_left(n.left)
        return self._rotate_right(n)

    def _rotate_right_left(self, n):
        n.right = self._rotate_right(n.right)
        return self._rotate_left(n)

    def _rebalance(self, n):
        self._update(n)
        balance = self._balance_factor(n)

        if balance > 1:
            if self._balance_factor(n.left) >= 0:
                return self._rotate_right(n)
            return self._rotate_left_right(n)
        if balance < -1:
            if self._balance_factor(n.right) <= 0:
                return self._rotate_left(n)
            return self._rotate_right_left(n)
        return n
def insert(self, start, end, package_id):
        """
        Inserts a new slot [start, end) for the given package.
        Time: O(log n).
        """
        if start >= end:
            return False
        if self.find_node(start) is not None:
            return False
        self._root = self._insert_rec(self._root, start, end, package_id)
        self._size += 1
        return True

    def _insert_rec(self, node, start, end, package_id):
        if node is None:
            return IntervalTreeNode(start, end, package_id)
        if start < node.start:
            node.left = self._insert_rec(node.left, start, end, package_id)
        else:
            node.right = self._insert_rec(node.right, start, end, package_id)
        return self._rebalance(node)

    def delete(self, start):
        """
        Deletes the slot whose start time equals 'start'.
        Time: O(log n).
        """
        self._deleted_flag = False
        self._root = self._delete_rec(self._root, start)
        if self._deleted_flag:
            self._size -= 1
        return self._deleted_flag

    def _delete_rec(self, node, start):
        if node is None:
            return None
        if start < node.start:
            node.left = self._delete_rec(node.left, start)
        elif start > node.start:
            node.right = self._delete_rec(node.right, start)
        else:
            if not self._deleted_flag:
                self._deleted_flag = True
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left
            successor = self._min_node(node.right)
            node.start = successor.start
            node.end = successor.end
            node.package_id = successor.package_id
            node.right = self._delete_rec(node.right, successor.start)
        return self._rebalance(node)

    def _min_node(self, node):
        while node.left is not None:
            node = node.left
        return node
def find_node(self, start):
        """Finds the node whose start time equals 'start'. Time: O(log n)."""
        n = self._root
        while n is not None:
            if start < n.start:
                n = n.left
            elif start > n.start:
                n = n.right
            else:
                return n
        return None

    def search_overlap(self, q_start, q_end):
        """Returns ANY slot that overlaps the query [q_start, q_end), or None."""
        n = self._root
        while n is not None and not (n.start < q_end and q_start < n.end):
            if n.left is not None and n.left.max_end > q_start:
                n = n.left
            else:
                n = n.right
        return n

    def has_conflict(self, q_start, q_end):
        """True if [q_start, q_end) conflicts with any booked slot. Time: O(log n)."""
        return self.search_overlap(q_start, q_end) is not None

    def report_overlaps(self, q_start, q_end):
        """Returns every slot overlapping [q_start, q_end) in start-time order."""
        self._report_buffer = [None] * 8
        self._report_count = 0
        self._report_rec(self._root, q_start, q_end)

        result = [None] * self._report_count
        for i in range(self._report_count):
            result[i] = self._report_buffer[i]
        self._report_buffer = None
        return result

    def _report_rec(self, n, q_start, q_end):
        if n is None or n.max_end <= q_start:
            return
        self._report_rec(n.left, q_start, q_end)
        if n.start < q_end and q_start < n.end:
            self._add_to_buffer(n)
        if n.start < q_end:
            self._report_rec(n.right, q_start, q_end)

    def _add_to_buffer(self, n):
        if self._report_count == len(self._report_buffer):
            bigger = [None] * (len(self._report_buffer) * 2)
            for i in range(self._report_count):
                bigger[i] = self._report_buffer[i]
            self._report_buffer = bigger
        self._report_buffer[self._report_count] = n
        self._report_count += 1

    def stabbing_query(self, t):
        """Every delivery active at the single instant t. Time: O(log n + k)."""
        return self.report_overlaps(t, t + 1)

    def free_slot(self, duration, after):
        """Earliest time T >= 'after' for a gap of at least 'duration' minutes."""
        self._cursor = after
        self._gap_found = False
        self._gap_duration = duration
        self._free_slot_visit(self._root)
        return self._cursor

    def _free_slot_visit(self, n):
        if n is None or self._gap_found or n.max_end <= self._cursor:
            return
        self._free_slot_visit(n.left)
        if self._gap_found:
            return
        if n.start - self._cursor >= self._gap_duration:
            self._gap_found = True
            return
        self._cursor = max(self._cursor, n.end)
        self._free_slot_visit(n.right)

    def predecessor(self, t):
        """Slot with the largest start strictly before t. Time: O(log n)."""
        best = None
        n = self._root
        while n is not None:
            if n.start < t:
                best = n
                n = n.right
            else:
                n = n.left
        return best

    def successor(self, t):
        """Slot with the smallest start at or after t. Time: O(log n)."""
        best = None
        n = self._root
        while n is not None:
            if n.start >= t:
                best = n
                n = n.left
            else:
                n = n.right
        return best
