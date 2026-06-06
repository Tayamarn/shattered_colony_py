"""
Spawner — wave timer that emits Zombie lists at the four bridge entry points.

Entry points are the map-edge tiles of each bridge axis.  Loot amounts and
timing constants live in config.py so balance changes need no code edits.
"""

import random

from config import (
    BRIDGE_COL, BRIDGE_ROW, ROWS, COLS, TILE_SIZE,
    WAVE_FIRST_DELAY, WAVE_INTERVAL, WAVE_BASE_COUNT, WAVE_COUNT_GROWTH,
)
from zombie import Zombie


class Spawner:
    def __init__(self, world) -> None:
        self._timer: float = WAVE_FIRST_DELAY
        self._wave: int = 0
        # One entry point per bridge end, in world pixels
        self._entries: list[tuple[int, int]] = [
            world.grid_center(0,          BRIDGE_COL),   # top
            world.grid_center(ROWS - 1,   BRIDGE_COL),   # bottom
            world.grid_center(BRIDGE_ROW, 0),             # left
            world.grid_center(BRIDGE_ROW, COLS - 1),     # right
        ]

    def tick(self, dt: float, world) -> list[Zombie]:
        self._timer -= dt
        if self._timer > 0:
            return []
        self._timer += WAVE_INTERVAL
        self._wave += 1
        count  = WAVE_BASE_COUNT + (self._wave - 1) * WAVE_COUNT_GROWTH
        jitter = TILE_SIZE * 0.3   # spread within the bridge tile
        batch: list[Zombie] = []
        for wx, wy in self._entries:
            for _ in range(count):
                jx = random.uniform(-jitter, jitter)
                jy = random.uniform(-jitter, jitter)
                batch.append(Zombie(float(wx + jx), float(wy + jy)))
        return batch

    @property
    def seconds_to_next_wave(self) -> float:
        return max(0.0, self._timer)

    @property
    def wave(self) -> int:
        return self._wave
