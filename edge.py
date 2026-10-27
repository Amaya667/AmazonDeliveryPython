"""
edge.py
---------------------------------------------------------------
One directed road of the delivery network.  OWNER: Member 3

An edge goes from one vertex to vertex 'to' and is weighted by the
travel time in minutes. Edges of the same source vertex are chained
together through the 'next' pointer (adjacency list).

A road can be OPEN (normal), SLOW (travel time doubles) or CLOSED
(cannot be used). Road status changes are handled by the scheduler.
"""


class Edge:
    # Road status values.
    OPEN = 0
    SLOW = 1
    CLOSED = 2

    def __init__(self, from_vertex, to, base_time):
        """Creates an open road. Time: O(1)."""
        # Source vertex id.
        self.from_vertex = from_vertex

        # Destination vertex id.
        self.to = to

        # Normal travel time in minutes (used when the road is OPEN).
        self.base_time = base_time

        # Current status: OPEN, SLOW or CLOSED.
        self.status = Edge.OPEN

        # Next outgoing edge of the same source vertex.
        self.next = None

    def effective_time(self):
        """
        Travel time that Dijkstra should use right now:
        OPEN -> baseTime, SLOW -> 2 * baseTime, CLOSED -> not usable
        (callers must test is_closed() first). Time: O(1).
        """
        if self.status == Edge.SLOW:
            return self.base_time * 2
        return self.base_time

    def is_closed(self):
        """True when the road cannot be used. Time: O(1)."""
        return self.status == Edge.CLOSED

    def status_name(self):
        """Status as readable text. Time: O(1)."""
        if self.status == Edge.SLOW:
            return "SLOW"
        if self.status == Edge.CLOSED:
            return "CLOSED"
        return "OPEN"
