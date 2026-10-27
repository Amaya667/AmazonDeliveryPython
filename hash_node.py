"""
hash_node.py
---------------------------------------------------------------
One entry (key -> value) inside a bucket of the Hash Table.
OWNER: Member 2

Collisions are handled by CHAINING: all entries that land in the same
bucket are linked together through the 'next' pointer.
"""


class HashNode:
    def __init__(self, key, value):
        """Creates a new entry. Time: O(1)."""
        # Integer key (Package_ID or Vehicle_ID).
        self.key = key

        # Stored object (a Package, a Vehicle, or a [vehicleId, slotStart] slot key).
        self.value = value

        # Next entry in the same bucket (None at the end of the chain).
        self.next = None
