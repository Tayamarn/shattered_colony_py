"""
Colonist — a selectable unit controlled by the player.

Phase 1: exists at a position.
Phase 2: selection state (handled externally in Selection).
Phase 3: orders deque + tick().
"""

from __future__ import annotations
from collections import deque

from entity import Entity
from config import COLONIST_HP, COLONIST_SPEED, COLONIST_RADIUS


class Colonist(Entity):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(
            x=x, y=y,
            hp=COLONIST_HP,
            speed=COLONIST_SPEED,
            radius=COLONIST_RADIUS,
        )
        self.orders: deque = deque()

    def tick(self, dt: float, world) -> None:
        if not self.alive or not self.orders:
            return
        done = self.orders[0].execute(self, dt, world)
        if done:
            self.orders.popleft()
