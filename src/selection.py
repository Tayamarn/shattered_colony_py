"""
Selection — owns the set of currently selected entities.

No pygame dependency; operates entirely in world coordinates.
game.py feeds it events from input_handler and the entity lists to search.
"""

from __future__ import annotations
from entity import Entity


class Selection:
    def __init__(self) -> None:
        self.selected: set[Entity] = set()

    def click_select(
        self, wx: float, wy: float, entities: list[Entity]
    ) -> None:
        """Select the first entity whose radius contains (wx, wy).
        Deselects all if the click misses every entity."""
        for e in entities:
            if (e.x - wx) ** 2 + (e.y - wy) ** 2 <= e.radius ** 2:
                self.selected = {e}
                return
        self.deselect_all()

    def box_select(
        self,
        world_x0: float,
        world_y0: float,
        world_x1: float,
        world_y1: float,
        entities: list[Entity],
    ) -> None:
        """Select all entities whose centre lies inside the given world rect.
        Drag direction is irrelevant — min/max normalises the corners."""
        min_x, max_x = min(world_x0, world_x1), max(world_x0, world_x1)
        min_y, max_y = min(world_y0, world_y1), max(world_y0, world_y1)
        self.selected = {
            e for e in entities
            if min_x <= e.x <= max_x and min_y <= e.y <= max_y
        }

    def deselect_all(self) -> None:
        self.selected.clear()
