"""
Zombie — direct-pursuit AI v1.

Moves toward the nearest living colonist each tick, sliding around walls
rather than clipping through them.  Attacks with a cooldown when in range.
V2 (flow field) is deferred until v1 feel is confirmed.
"""

from __future__ import annotations
from math import sqrt

from entity import Entity
from tiles import WALKABLE
from config import (
    ZOMBIE_HP, ZOMBIE_SPEED, ZOMBIE_RADIUS,
    ZOMBIE_DAMAGE, ZOMBIE_ATTACK_RATE, ZOMBIE_ATTACK_REACH,
)


class Zombie(Entity):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            hp=ZOMBIE_HP,
            speed=ZOMBIE_SPEED,
            radius=ZOMBIE_RADIUS,
        )
        self._attack_cd: float = 0.0

    def tick(self, dt: float, world, colonists: list) -> None:
        if not self.alive:
            return
        self._attack_cd = max(0.0, self._attack_cd - dt)

        target = self._nearest_living(colonists)
        if target is None:
            return

        dx = target.x - self.x
        dy = target.y - self.y
        dist = sqrt(dx * dx + dy * dy)

        if dist <= self.radius + target.radius + ZOMBIE_ATTACK_REACH:
            if self._attack_cd == 0.0:
                target.take_damage(ZOMBIE_DAMAGE)
                self._attack_cd = 1.0 / ZOMBIE_ATTACK_RATE
            return

        step = self.speed * dt
        vx = dx / dist * step
        vy = dy / dist * step
        self._slide_move(vx, vy, world)

    def _slide_move(self, dx: float, dy: float, world) -> None:
        """Move with wall-sliding: try full step, then x-only, then y-only."""
        if world.tile_at_pixel(self.x + dx, self.y + dy) in WALKABLE:
            self.x += dx
            self.y += dy
        elif world.tile_at_pixel(self.x + dx, self.y) in WALKABLE:
            self.x += dx
        elif world.tile_at_pixel(self.x, self.y + dy) in WALKABLE:
            self.y += dy

    def _nearest_living(self, colonists: list):
        best, best_d2 = None, float("inf")
        for c in colonists:
            if not c.alive:
                continue
            d2 = (c.x - self.x) ** 2 + (c.y - self.y) ** 2
            if d2 < best_d2:
                best_d2, best = d2, c
        return best
