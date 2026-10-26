def _java_div(a, b):
    """Integer division that truncates toward zero (exactly like Java's '/')."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q

class IntervalTreeNode:
    def __init__(self, start, end, package_id):
        """
        Creates a new leaf node for the slot [start, end).
        A new leaf has height 1 and its maxEnd equals its own end.
        Time: O(1).
        """
        # Slot start time (inclusive). This is the BST key.
        self.start = start

        # Slot end time (exclusive).
        self.end = end

        # Package currently occupying this slot.
        self.package_id = package_id

        # Augmentation: the largest 'end' value in the subtree rooted here.
        self.max_end = end

        # AVL height of the subtree rooted here (a leaf has height 1).
        self.height = 1

        # Left child (slots with smaller start).
        self.left = None

        # Right child (slots with larger start).
        self.right = None
