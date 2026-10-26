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
