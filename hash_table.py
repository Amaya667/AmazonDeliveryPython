"""
hash_table.py
---------------------------------------------------------------
Hash Table with chaining. OWNER: Member 2

It holds the THREE indexes required by the abstract:
   index 0 : Package_ID -> Package record
   index 1 : Vehicle_ID -> Vehicle record
   index 2 : Package_ID -> slot key  (vehicle id + slot start time)

The slot key is stored as a 2-element list [vehicleId, startTime].
We store the KEY (not a tree-node pointer) because the interval tree's
delete copies data between nodes, so raw node pointers could go stale.

Hash function : (key * 31) mod capacity (made non-negative)
Collisions    : separate chaining (linked HashNodes)
Resizing      : capacity doubles when load factor passes 0.75

Insert / search / delete / update: O(1) average, O(n) worst case.

NOTE: this is the project's own hand-written table. Python's dict is NOT
used to store the data; buckets are plain fixed-size lists of HashNode chains.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hash_node import HashNode

if TYPE_CHECKING:  # type-only imports: avoids the Vehicle <-> HashTable import cycle
    from package import Package
    from vehicle import Vehicle


def _to_int32(value):
    """Wraps a Python int to Java's 32-bit signed int range."""
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value >= 0x80000000 else value


class HashTable:
    # Ids of the three internal indexes.
    _PACKAGES = 0
    _VEHICLES = 1
    _SLOTS = 2

    # Starting number of buckets for each index.
    _INITIAL_CAPACITY = 16

    def __init__(self):
        """Creates the three empty indexes. Time: O(1)."""
        # buckets[which] is the bucket array of one index.
        self._buckets = [None] * 3

        # counts[which] = number of entries stored in that index.
        self._counts = [0] * 3
        for i in range(3):
            self._buckets[i] = [None] * HashTable._INITIAL_CAPACITY
            self._counts[i] = 0

    # =====================================================================
    # Generic private operations (work on any of the three indexes)
    # =====================================================================

    def _hash(self, key, capacity):
        """Hash function: maps a key to a bucket number. Time: O(1)."""
        h = _to_int32(key * 31)
        if h < 0:
            h = _to_int32(-h)
            if h < 0:
                h = 0                  # Integer.MIN_VALUE edge case
        return h % capacity

    def _find_node(self, which, key):
        """Finds the entry with this key in index 'which' (None if absent)."""
        b = self._hash(key, len(self._buckets[which]))
        current = self._buckets[which][b]
        while current is not None:
            if current.key == key:
                return current
            current = current.next
        return None

    def _insert(self, which, key, value):
        """
        Inserts key -> value. Returns False (and changes nothing)
        if the key already exists. Time: O(1) average.
        """
        if self._find_node(which, key) is not None:
            return False
        if self._counts[which] + 1 > len(self._buckets[which]) * 3 // 4:
            self._resize(which)                    # keep the chains short
        b = self._hash(key, len(self._buckets[which]))
        node = HashNode(key, value)
        node.next = self._buckets[which][b]        # add at the front of the chain
        self._buckets[which][b] = node
        self._counts[which] += 1
        return True

    def _search(self, which, key):
        """Returns the value stored for key, or None. Time: O(1) average."""
        node = self._find_node(which, key)
        return None if node is None else node.value

    def _update(self, which, key, value):
        """
        Replaces the value of an EXISTING key.
        Returns False if the key is not present. Time: O(1) average.
        """
        node = self._find_node(which, key)
        if node is None:
            return False
        node.value = value
        return True

    def _delete(self, which, key):
        """Removes key. Returns False if it was not present. Time: O(1) average."""
        b = self._hash(key, len(self._buckets[which]))
        previous = None
        current = self._buckets[which][b]
        while current is not None:
            if current.key == key:
                if previous is None:
                    self._buckets[which][b] = current.next    # removing the chain head
                else:
                    previous.next = current.next
                self._counts[which] -= 1
                return True
            previous = current
            current = current.next
        return False

    def _resize(self, which):
        """Doubles the bucket array of one index and re-hashes every entry. Time: O(n)."""
        old = self._buckets[which]
        bigger = [None] * (len(old) * 2)
        for i in range(len(old)):
            current = old[i]
            while current is not None:
                nxt = current.next                  # remember before relinking
                b = self._hash(current.key, len(bigger))
                current.next = bigger[b]
                bigger[b] = current
                current = nxt
        self._buckets[which] = bigger

    def _sorted_entries(self, which):
        """
        Collects all entries of one index into a list, sorted by key
        (insertion sort) so the GUI shows a stable order. Time: O(n^2).
        """
        all_nodes = [None] * self._counts[which]
        n = 0
        for i in range(len(self._buckets[which])):
            current = self._buckets[which][i]
            while current is not None:
                all_nodes[n] = current
                n += 1
                current = current.next
        for i in range(1, len(all_nodes)):
            key = all_nodes[i]
            j = i - 1
            while j >= 0 and all_nodes[j].key > key.key:
                all_nodes[j + 1] = all_nodes[j]
                j -= 1
            all_nodes[j + 1] = key
        return all_nodes

    # =====================================================================
    # PACKAGE LOOKUP (Package_ID -> Package)
    # =====================================================================

    def insert_package(self, p: Package) -> bool:
        """Registers a package record. False if the id already exists. O(1) avg."""
        return self._insert(HashTable._PACKAGES, p.package_id, p)

    def search_package(self, package_id: int) -> Package | None:
        """Finds a package by id (None if unknown). O(1) avg."""
        return self._search(HashTable._PACKAGES, package_id)

    def update_package(self, p):
        """Replaces the stored record of an existing package. O(1) avg."""
        return self._update(HashTable._PACKAGES, p.package_id, p)

    def delete_package(self, package_id):
        """Removes a package record. O(1) avg."""
        return self._delete(HashTable._PACKAGES, package_id)

    def package_count(self):
        """Number of registered packages."""
        return self._counts[HashTable._PACKAGES]

    def get_all_packages(self):
        """All packages sorted by id. Time: O(n^2)."""
        entries = self._sorted_entries(HashTable._PACKAGES)
        result = [None] * len(entries)
        for i in range(len(entries)):
            result[i] = entries[i].value
        return result

    # =====================================================================
    # VEHICLE LOOKUP (Vehicle_ID -> Vehicle)
    # =====================================================================

    def insert_vehicle(self, v: Vehicle) -> bool:
        """Registers a vehicle record. False if the id already exists. O(1) avg."""
        return self._insert(HashTable._VEHICLES, v.vehicle_id, v)

    def search_vehicle(self, vehicle_id: int) -> Vehicle | None:
        """Finds a vehicle by id (None if unknown). O(1) avg."""
        return self._search(HashTable._VEHICLES, vehicle_id)

    def update_vehicle(self, v):
        """Replaces the stored record of an existing vehicle. O(1) avg."""
        return self._update(HashTable._VEHICLES, v.vehicle_id, v)

    def delete_vehicle(self, vehicle_id):
        """Removes a vehicle record. O(1) avg."""
        return self._delete(HashTable._VEHICLES, vehicle_id)

    def vehicle_count(self):
        """Number of registered vehicles."""
        return self._counts[HashTable._VEHICLES]

    def get_all_vehicles(self):
        """All vehicles sorted by id. Time: O(n^2)."""
        entries = self._sorted_entries(HashTable._VEHICLES)
        result = [None] * len(entries)
        for i in range(len(entries)):
            result[i] = entries[i].value
        return result

    # =====================================================================
    # PACKAGE-TO-SLOT MAPPING (Package_ID -> [vehicleId, slotStart])
    # =====================================================================

    def put_slot(self, package_id, vehicle_id, slot_start):
        """
        Records where a package is booked: which vehicle and which slot start time.
        If the package already has a mapping it is overwritten. O(1) avg.
        """
        slot_key = [vehicle_id, slot_start]
        if not self._update(HashTable._SLOTS, package_id, slot_key):
            self._insert(HashTable._SLOTS, package_id, slot_key)

    def get_slot(self, package_id):
        """
        Returns the slot key [vehicleId, slotStart] of a package,
        or None if the package has no booked slot. O(1) avg.
        """
        return self._search(HashTable._SLOTS, package_id)

    def remove_slot(self, package_id):
        """Removes the slot mapping of a package (after cancel / re-queue). O(1) avg."""
        return self._delete(HashTable._SLOTS, package_id)

    def slot_count(self):
        """Number of packages that currently hold a slot."""
        return self._counts[HashTable._SLOTS]

    # =====================================================================
    # CLEAR
    # =====================================================================

    def clear(self):
        """Empties all three indexes. Time: O(1)."""
        for i in range(3):
            self._buckets[i] = [None] * HashTable._INITIAL_CAPACITY
            self._counts[i] = 0
