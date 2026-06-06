"""
Commands — order objects placed in a colonist's orders deque.

Each command owns its own execution state and sub-steps.
execute(colonist, dt, world) → bool  returns True when the command is done.
game.py never inspects the sub-steps; it only sees True/False.
"""

from __future__ import annotations
from collections import deque
from math import sqrt
from typing import Callable

from config import ARRIVAL_RADIUS, SCAVENGE_DURATION
from pathfinding import find_path
from tiles import WALKABLE


class MoveCommand:
    """Walk a colonist through a list of tile waypoints."""

    def __init__(self, waypoints: list[tuple[int, int]]) -> None:
        self._waypoints: deque[tuple[int, int]] = deque(waypoints)

    def execute(self, colonist, dt: float, world) -> bool:
        """Advance the colonist one tick.  Returns True when all waypoints done."""
        if not self._waypoints:
            return True

        target_r, target_c = self._waypoints[0]
        tx, ty = world.grid_center(target_r, target_c)

        dx = tx - colonist.x
        dy = ty - colonist.y
        dist = sqrt(dx * dx + dy * dy)

        if dist <= ARRIVAL_RADIUS:
            self._waypoints.popleft()
            return not self._waypoints

        step = colonist.speed * dt
        if step >= dist:
            # Snap to waypoint centre rather than overshooting
            colonist.x = float(tx)
            colonist.y = float(ty)
            self._waypoints.popleft()
            return not self._waypoints

        colonist.x += (dx / dist) * step
        colonist.y += (dy / dist) * step
        return False


class ScavengeCommand:
    """Walk a colonist to a building, work SCAVENGE_DURATION seconds, collect loot."""

    _CARDINALS = ((-1, 0), (1, 0), (0, -1), (0, 1))

    def __init__(
        self,
        building_r: int,
        building_c: int,
        resources,
        on_rescue: Callable[[float, float], None],
    ) -> None:
        self._br         = building_r
        self._bc         = building_c
        self._resources  = resources
        self._on_rescue  = on_rescue
        self._nav: MoveCommand | None = None
        self._work_timer: float = 0.0
        self._state: str = "init"

    def execute(self, colonist, dt: float, world) -> bool:
        if self._state == "init":
            self._start_navigate(colonist, world)

        if self._state == "navigate":
            if self._nav is None or self._nav.execute(colonist, dt, world):
                self._state = "work"

        if self._state == "work":
            self._work_timer += dt
            if self._work_timer >= SCAVENGE_DURATION:
                self._complete(colonist, world)
                self._state = "done"

        return self._state == "done"

    @property
    def progress(self) -> float | None:
        """Work progress 0.0–1.0 while working, None otherwise."""
        if self._state != "work":
            return None
        return min(1.0, self._work_timer / SCAVENGE_DURATION)

    def _start_navigate(self, colonist, world) -> None:
        start_r, start_c = world.pixel_to_grid(colonist.x, colonist.y)
        adj = [
            (self._br + dr, self._bc + dc)
            for dr, dc in self._CARDINALS
            if world.tile_at(self._br + dr, self._bc + dc) in WALKABLE
        ]
        if not adj:
            self._state = "done"
            return
        if (start_r, start_c) in adj:
            self._state = "work"
            return
        best_path: list | None = None
        for goal_r, goal_c in adj:
            path = find_path(world, start_r, start_c, goal_r, goal_c)
            if path and (best_path is None or len(path) < len(best_path)):
                best_path = path
        if best_path:
            self._nav = MoveCommand(best_path)
            self._state = "navigate"
        else:
            self._state = "done"

    def _complete(self, colonist, world) -> None:
        bd = world.get_building(self._br, self._bc)
        if bd is None or bd.scavenged:
            return
        bd.scavenged = True
        self._resources.earn(wood=bd.wood, ammo=bd.ammo)
        if bd.has_colonist:
            self._on_rescue(colonist.x, colonist.y)
