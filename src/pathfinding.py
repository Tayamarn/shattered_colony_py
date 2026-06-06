"""
Pathfinding — A* on the tile grid.

8-directional movement with diagonal cost √2.
Diagonal steps are only allowed when BOTH cardinal neighbours are walkable
(the corner-cut rule), preventing colonists from clipping through corners.

Called once per MoveCommand, never per frame.  No pygame dependency.
"""

from __future__ import annotations
import heapq
from math import sqrt

from tiles import WALKABLE
from world import World

_SQRT2 = sqrt(2)


def find_path(
    world: World,
    start_r: int,
    start_c: int,
    goal_r: int,
    goal_c: int,
) -> list[tuple[int, int]]:
    """
    Return a list of (r, c) waypoints from start (exclusive) to goal
    (inclusive).  Returns [] when start == goal, goal is not walkable,
    or no path exists.
    """
    if start_r == goal_r and start_c == goal_c:
        return []
    if world.tile_at(goal_r, goal_c) not in WALKABLE:
        return []

    def h(r: int, c: int) -> float:
        dr = abs(goal_r - r)
        dc = abs(goal_c - c)
        return max(dr, dc) + (_SQRT2 - 1) * min(dr, dc)

    # heap entries: (f, g, r, c)
    open_heap: list[tuple[float, float, int, int]] = [
        (h(start_r, start_c), 0.0, start_r, start_c)
    ]
    g_score: dict[tuple[int, int], float] = {(start_r, start_c): 0.0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}

    while open_heap:
        _, g, r, c = heapq.heappop(open_heap)

        if r == goal_r and c == goal_c:
            return _reconstruct(came_from, r, c)

        if g > g_score.get((r, c), float("inf")):
            continue  # stale heap entry

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue

                nr, nc = r + dr, c + dc

                if not (0 <= nr < world.rows and 0 <= nc < world.cols):
                    continue
                if world.tile_at(nr, nc) not in WALKABLE:
                    continue

                # Diagonal corner-cut rule
                if dr != 0 and dc != 0:
                    if world.tile_at(r + dr, c) not in WALKABLE:
                        continue
                    if world.tile_at(r, c + dc) not in WALKABLE:
                        continue

                step_cost = _SQRT2 if (dr != 0 and dc != 0) else 1.0
                new_g = g + step_cost

                neighbour = (nr, nc)
                if new_g < g_score.get(neighbour, float("inf")):
                    g_score[neighbour] = new_g
                    came_from[neighbour] = (r, c)
                    heapq.heappush(
                        open_heap, (new_g + h(nr, nc), new_g, nr, nc)
                    )

    return []  # no path


def _reconstruct(
    came_from: dict[tuple[int, int], tuple[int, int]],
    r: int,
    c: int,
) -> list[tuple[int, int]]:
    path: list[tuple[int, int]] = []
    node = (r, c)
    while node in came_from:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path
