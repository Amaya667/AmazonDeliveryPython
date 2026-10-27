# Amazon Last-Mile Delivery - Interval Tree Scheduler (Python / Tkinter)

A complete Python port of the Java Eclipse project `Amazon`. Every Java class is one Python
class in its own module, all algorithms are unchanged, and the Swing GUI is replaced by a Tkinter GUI
with the same functionality.

## Run

```bash
cd AmazonDeliveryPython
python main.py
```

* Python 3.8+ (developed and tested on Python 3.12) and **no third-party packages** (see `requirements.txt`).
* On Linux install Tkinter once: `sudo apt install python3-tk`.
* Works in VS Code / PyCharm: open the folder and run `main.py`.

The program starts with the demo data already loaded (9 vertices, 3 vehicles, 5 packages), exactly
like the Java version.

## Project structure

| Python module              | Java class            | Role |
|----------------------------|-----------------------|------|
| `main.py`                  | `Main`                | Entry point: scheduler -> sample data -> GUI |
| `gui.py`                   | `MainFrame`           | Tkinter window (replaces Swing) |
| `delivery_scheduler.py`    | `DeliveryScheduler`   | Orchestrator: RANK -> LOCATE -> ROUTE -> CHECK |
| `package.py`               | `Package`             | One customer order |
| `vehicle.py`               | `Vehicle`             | Fleet member + placement logic, owns one `IntervalTree` |
| `interval_tree.py`         | `IntervalTree`        | Augmented AVL interval tree (hand-written) |
| `interval_tree_node.py`    | `IntervalTreeNode`    | Tree node (`start`, `end`, `max_end`, `height`) |
| `pairing_heap.py`          | `PairingHeap`         | Urgency queue, two-pass pairing (hand-written) |
| `pairing_heap_node.py`     | `PairingHeapNode`     | Left-child / right-sibling node |
| `hash_table.py`            | `HashTable`           | Chained hash table with 3 indexes (hand-written) |
| `hash_node.py`             | `HashNode`            | One chain entry |
| `graph.py`                 | `Graph`               | Weighted directed graph + Dijkstra with its own binary heap |
| `vertex.py`                | `Vertex`              | Graph vertex + adjacency list head |
| `edge.py`                  | `Edge`                | Road (OPEN / SLOW / CLOSED) |
| `sample_data.py`           | *(part of `DeliveryScheduler.loadSampleData`)* | Demo network, vehicles and packages |

`sample_data.py` was split out of `DeliveryScheduler.loadSampleData()` so the demo data can be edited
without touching the scheduler. `DeliveryScheduler.load_sample_data()` still exists and calls it, and
the data still goes through the real handlers (`add_vehicle`, `handle_new_order`, ...).

## Data structures are still manual

Nothing was replaced by a library: no `heapq`, `queue`, `collections.deque`, `networkx`, no scheduling
package and no `dict` standing in for the hash table. Where Java used arrays, Python uses plain lists
as fixed-size arrays that are grown by hand (hash buckets, graph vertex array, report buffer, fleet array).

* **Pairing Heap** - iterative two-pass `extract_min`, O(1) `insert` / `meld`.
* **Hash Table** - separate chaining, `(key * 31) mod capacity`, doubles at load factor 0.75. The 32-bit
  integer overflow of the Java hash function is reproduced, so bucket placement matches Java.
* **Interval Tree** - AVL rotations, `max_end` augmentation, overlap / report / stabbing / free-slot /
  predecessor / successor queries and the invariant checker `is_valid()`.
* **Graph + Dijkstra** - adjacency lists, memoised distance rows, hand-written array binary min-heap.

## GUI

All buttons from the Swing version: **Add Package, Assign Vehicle, Cancel Package, Reschedule Package,
Search Overlap, Display Vehicles, Display Packages, Display Graph, Load Sample Data, Clear, Exit**,
plus the input panel, a scrollable monospace **output area** and a **status bar**.
Times can be typed as `HH:MM` (e.g. `14:30`) or as minutes from midnight (e.g. `870`).
`Clear` and `Exit` ask for confirmation, like the original.

`handle_vehicle_delay` and `handle_road_change` are fully implemented in the scheduler (as in the Java
project) but, as in the Java GUI, have no button.

## Naming conventions

* Java `camelCase` -> Python `snake_case` (`handleNewOrder` -> `handle_new_order`, `packageId` -> `package_id`).
* Java `toString()` -> `__str__()`; Java `null` -> `None`; Java `int[]` results -> Python lists.
* `Edge.from` -> `Edge.from_vertex` (`from` is a reserved word in Python).
* `Package.copy()`, `Package.priority_name()`, `Package.status_name()` etc. keep their names.
* Circular imports are avoided: `Vehicle` and `HashTable` reference each other only in type hints
  (guarded by `typing.TYPE_CHECKING`); nothing needs the other module at import time.

## Verification

The Python backend was checked against the original Java source compiled with JDK 21, using the same
deterministic pseudo-random operation sequences and diffing the complete text output:

* 300 random orders / cancellations / reschedules / vehicle delays / road changes on the real scheduler,
  with all-pairs Dijkstra results and full schedule / heap / graph dumps: **identical output**, and
  every vehicle's AVL tree stayed valid after every step.
* 6,000 random inserts / deletes / queries on `IntervalTree` (grown to 1,801 slots, height 13),
  4,000 `PairingHeap` operations incl. `meld`, 5,000 `HashTable` operations incl. keys that overflow 32 bits,
  and a 60-vertex random `Graph` with road closures and removals: **identical output**.
* Every module imports cleanly on its own, `pyflakes` reports nothing, and every GUI button was driven
  under a virtual display.
