"""
package.py
---------------------------------------------------------------
The record of ONE customer order.  OWNER: Member 4

A package knows its destination (a Graph vertex id), urgency class,
weight, delivery window [windowStart, windowEnd), service time and its
lifecycle status. Times are integer minutes from the start of the
planning day (for example 14:00 = 840).

The Pairing Heap ranks packages with compare_urgency():
     class (Critical first) -> deadline (earlier first) -> request time.
"""

from interval_tree_node import IntervalTreeNode


class Package:
    # ---- urgency classes (smaller number = more urgent) ----
    CRITICAL = 0
    SAME_DAY = 1
    EXPRESS = 2
    STANDARD = 3

    # ---- lifecycle status ----
    NEW = 0
    QUEUED = 1       # waiting in the heap
    ASSIGNED = 2     # holds a slot on a vehicle
    UNASSIGNED = 3   # no feasible vehicle yet, retried later
    CANCELLED = 4

    def __init__(self, package_id, warehouse_id, destination, priority,
                 weight, window_start, window_end, service_time, request_time):
        """Creates a new package in NEW status with no slot. Time: O(1)."""
        # Unique package id (also the Hash Table key).
        self.package_id = package_id

        # Warehouse the package comes from.
        self.warehouse_id = warehouse_id

        # Destination = vertex id in the Graph.
        self.destination = destination

        # One of CRITICAL, SAME_DAY, EXPRESS, STANDARD.
        self.priority = priority

        # Weight (kg), compared with the vehicle's remaining capacity.
        # (stored as float, like Java's double, so it prints as "5.0")
        self.weight = float(weight)

        # Promised delivery window [windowStart, windowEnd) in minutes.
        self.window_start = window_start
        self.window_end = window_end

        # Minutes needed at the customer's door.
        self.service_time = service_time

        # Time the order was requested (tie-breaker in the heap).
        self.request_time = request_time

        # Current lifecycle status.
        self.status = Package.NEW

        # Where the package is booked (-1 when it has no slot).
        self.vehicle_id = -1
        self.slot_start = -1
        self.slot_end = -1

    def copy(self):
        """Returns an independent copy of this record (same status and slot). Time: O(1)."""
        c = Package(self.package_id, self.warehouse_id, self.destination, self.priority,
                    self.weight, self.window_start, self.window_end,
                    self.service_time, self.request_time)
        c.status = self.status
        c.vehicle_id = self.vehicle_id
        c.slot_start = self.slot_start
        c.slot_end = self.slot_end
        return c

    def compare_urgency(self, other):
        """
        Urgency comparison used by the Pairing Heap.
        Returns a negative number if this package is MORE urgent than other,
        positive if LESS urgent, 0 if equal.
        Order: priority class, then deadline, then request time, then id.
        Time: O(1).
        """
        if self.priority != other.priority:
            return self.priority - other.priority
        if self.window_end != other.window_end:
            return self.window_end - other.window_end
        if self.request_time != other.request_time:
            return self.request_time - other.request_time
        return self.package_id - other.package_id

    @staticmethod
    def priority_name(priority):
        """Priority number as text. Time: O(1)."""
        if priority == Package.CRITICAL:
            return "Critical"
        if priority == Package.SAME_DAY:
            return "Same-day"
        if priority == Package.EXPRESS:
            return "Express"
        return "Standard"

    @staticmethod
    def status_name(status):
        """Status number as text. Time: O(1)."""
        if status == Package.NEW:
            return "NEW"
        if status == Package.QUEUED:
            return "QUEUED"
        if status == Package.ASSIGNED:
            return "ASSIGNED"
        if status == Package.UNASSIGNED:
            return "UNASSIGNED"
        return "CANCELLED"

    def __str__(self):
        """One-line description used by the GUI. Time: O(1)."""
        text = ("P" + str(self.package_id) + " | " + Package.priority_name(self.priority)
                + " | dest vertex " + str(self.destination)
                + " | " + str(self.weight) + " kg"
                + " | window [" + IntervalTreeNode.format_time(self.window_start) + ", "
                + IntervalTreeNode.format_time(self.window_end) + ")"
                + " | service " + str(self.service_time) + " min"
                + " | " + Package.status_name(self.status))
        if self.status == Package.ASSIGNED:
            text += (" -> V" + str(self.vehicle_id) + " ["
                     + IntervalTreeNode.format_time(self.slot_start) + ", "
                     + IntervalTreeNode.format_time(self.slot_end) + ")")
        return text
