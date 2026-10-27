"""
graph.py
---------------------------------------------------------------
Weighted DIRECTED graph of the delivery network.  OWNER: Member 3

- Vertices: warehouses, stations and destinations.
- Edges: roads weighted by travel time in minutes.
- Dijkstra's algorithm computes the shortest travel time.
- Results are MEMOIZED: after one Dijkstra run from a source vertex,
  the distances to every other vertex are cached, so later
  travel_time(u, v) calls for the same source cost O(1).
- When a road changes status (or an edge is added / removed), the whole
  cache is invalidated so no stale travel time is ever used.

Dijkstra uses a small array-based binary min-heap written by hand
(heapq / PriorityQueue are not allowed), giving O((V + E) log V).
"""

from edge import Edge
from vertex import Vertex


class Graph:
    # Distance meaning "unreachable". Small enough that adding two never overflows.
    INFINITY = 1000000

    def __init__(self):
        """Creates an empty graph. Time: O(1)."""
        # vertices[i] is the vertex whose id is i.
        self._vertices = [None] * 16

        # Number of vertices stored.
        self._vertex_count = 0

        # Number of directed edges stored.
        self._edge_count = 0

        # cache[u] = shortest distances from u to every vertex (None = not computed yet).
        self._cache = [None] * 16

        # ---- arrays used by the hand-written binary min-heap inside Dijkstra ----
        self._heap_distance = None     # priority (distance) of each heap entry
        self._heap_vertex = None       # vertex id of each heap entry
        self._heap_size = 0            # number of entries currently in the heap

    # =====================================================================
    # VERTICES
    # =====================================================================

    def add_vertex(self, name, vertex_type):
        """
        Adds a new vertex and returns its id (ids are 0, 1, 2, ...).
        The arrays double in size when full. Time: O(1) amortized.
        """
        if self._vertex_count == len(self._vertices):
            bigger_vertices = [None] * (len(self._vertices) * 2)
            bigger_cache = [None] * (len(self._cache) * 2)
            for i in range(self._vertex_count):
                bigger_vertices[i] = self._vertices[i]
                bigger_cache[i] = self._cache[i]
            self._vertices = bigger_vertices
            self._cache = bigger_cache
        vertex_id = self._vertex_count
        self._vertices[vertex_id] = Vertex(vertex_id, name, vertex_type)
        self._vertex_count += 1
        self.invalidate_cache()             # old cached rows have the wrong length now
        return vertex_id

    def has_vertex(self, vertex_id):
        """True if id is a valid vertex id. Time: O(1)."""
        return vertex_id >= 0 and vertex_id < self._vertex_count

    def get_vertex(self, vertex_id):
        """Returns the vertex with this id (None if invalid). Time: O(1)."""
        return self._vertices[vertex_id] if self.has_vertex(vertex_id) else None

    def find_vertex_by_name(self, name):
        """Finds a vertex id by its name (-1 if not found). Time: O(V)."""
        for i in range(self._vertex_count):
            if self._vertices[i].name.lower() == name.lower():
                return i
        return -1

    def get_vertex_count(self):
        """Number of vertices."""
        return self._vertex_count

    def get_edge_count(self):
        """Number of directed edges."""
        return self._edge_count

    # =====================================================================
    # EDGES
    # =====================================================================

    def add_edge(self, u, v, travel_time):
        """
        Adds a directed road u -> v with the given travel time (minutes).
        If the road already exists, only its travel time is updated.
        Returns False for invalid vertices or a non-positive time.
        Time: O(degree of u).
        """
        if not self.has_vertex(u) or not self.has_vertex(v) or u == v or travel_time <= 0:
            return False
        existing = self.find_edge(u, v)
        if existing is not None:
            existing.base_time = travel_time
        else:
            edge = Edge(u, v, travel_time)
            edge.next = self._vertices[u].first_edge      # add at the front of the list
            self._vertices[u].first_edge = edge
            self._edge_count += 1
        self.invalidate_cache()
        return True

    def add_road(self, u, v, travel_time):
        """Adds the road in BOTH directions (a normal two-way street)."""
        first = self.add_edge(u, v, travel_time)
        second = self.add_edge(v, u, travel_time)
        return first and second

    def remove_edge(self, u, v):
        """
        Removes the directed road u -> v.
        Returns False if there was no such road. Time: O(degree of u).
        """
        if not self.has_vertex(u):
            return False
        previous = None
        current = self._vertices[u].first_edge
        while current is not None:
            if current.to == v:
                if previous is None:
                    self._vertices[u].first_edge = current.next
                else:
                    previous.next = current.next
                self._edge_count -= 1
                self.invalidate_cache()
                return True
            previous = current
            current = current.next
        return False

    def find_edge(self, u, v):
        """Finds the directed edge u -> v (None if none). Time: O(degree of u)."""
        if not self.has_vertex(u):
            return None
        current = self._vertices[u].first_edge
        while current is not None:
            if current.to == v:
                return current
            current = current.next
        return None

    def set_road_status(self, u, v, status):
        """
        Changes the status of the road u -> v (Edge.OPEN, Edge.SLOW or Edge.CLOSED)
        and INVALIDATES every cached travel time. Returns False if no such road.
        Time: O(degree of u).
        """
        edge = self.find_edge(u, v)
        if edge is None:
            return False
        edge.status = status
        self.invalidate_cache()
        return True

    def set_road_status_both(self, u, v, status):
        """Sets the status of the road in both directions (ignores a missing reverse road)."""
        forward = self.set_road_status(u, v, status)
        self.set_road_status(v, u, status)
        return forward

    # =====================================================================
    # DIJKSTRA + TRAVEL TIME
    # =====================================================================

    def invalidate_cache(self):
        """Forgets every memoized Dijkstra result. Time: O(V)."""
        for i in range(len(self._cache)):
            self._cache[i] = None

    def travel_time(self, u, v):
        """
        Travel time in minutes from u to v (INFINITY if unreachable).
        The first call for a source u runs Dijkstra and caches the whole
        distance row; later calls from the same u are O(1).
        Time: O((V + E) log V) for a cache miss, O(1) for a hit.
        """
        if not self.has_vertex(u) or not self.has_vertex(v):
            return Graph.INFINITY
        if u == v:
            return 0
        if self._cache[u] is None:
            self._cache[u] = self._dijkstra(u, None)
        return self._cache[u][v]

    def is_reachable(self, u, v):
        """True if v can be reached from u using only non-closed roads."""
        return self.travel_time(u, v) < Graph.INFINITY

    def _dijkstra(self, source, previous):
        """
        Dijkstra's shortest-path algorithm from 'source'.

        Idea: repeatedly take the closest not-yet-finished vertex from the
        min-heap, then try to shorten the distance of its neighbours
        ("relaxation"). Closed roads are skipped. When a shorter distance is
        found, a new entry is pushed; outdated heap entries are ignored when
        they are popped ("lazy deletion").

        'previous' - if not None, filled with the previous vertex on each shortest path
        Returns the distance list (INFINITY for unreachable vertices).
        Time: O((V + E) log V).
        """
        distance = [0] * self._vertex_count
        for i in range(self._vertex_count):
            distance[i] = Graph.INFINITY
            if previous is not None:
                previous[i] = -1
        distance[source] = 0

        # Every push comes from one relaxation, so edgeCount + 2 slots are enough.
        self._heap_distance = [0] * (self._edge_count + 2)
        self._heap_vertex = [0] * (self._edge_count + 2)
        self._heap_size = 0
        self._heap_push(0, source)

        while self._heap_size > 0:
            current_distance = self._heap_distance[0]
            u = self._heap_vertex[0]
            self._heap_pop()

            if current_distance > distance[u]:
                continue                            # outdated entry, skip
            edge = self._vertices[u].first_edge
            while edge is not None:
                if not edge.is_closed():
                    candidate = current_distance + edge.effective_time()
                    if candidate < distance[edge.to]:
                        distance[edge.to] = candidate
                        if previous is not None:
                            previous[edge.to] = u
                        self._heap_push(candidate, edge.to)
                edge = edge.next
        return distance

    def shortest_path(self, u, v):
        """
        Returns the shortest path from u to v as a list of vertex ids
        (including both ends), or None if v is unreachable.
        Time: O((V + E) log V).
        """
        if not self.has_vertex(u) or not self.has_vertex(v):
            return None
        previous = [0] * self._vertex_count
        distance = self._dijkstra(u, previous)
        if distance[v] >= Graph.INFINITY:
            return None
        # Count the vertices on the path, then fill the array from the back.
        length = 1
        step = v
        while step != u:
            step = previous[step]
            length += 1
        path = [0] * length
        step = v
        for i in range(length - 1, -1, -1):
            path[i] = step
            step = previous[step]
        return path

    # =====================================================================
    # Hand-written binary min-heap (used only by Dijkstra)
    # =====================================================================

    def _heap_push(self, distance, vertex):
        """Adds (distance, vertex) to the heap and sifts it up. Time: O(log n)."""
        i = self._heap_size
        self._heap_size += 1
        while i > 0:
            parent = (i - 1) // 2
            if self._heap_distance[parent] <= distance:
                break
            self._heap_distance[i] = self._heap_distance[parent]
            self._heap_vertex[i] = self._heap_vertex[parent]
            i = parent
        self._heap_distance[i] = distance
        self._heap_vertex[i] = vertex

    def _heap_pop(self):
        """Removes the smallest entry (index 0) and sifts down. Time: O(log n)."""
        self._heap_size -= 1
        if self._heap_size == 0:
            return
        last_distance = self._heap_distance[self._heap_size]
        last_vertex = self._heap_vertex[self._heap_size]
        i = 0
        while True:
            child = 2 * i + 1
            if child >= self._heap_size:
                break
            if (child + 1 < self._heap_size
                    and self._heap_distance[child + 1] < self._heap_distance[child]):
                child += 1                          # pick the smaller child
            if self._heap_distance[child] >= last_distance:
                break
            self._heap_distance[i] = self._heap_distance[child]
            self._heap_vertex[i] = self._heap_vertex[child]
            i = child
        self._heap_distance[i] = last_distance
        self._heap_vertex[i] = last_vertex

    # =====================================================================
    # DISPLAY
    # =====================================================================

    def describe(self):
        """
        Builds a text view of the whole graph (adjacency lists with travel
        times and road status) for the GUI "Display Graph" button.
        Time: O(V + E).
        """
        sb = []
        sb.append("Delivery network: " + str(self._vertex_count) + " vertices, "
                  + str(self._edge_count) + " directed roads\n")
        sb.append("--------------------------------------------------\n")
        for i in range(self._vertex_count):
            sb.append(str(self._vertices[i]) + "\n")
            edge = self._vertices[i].first_edge
            if edge is None:
                sb.append("     (no outgoing roads)\n")
            while edge is not None:
                sb.append("     -> " + self._vertices[edge.to].name
                          + "  " + str(edge.base_time) + " min  ["
                          + edge.status_name() + "]\n")
                edge = edge.next
        return "".join(sb)

    def clear(self):
        """Removes every vertex and edge. Time: O(1)."""
        self._vertices = [None] * 16
        self._cache = [None] * 16
        self._vertex_count = 0
        self._edge_count = 0
