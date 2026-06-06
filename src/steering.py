"""
Steering — post-movement entity separation.

After all entities have moved for a frame, `separate()` pushes overlapping
pairs apart by half the overlap each.  Each axis is tried independently so
entities slide along walls rather than clipping through them.

No pygame dependency.
"""

from __future__ import annotations
from math import sqrt

from tiles import WALKABLE


def separate(entities: list, world) -> None:
    """Push every overlapping pair of entities apart by half the overlap.

    Entities need: x (float), y (float), radius (int|float).
    World needs:   tile_at_pixel(x, y) → Tile.
    """
    n = len(entities)
    for i in range(n):
        a = entities[i]
        for j in range(i + 1, n):
            b = entities[j]
            dx = b.x - a.x
            dy = b.y - a.y
            dist_sq = dx * dx + dy * dy
            min_dist = float(a.radius + b.radius)

            if dist_sq >= min_dist * min_dist or dist_sq < 1e-9:
                continue

            dist = sqrt(dist_sq)
            push = (min_dist - dist) * 0.5
            nx, ny = dx / dist, dy / dist

            # Push a in the −normal direction, axis-by-axis
            new_ax = a.x - nx * push
            if world.tile_at_pixel(new_ax, a.y) in WALKABLE:
                a.x = new_ax
            new_ay = a.y - ny * push
            if world.tile_at_pixel(a.x, new_ay) in WALKABLE:
                a.y = new_ay

            # Push b in the +normal direction, axis-by-axis
            new_bx = b.x + nx * push
            if world.tile_at_pixel(new_bx, b.y) in WALKABLE:
                b.x = new_bx
            new_by = b.y + ny * push
            if world.tile_at_pixel(b.x, new_by) in WALKABLE:
                b.y = new_by
