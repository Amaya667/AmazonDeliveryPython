"""
vehicle.py
---------------------------------------------------------------
One delivery vehicle.  OWNER: Member 4

A vehicle has a shift [shiftStart, shiftEnd), a capacity, a home
location (Graph vertex id) and ONE IntervalTree holding its booked slots.
This class wraps the tree with the placement logic of the abstract
(Section 4.4):  find_free_slot, is_placement_valid, assign, release.

Travel rule: between two consecutive stops the vehicle needs the Graph's
travel time, so   next.start >= previous.end + travelTime(prev, next).
For the first stop the "previous stop" is the vehicle's home location,
available from shiftStart.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graph import Graph
from interval_tree import IntervalTree
from interval_tree_node import IntervalTreeNode
from package import Package

if TYPE_CHECKING:  # type-only import: avoids the Vehicle <-> HashTable import cycle
    from hash_table import HashTable


class Vehicle:
    def __init__(self, vehicle_id, location, capacity, shift_start, shift_end, vehicle_type):
        """Creates a vehicle with an empty schedule. Time: O(1)."""
        # Unique vehicle id (Hash Table key).
        self.vehicle_id = vehicle_id

        # Home vertex in the Graph (where the vehicle starts its shift).
        self.location = location

        # Total load capacity (kg) and load already booked.
        self.capacity = float(capacity)
        self.used_load = 0.0

        # Working shift [shiftStart, shiftEnd) in minutes.
        self.shift_start = shift_start
        self.shift_end = shift_end

        # "Van", "Truck", ... (display only).
        self.type = vehicle_type

        # This vehicle's booked slots (Augmented AVL Interval Tree).
        self._schedule = IntervalTree()

    def get_schedule(self):
        """The vehicle's interval tree (used by the GUI for overlap searches)."""
        return self._schedule

    def remaining_capacity(self):
        """Capacity still free. Time: O(1)."""
        return self.capacity - self.used_load

    # =====================================================================
    # Step 1 of the policy: capacity and shift filter
    # =====================================================================

    def can_serve(self, p):
        """
        True if the vehicle has enough capacity AND its shift overlaps the
        package's delivery window. Time: O(1).
        """
        if self.remaining_capacity() < p.weight:
            return False
        return self.shift_start < p.window_end and p.window_start < self.shift_end

    # =====================================================================
    # Travel-time helpers
    # =====================================================================

    def _location_of(self, node, index: HashTable):
        """Location (vertex id) of the package booked in a tree node."""
        booked = index.search_package(node.package_id)
        return self.location if booked is None else booked.destination

    def _travel_in(self, pred, p, graph, index):
        """Travel time from the previous stop (or home) to the package's destination."""
        from_vertex = self.location if pred is None else self._location_of(pred, index)
        return graph.travel_time(from_vertex, p.destination)

    def _travel_out(self, nxt, p, graph, index):
        """Travel time from the package's destination to the next booked stop (0 if none)."""
        if nxt is None:
            return 0
        return graph.travel_time(p.destination, self._location_of(nxt, index))

    # =====================================================================
    # Step 4 of the policy: exact verification
    # =====================================================================

    def is_placement_valid(self, p: Package, start: int, graph: Graph, index: HashTable) -> bool:
        """
        Exact check that package p can start at 'start' on this vehicle:
          - slot [start, start+service) lies inside the window AND the shift
          - no overlap with any booked slot (tree overlap search)
          - the vehicle can drive from the previous stop in time
          - the vehicle can reach the next stop in time afterwards
        Time: O(log n) tree queries + Graph lookups.
        """
        if p.service_time <= 0:
            return False
        end = start + p.service_time
        if start < max(p.window_start, self.shift_start):
            return False
        if end > min(p.window_end, self.shift_end):
            return False
        if self._schedule.has_conflict(start, end):
            return False
        pred = self._schedule.predecessor(start)
        nxt = self._schedule.successor(start)

        tin = self._travel_in(pred, p, graph, index)
        if tin >= Graph.INFINITY:
            return False
        previous_end = self.shift_start if pred is None else pred.end
        if start < previous_end + tin:
            return False
        tout = self._travel_out(nxt, p, graph, index)
        if tout >= Graph.INFINITY:
            return False
        if nxt is not None and end + tout > nxt.start:
            return False
        return True

    # =====================================================================
    # Steps 2-4 of the policy: find the earliest feasible slot
    # =====================================================================

    def find_free_slot(self, p: Package, graph: Graph, index: HashTable):
        """
        Finds the earliest feasible start time for package p.

        Loop:  (a) look at the neighbours of the cursor and ask the Graph for
        travel times, (b) ask the tree for the earliest free gap long enough
        for  travelIn + service + travelOut  (coarse free-slot search),
        (c) verify exactly with is_placement_valid; if it fails, advance the
        cursor and retry. The number of retries is bounded.

        Returns a 4-element list [start, end, unusedGap, addedTravel] or None
        if the package cannot be placed on this vehicle.
        Time: O(log n) per retry (free-slot worst case O(n)).
        """
        if not self.can_serve(p):
            return None
        earliest = max(p.window_start, self.shift_start)
        latest_end = min(p.window_end, self.shift_end)
        cursor = earliest
        max_tries = 4 * self._schedule.get_size() + 500

        for _ in range(max_tries):
            if cursor + p.service_time > latest_end:
                return None                           # no room left inside the window
            pred0 = self._schedule.predecessor(cursor)
            next0 = self._schedule.successor(cursor)
            tin = self._travel_in(pred0, p, graph, index)
            tout = self._travel_out(next0, p, graph, index)

            if tin >= Graph.INFINITY or tout >= Graph.INFINITY:
                if next0 is None:
                    return None                       # unreachable and nothing later to try
                cursor = max(cursor + 1, next0.end)   # skip past that neighbour
                continue

            # Coarse search: earliest gap that can hold travel + service + travel.
            gap_start = self._schedule.free_slot(tin + p.service_time + tout, cursor)
            if gap_start == cursor:
                previous_end = self.shift_start if pred0 is None else pred0.end
                start = max(cursor, previous_end + tin)
            else:
                start = gap_start + tin               # gap begins right after a booked slot
            start = max(start, earliest)
            if start + p.service_time > latest_end:
                return None

            # Exact verification
            if self.is_placement_valid(p, start, graph, index):
                return self._build_result(p, start, graph, index)

            # Verification failed: advance the cursor and retry.
            blocker = self._schedule.search_overlap(start, start + p.service_time)
            if blocker is not None:
                cursor = max(cursor + 1, blocker.end)
            else:
                cursor = max(cursor + 1, start + 1)
        return None

    def _build_result(self, p, start, graph, index):
        """Computes [start, end, unusedGap, addedTravel] for a verified placement."""
        pred = self._schedule.predecessor(start)
        nxt = self._schedule.successor(start)
        tin = self._travel_in(pred, p, graph, index)
        tout = self._travel_out(nxt, p, graph, index)
        gap_begin = self.shift_start if pred is None else pred.end
        gap_finish = self.shift_end if nxt is None else nxt.start
        used = tin + p.service_time + tout
        unused = (gap_finish - gap_begin) - used
        result = [0] * 4
        result[0] = start
        result[1] = start + p.service_time
        result[2] = unused
        result[3] = tin + tout
        return result

    # =====================================================================
    # Assign / release
    # =====================================================================

    def assign(self, p, start):
        """
        Books package p at 'start': inserts the slot into the tree and adds
        the weight to the used load. Returns False if the tree refuses it.
        Time: O(log n).
        """
        if not self._schedule.insert(start, start + p.service_time, p.package_id):
            return False
        self.used_load += p.weight
        return True

    def release(self, p, start):
        """
        Frees the slot starting at 'start' and releases its capacity.
        Time: O(log n).
        """
        if not self._schedule.delete(start):
            return False
        self.used_load -= p.weight
        if self.used_load < 0:
            self.used_load = 0.0
        return True

    # =====================================================================
    # Road change support
    # =====================================================================

    def find_infeasible_slots(self, graph, index):
        """
        Walks the schedule in time order and returns the START times of slots
        that can no longer be reached in time (e.g. after a road closure).
        Slots that are kept become the "previous stop" of the next check.
        Time: O(n) slots, each with a cached Graph lookup.
        """
        slots = self._schedule.to_array()
        bad = [0] * len(slots)
        bad_count = 0
        previous_end = self.shift_start
        previous_location = self.location

        for i in range(len(slots)):
            p = index.search_package(slots[i].package_id)
            if p is None:
                continue
            travel = graph.travel_time(previous_location, p.destination)
            if travel >= Graph.INFINITY or previous_end + travel > slots[i].start:
                bad[bad_count] = slots[i].start         # cannot arrive in time
                bad_count += 1
            else:
                previous_end = slots[i].end
                previous_location = p.destination
        result = [0] * bad_count
        for i in range(bad_count):
            result[i] = bad[i]
        return result

    # =====================================================================
    # Display
    # =====================================================================

    def __str__(self):
        """Short one-line summary of the vehicle."""
        return ("V" + str(self.vehicle_id) + " (" + self.type + ") | home vertex "
                + str(self.location)
                + " | shift " + IntervalTreeNode.format_time(self.shift_start) + "-"
                + IntervalTreeNode.format_time(self.shift_end)
                + " | load " + str(self.used_load) + "/" + str(self.capacity) + " kg"
                + " | slots " + str(self._schedule.get_size()))

    def describe_schedule(self, graph, index):
        """
        Full text view of this vehicle's schedule for the GUI
        ("Display Vehicle Schedule" button). Time: O(n).
        """
        sb = []
        sb.append(str(self) + "\n")
        sb.append("Interval tree height: " + str(self._schedule.get_height())
                  + "  | invariants valid: "
                  + ("true" if self._schedule.is_valid() else "false") + "\n")
        sb.append("--------------------------------------------------\n")
        slots = self._schedule.to_array()
        if len(slots) == 0:
            sb.append("(no booked slots)\n")
        for i in range(len(slots)):
            p = index.search_package(slots[i].package_id)
            sb.append(str(slots[i]))
            if p is not None:
                v = graph.get_vertex(p.destination)
                sb.append("  -> " + ("vertex " + str(p.destination) if v is None else v.name))
                sb.append("  [" + Package.priority_name(p.priority) + "]")
            sb.append("  maxEnd=" + IntervalTreeNode.format_time(slots[i].max_end))
            sb.append("\n")
        return "".join(sb)
