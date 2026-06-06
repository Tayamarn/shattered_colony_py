"""
SniperTower — stationary auto-targeting turret.

Not an Entity (doesn't move; hp can be added later if towers become
destructible).  Stored in world.towers[(r, c)].  tick() returns the zombie
it chose to shoot (after consuming ammo) so game.py can spawn the Projectile.
This keeps tower.py free of a projectile import.
"""

from __future__ import annotations

from config import TOWER_RANGE_PX, TOWER_FIRE_RATE


class SniperTower:
    def __init__(self, r: int, c: int, world) -> None:
        self.r = r
        self.c = c
        wx, wy      = world.grid_center(r, c)
        self.x      = float(wx)
        self.y      = float(wy)
        self._cd    = 0.0   # cooldown remaining in seconds
        self._world = world

    def tick(self, dt: float, zombies: list, resources) -> object | None:
        """Advance one tick.  Returns the zombie to shoot, or None."""
        self._cd = max(0.0, self._cd - dt)
        if self._cd > 0:
            return None
        target = self._nearest_in_range(zombies)
        if target is None:
            return None
        if not resources.spend(ammo=1):
            return None
        self._cd = 1.0 / TOWER_FIRE_RATE
        return target

    def _nearest_in_range(self, zombies: list):
        best, best_d2 = None, TOWER_RANGE_PX ** 2
        for z in zombies:
            if not z.alive:
                continue
            d2 = (z.x - self.x) ** 2 + (z.y - self.y) ** 2
            if d2 >= best_d2:
                continue
            if not self._world.has_los(self.x, self.y, z.x, z.y):
                continue
            best_d2, best = d2, z
        return best
