"""
Projectile — a homing bullet fired by a SniperTower.

Flies straight toward its target zombie each tick.  If the target dies in
flight the projectile disappears; it does not continue to a fixed point.
"""

from __future__ import annotations
from math import sqrt

from entity import Entity
from config import PROJ_SPEED, PROJ_RADIUS, TOWER_DAMAGE


class Projectile(Entity):
    def __init__(self, x: float, y: float, target) -> None:
        super().__init__(x=x, y=y, hp=1, speed=PROJ_SPEED, radius=PROJ_RADIUS)
        self._target = target

    def tick(self, dt: float) -> None:
        if not self.alive:
            return
        if not self._target.alive:
            self.alive = False
            return

        dx = self._target.x - self.x
        dy = self._target.y - self.y
        dist = sqrt(dx * dx + dy * dy)
        step = self.speed * dt

        if step >= dist:
            self._target.take_damage(TOWER_DAMAGE)
            self.alive = False
        else:
            self.x += dx / dist * step
            self.y += dy / dist * step
