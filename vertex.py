"""
vertex.py
---------------------------------------------------------------
One vertex (node) of the delivery network graph.  OWNER: Member 3

A vertex is a warehouse, a delivery station or a customer destination.
Its outgoing roads are kept in a singly linked list of Edge objects
(adjacency list), so no built-in container is needed.
"""


class Vertex:
    # Vertex types.
    WAREHOUSE = 0
    STATION = 1
    DESTINATION = 2

    def __init__(self, vertex_id, name, vertex_type):
        """Creates a vertex with no roads yet. Time: O(1)."""
        # Unique id. It is also the index of this vertex inside the Graph.
        self.id = vertex_id

        # Readable name, for example "Station-3" or "Dest-12".
        self.name = name

        # One of WAREHOUSE, STATION, DESTINATION.
        self.type = vertex_type

        # Head of the linked list of OUTGOING edges (None if there are none).
        self.first_edge = None

    def type_name(self):
        """Returns the type as readable text. Time: O(1)."""
        if self.type == Vertex.WAREHOUSE:
            return "Warehouse"
        if self.type == Vertex.STATION:
            return "Station"
        return "Destination"

    def __str__(self):
        """Text such as "3: Station-3 (Station)". Time: O(1)."""
        return str(self.id) + ": " + self.name + " (" + self.type_name() + ")"
