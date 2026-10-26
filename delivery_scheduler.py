"""
delivery_scheduler.py
---------------------------------------------------------------
The orchestrating class of the project.  OWNER: Member 4

It owns ONE PairingHeap, ONE HashTable, ONE Graph and the fleet of
Vehicles (each with its own IntervalTree). It follows the pipeline
                   RANK -> LOCATE -> ROUTE -> CHECK

  New order : HashTable registers, PairingHeap ranks, then for every
              vehicle the Graph gives travel time and the IntervalTree
              checks overlap + free slot; best fit gets the slot.
  Cancel    : HashTable finds the slot, IntervalTree deletes it.
  Reschedule: delete old slot, update window, re-queue in the heap.
  Delay     : shift later slots by delta, keep the ones still valid,
              delete and re-queue the others.
  Road change: Graph cache is invalidated, slots that are no longer
              reachable are deleted and re-queued.

The scheduler holds no schedule data itself. After each operation
get_last_message() returns a sentence for the GUI status bar.
"""

from __future__ import annotations

import sample_data
from edge import Edge
from graph import Graph
from hash_table import HashTable
from interval_tree import INT_MAX
from interval_tree_node import IntervalTreeNode
from package import Package
from pairing_heap import PairingHeap
from vehicle import Vehicle


class DeliveryScheduler:
    def __init__(self):
        """Creates an empty scheduler. Time: O(1)."""
        # Global priority queue of unassigned packages.
        self._queue = PairingHeap()

        # Package index, Vehicle index and Package-to-slot index.
        self._index = HashTable()

        # Delivery network (travel times via Dijkstra).
        self._network = Graph()

        # The fleet (plain list that grows when full).
        self._vehicles = [None] * 8
        self._vehicle_count = 0

        # Suggested id for the next package typed in the GUI.
        self._next_package_id = 101

        # Result message of the last operation (shown in the status bar).
        self._last_message = "Ready."

    # =====================================================================
    # Getters
    # =====================================================================

    def get_network(self):
        return self._network

    def get_index(self):
        return self._index

    def get_queue(self):
        return self._queue

    def get_vehicle_count(self):
        return self._vehicle_count

    def get_next_package_id(self):
        return self._next_package_id

    def get_last_message(self):
        """Message describing the result of the last operation."""
        return self._last_message

    def get_vehicle(self, vehicle_id):
        """Looks a vehicle up by id through the Hash Table. O(1) average."""
        return self._index.search_vehicle(vehicle_id)

    def get_vehicles(self):
        """Returns a copy of the fleet list (exactly vehicleCount long)."""
        copy = [None] * self._vehicle_count
        for i in range(self._vehicle_count):
            copy[i] = self._vehicles[i]
        return copy

    # =====================================================================
    # Fleet management
    # =====================================================================

    def add_vehicle(self, v: Vehicle) -> bool:
        """
        Adds a vehicle to the fleet and registers it in the Hash Table.
        Returns False if the id exists or the home vertex is invalid.
        Time: O(1) average.
        """
        if not self._network.has_vertex(v.location):
            self._last_message = "Vehicle home vertex " + str(v.location) + " does not exist."
            return False
        if not self._index.insert_vehicle(v):
            self._last_message = "Vehicle id " + str(v.vehicle_id) + " already exists."
            return False
        if self._vehicle_count == len(self._vehicles):
            bigger = [None] * (len(self._vehicles) * 2)
            for i in range(self._vehicle_count):
                bigger[i] = self._vehicles[i]
            self._vehicles = bigger
        self._vehicles[self._vehicle_count] = v
        self._vehicle_count += 1
        self._last_message = "Vehicle V" + str(v.vehicle_id) + " added."
        return True

    # =====================================================================
    # EVENT 1: NEW ORDER
    # =====================================================================

    def handle_new_order(self, pkg):
        """
        handle_new_order: validates the package, registers it in the Hash
        Table, ranks it in the Pairing Heap and runs the planning pass.
        Returns True if the order was accepted (it may still end UNASSIGNED).
        """
        if pkg.window_start >= pkg.window_end or pkg.service_time <= 0 or pkg.weight < 0:
            self._last_message = "Invalid package: check window, service time and weight."
            return False
        if not self._network.has_vertex(pkg.destination):
            self._last_message = "Destination vertex " + str(pkg.destination) + " does not exist."
            return False
        if not self._index.insert_package(pkg):                  # HASH TABLE: register
            self._last_message = "Package id " + str(pkg.package_id) + " already exists."
            return False
        if pkg.package_id >= self._next_package_id:
            self._next_package_id = pkg.package_id + 1
        pkg.status = Package.QUEUED
        self._queue.insert(pkg)                                  # PAIRING HEAP: rank
        self.run_planning_pass()                                 # extract, route, check

        if pkg.status == Package.ASSIGNED:
            self._last_message = ("P" + str(pkg.package_id) + " assigned to V"
                                  + str(pkg.vehicle_id) + " at ["
                                  + IntervalTreeNode.format_time(pkg.slot_start) + ", "
                                  + IntervalTreeNode.format_time(pkg.slot_end) + ").")
        else:
            self._last_message = ("P" + str(pkg.package_id)
                                  + " accepted but UNASSIGNED (no feasible vehicle). "
                                  + "It will be retried.")
        return True

    # =====================================================================
    # PLANNING PASS (the normal assignment loop)
    # =====================================================================

    def run_planning_pass(self):
        """
        Repeatedly extracts the most urgent package from the heap and tries
        to assign it. Packages with no feasible vehicle are marked UNASSIGNED
        and put back into the heap AFTER the pass (retry next time).
        Cancelled (stale) heap entries are dropped.

        Returns the number of packages assigned in this pass.
        """
        assigned = 0
        leftovers = [None] * self._queue.size()
        leftover_count = 0

        while not self._queue.is_empty():
            p = self._queue.extract_min()                 # most urgent first
            if p.status == Package.CANCELLED:
                continue                                  # lazy deletion
            chosen = self.assign_best_vehicle(p)
            if chosen is not None:
                assigned += 1
            else:
                p.status = Package.UNASSIGNED
                leftovers[leftover_count] = p
                leftover_count += 1
        for i in range(leftover_count):
            self._queue.insert(leftovers[i])              # retry in the next pass
        return assigned

    # =====================================================================
    # ASSIGN BEST VEHICLE (Section 4.4 policy)
    # =====================================================================

    def assign_best_vehicle(self, p):
        """
        assign_best_vehicle: for every vehicle, filter by capacity/shift,
        ask the Graph for travel times, search the tree for a free slot and
        verify it. Among feasible vehicles choose the one with the SMALLEST
        unused gap; ties go to the shorter added travel time.
        On success the slot is inserted and recorded in the Hash Table.

        Returns the chosen vehicle, or None if nobody can take the package.
        """
        best_vehicle = None
        best_slot = None

        for i in range(self._vehicle_count):
            slot = self._vehicles[i].find_free_slot(p, self._network, self._index)
            if slot is None:
                continue                                  # this vehicle is not feasible
            better = (best_slot is None
                      or slot[2] < best_slot[2]
                      or (slot[2] == best_slot[2] and slot[3] < best_slot[3]))
            if better:
                best_vehicle = self._vehicles[i]
                best_slot = slot
        if best_vehicle is None:
            return None
        if not best_vehicle.assign(p, best_slot[0]):
            return None
        p.status = Package.ASSIGNED
        p.vehicle_id = best_vehicle.vehicle_id
        p.slot_start = best_slot[0]
        p.slot_end = best_slot[1]
        self._index.put_slot(p.package_id, best_vehicle.vehicle_id, best_slot[0])  # package -> slot key
        return best_vehicle

    # =====================================================================
    # Helper: free a package's slot
    # =====================================================================

    def _release_slot(self, p):
        """
        Uses the Hash Table slot key to delete the package's interval from
        its vehicle's tree and to release the capacity. O(1) + one tree deletion.
        """
        slot_key = self._index.get_slot(p.package_id)     # [vehicleId, slotStart]
        if slot_key is not None:
            v = self._index.search_vehicle(slot_key[0])
            if v is not None:
                v.release(p, slot_key[1])
            self._index.remove_slot(p.package_id)
        p.vehicle_id = -1
        p.slot_start = -1
        p.slot_end = -1

    # =====================================================================
    # EVENT 2: CANCELLATION
    # =====================================================================

    def handle_cancellation(self, package_id):
        """
        handle_cancellation: finds the slot through the Hash Table, deletes
        it from the interval tree, marks the package CANCELLED and runs a
        planning pass because the freed slot may suit an UNASSIGNED package.
        Heap entries are removed lazily (skipped when extracted).
        """
        p = self._index.search_package(package_id)
        if p is None:
            self._last_message = "Package " + str(package_id) + " not found."
            return False
        if p.status == Package.CANCELLED:
            self._last_message = "P" + str(package_id) + " is already cancelled."
            return False
        if p.status == Package.ASSIGNED:
            self._release_slot(p)
        p.status = Package.CANCELLED
        newly_assigned = self.run_planning_pass()
        self._last_message = ("P" + str(package_id) + " cancelled. Re-planning assigned "
                              + str(newly_assigned) + " waiting package(s).")
        return True

    # =====================================================================
    # EVENT 3: RESCHEDULE
    # =====================================================================

    def handle_reschedule(self, package_id, new_window_start, new_window_end):
        """
        handle_reschedule: the customer changes the delivery window.
        Deletes the old interval, stores the new window in a fresh record
        (the old object is marked CANCELLED so any stale heap entry is
        ignored) and re-inserts the package into the heap.
        """
        old = self._index.search_package(package_id)
        if old is None:
            self._last_message = "Package " + str(package_id) + " not found."
            return False
        if old.status == Package.CANCELLED:
            self._last_message = "P" + str(package_id) + " is cancelled and cannot be rescheduled."
            return False
        if new_window_start >= new_window_end:
            self._last_message = "Invalid window: start must be before end."
            return False
        if old.status == Package.ASSIGNED:
            self._release_slot(old)                        # tree delete + capacity
        updated = old.copy()
        updated.window_start = new_window_start
        updated.window_end = new_window_end
        updated.status = Package.QUEUED
        updated.vehicle_id = -1
        updated.slot_start = -1
        updated.slot_end = -1
        old.status = Package.CANCELLED                     # stale heap copy will be skipped

        self._index.update_package(updated)                # HASH TABLE: new record
        self._queue.insert(updated)                        # PAIRING HEAP: re-queue
        self.run_planning_pass()

        if updated.status == Package.ASSIGNED:
            self._last_message = ("P" + str(package_id) + " rescheduled to V"
                                  + str(updated.vehicle_id) + " at ["
                                  + IntervalTreeNode.format_time(updated.slot_start) + ", "
                                  + IntervalTreeNode.format_time(updated.slot_end) + ").")
        else:
            self._last_message = ("P" + str(package_id)
                                  + " rescheduled but UNASSIGNED (no feasible slot yet).")
        return True

    # =====================================================================
    # EVENT 4: VEHICLE DELAY
    # =====================================================================

    def handle_vehicle_delay(self, vehicle_id, t, delta):
        """
        handle_vehicle_delay: vehicle runs late by 'delta' minutes from time t.
         1. Report all slots starting at or after t (tree range query).
         2. Remove them, then try to re-insert each one shifted by delta.
         3. Slots still valid (inside window, shift and travel rules) are kept;
            the others stay deleted and are re-queued in the heap.
        Node data is copied into plain lists first, because deleting from the
        tree can copy data between nodes.
        """
        v = self._index.search_vehicle(vehicle_id)
        if v is None:
            self._last_message = "Vehicle " + str(vehicle_id) + " not found."
            return False
        if delta <= 0:
            self._last_message = "Delay must be a positive number of minutes."
            return False
        hit = v.get_schedule().report_overlaps(t, INT_MAX)

        starts = [0] * len(hit)
        package_ids = [0] * len(hit)
        count = 0
        for i in range(len(hit)):
            if hit[i].start >= t:                          # "starting at or after t"
                starts[count] = hit[i].start
                package_ids[count] = hit[i].package_id
                count += 1
        # Remove the affected slots
        for i in range(count):
            p = self._index.search_package(package_ids[i])
            v.release(p, starts[i])
        # Re-insert in time order, shifted by delta
        kept = 0
        requeued = 0
        for i in range(count):
            p = self._index.search_package(package_ids[i])
            new_start = starts[i] + delta
            if v.is_placement_valid(p, new_start, self._network, self._index) and v.assign(p, new_start):
                p.slot_start = new_start
                p.slot_end = new_start + p.service_time
                self._index.put_slot(p.package_id, v.vehicle_id, new_start)
                kept += 1
            else:
                self._index.remove_slot(p.package_id)
                p.status = Package.QUEUED
                p.vehicle_id = -1
                p.slot_start = -1
                p.slot_end = -1
                self._queue.insert(p)                      # competes again in the heap
                requeued += 1
        reassigned = self.run_planning_pass()
        self._last_message = ("V" + str(vehicle_id) + " delayed " + str(delta) + " min from "
                              + IntervalTreeNode.format_time(t) + ": " + str(kept)
                              + " slot(s) shifted, " + str(requeued) + " re-queued, "
                              + str(reassigned) + " package(s) placed after re-planning.")
        return True

    # =====================================================================
    # EVENT 5: ROAD CHANGE
    # =====================================================================

    def handle_road_change(self, u, v, new_status):
        """
        handle_road_change: sets a road to OPEN / SLOW / CLOSED (both
        directions). The Graph invalidates its cached travel times. Every
        vehicle's schedule is then re-verified; slots that can no longer be
        reached in time are deleted and re-queued.

        Returns the number of slots re-queued, or -1 if the road does not exist.
        """
        if not self._network.set_road_status_both(u, v, new_status):
            self._last_message = "No road between vertex " + str(u) + " and " + str(v) + "."
            return -1
        requeued = 0
        for i in range(self._vehicle_count):
            vehicle = self._vehicles[i]
            while True:
                bad = vehicle.find_infeasible_slots(self._network, self._index)
                if len(bad) == 0:
                    break                                  # schedule is consistent again
                for k in range(len(bad)):
                    node = vehicle.get_schedule().find_node(bad[k])
                    if node is None:
                        continue
                    p = self._index.search_package(node.package_id)
                    self._release_slot(p)
                    p.status = Package.QUEUED
                    self._queue.insert(p)
                    requeued += 1
        reassigned = self.run_planning_pass()
        if new_status == Edge.OPEN:
            status_text = "OPEN"
        elif new_status == Edge.SLOW:
            status_text = "SLOW"
        else:
            status_text = "CLOSED"
        self._last_message = ("Road " + str(u) + " <-> " + str(v) + " is now " + status_text
                              + ". " + str(requeued) + " slot(s) re-queued, "
                              + str(reassigned) + " re-assigned.")
        return requeued

    # =====================================================================
    # Display helpers for the GUI
    # =====================================================================

    def describe_packages(self):
        """Text list of every registered package (sorted by id)."""
        all_packages = self._index.get_all_packages()
        sb = []
        sb.append("Packages registered: " + str(len(all_packages))
                  + "  |  waiting in heap: " + str(self._count_waiting())
                  + "  |  slots booked: " + str(self._index.slot_count()) + "\n")
        sb.append("--------------------------------------------------\n")
        if len(all_packages) == 0:
            sb.append("(no packages)\n")
        for i in range(len(all_packages)):
            sb.append(str(all_packages[i]) + "\n")
        return "".join(sb)

    def _count_waiting(self):
        """Number of live (not cancelled) packages in the heap."""
        in_heap = self._queue.to_array()
        live = 0
        for i in range(len(in_heap)):
            if in_heap[i].status != Package.CANCELLED:
                live += 1
        return live

    def describe_vehicle_schedule(self, vehicle_id):
        """Text view of one vehicle's schedule, or a not-found message."""
        v = self._index.search_vehicle(vehicle_id)
        if v is None:
            return "Vehicle " + str(vehicle_id) + " not found.\n"
        return v.describe_schedule(self._network, self._index)

    def describe_vehicles(self):
        """Text list of the whole fleet."""
        sb = []
        sb.append("Fleet size: " + str(self._vehicle_count) + "\n")
        sb.append("--------------------------------------------------\n")
        for i in range(self._vehicle_count):
            sb.append(str(self._vehicles[i]) + "\n")
        return "".join(sb)

    # =====================================================================
    # Reset and sample data
    # =====================================================================

    def clear(self):
        """Removes every package, vehicle, slot and vertex."""
        self._queue.clear()
        self._index.clear()
        self._network.clear()
        self._vehicles = [None] * 8
        self._vehicle_count = 0
        self._next_package_id = 101
        self._last_message = "Everything cleared."

    def load_sample_data(self):
        """
        Resets the system and loads a small demo network, 3 vehicles and
        5 packages (see sample_data.py). Everything goes through the real
        handlers, so the data structures are really populated (nothing is
        hard-coded output).

        Vertices: 0 Warehouse-1, 1 Station-1, 2 Station-2, 3..8 Dest-1..Dest-6.
        """
        self.clear()
        sample_data.populate(self)
        self._last_message = sample_data.SAMPLE_MESSAGE
