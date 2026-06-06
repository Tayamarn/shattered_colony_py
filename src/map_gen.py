"""
Map generation — no pygame dependency, fully unit-testable.

The city street network is defined as a set of horizontal and vertical
segments at irregular intervals.  Gaps of different widths between segments
produce blocks of varied shapes and sizes, avoiding a uniform grid look.
"""

import random
from dataclasses import dataclass
from typing import NamedTuple

from tiles import Tile
from config import (
    COLS, ROWS,
    ISLAND_CX, ISLAND_CY, ISLAND_RX, ISLAND_RY,
    BRIDGE_COL, BRIDGE_ROW,
    LOOT_WOOD_MIN, LOOT_WOOD_MAX,
    LOOT_AMMO_MIN, LOOT_AMMO_MAX,
    LOOT_COLONIST_CHANCE,
)


@dataclass
class BuildingData:
    """Per-building state and pre-rolled loot."""
    scavenged: bool = False
    wood: int = 0
    ammo: int = 0
    has_colonist: bool = False


class MapData(NamedTuple):
    grid: list
    building_data: dict  # (r, c) → BuildingData

# ── Street network ────────────────────────────────────────────────────────────
# Horizontal segments: (row, col_start, col_end)  — inclusive on both ends
H_SEGS: list[tuple[int, int, int]] = [
    ( 8, 10, 41),   # northern border road
    (12, 10, 21),   # NW short connector  →  T-intersection at cols 10 & 21
    (16, 10, 41),   # mid-north road
    (20,  7, 43),   # main E-W boulevard  (= BRIDGE_ROW)
    (24, 10, 41),   # mid-south road
    (29, 10, 41),   # southern road
    (33, 10, 41),   # southern border road
]

# Vertical segments: (col, row_start, row_end)  — inclusive on both ends
V_SEGS: list[tuple[int, int, int]] = [
    (10,  8, 33),   # west artery
    (14,  8, 33),   # W-inner artery
    (21,  8, 33),   # central artery
    (25,  5, 35),   # main N-S boulevard  (= BRIDGE_COL)
    (31, 20, 33),   # SE stub — south half only
    (33,  8, 20),   # NE stub — north half only
    (36,  8, 33),   # E-inner artery
    (41,  8, 33),   # east artery
]

# Park centres — each placed so that at least one street tile directly borders
# the park patch (guaranteeing a reachable entrance).
PARK_CENTERS: list[tuple[int, int]] = [
    (10, 17),   # NW:  row 8 street to north, row 12 to south, col 14 to west
    (10, 29),   # NE:  row 8 street to north (only entrance — large block)
    (26, 12),   # SW:  rows 24/29 + cols 10/14 surround it on all sides
    (25, 38),   # SE:  row 24 to north, col 36 to west, col 41 to east
]
PARK_RADIUS: int = 2   # half-size of each park patch (creates a 5×5 area)


# ── Generator ─────────────────────────────────────────────────────────────────

def _on_island(r: int, c: int) -> bool:
    return (
        ((c - ISLAND_CX) / ISLAND_RX) ** 2
        + ((r - ISLAND_CY) / ISLAND_RY) ** 2
    ) <= 1.0


def generate() -> MapData:
    """Return a fresh MapData(grid, building_data) for the island."""
    grid: list[list[Tile]] = [[Tile.WATER] * COLS for _ in range(ROWS)]

    # 1. Fill the elliptical island with buildings as the default land tile
    for r in range(ROWS):
        for c in range(COLS):
            if _on_island(r, c):
                grid[r][c] = Tile.BUILDING

    # 2. Carve street segments into land
    streets: set[tuple[int, int]] = set()
    for row, c0, c1 in H_SEGS:
        for c in range(c0, c1 + 1):
            streets.add((row, c))
    for col, r0, r1 in V_SEGS:
        for r in range(r0, r1 + 1):
            streets.add((r, col))

    for r, c in streets:
        if 0 <= r < ROWS and 0 <= c < COLS and grid[r][c] == Tile.BUILDING:
            grid[r][c] = Tile.STREET

    # 3. Guarantee the bridge axes have no building gaps at the island edge
    #    (segments may stop 1-2 tiles short of the water due to ellipse clipping)
    for r in range(ROWS):
        if grid[r][BRIDGE_COL] == Tile.BUILDING:
            grid[r][BRIDGE_COL] = Tile.STREET
    for c in range(COLS):
        if grid[BRIDGE_ROW][c] == Tile.BUILDING:
            grid[BRIDGE_ROW][c] = Tile.STREET

    # 4. Place parks (only replace building tiles, never streets)
    rad = PARK_RADIUS
    for pr, pc in PARK_CENTERS:
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                r, c = pr + dr, pc + dc
                if 0 <= r < ROWS and 0 <= c < COLS and grid[r][c] == Tile.BUILDING:
                    grid[r][c] = Tile.PARK

    # 5. Extend the bridge axes over water to the map edges
    for r in range(ROWS):
        if grid[r][BRIDGE_COL] == Tile.WATER:
            grid[r][BRIDGE_COL] = Tile.BRIDGE
    for c in range(COLS):
        if grid[BRIDGE_ROW][c] == Tile.WATER:
            grid[BRIDGE_ROW][c] = Tile.BRIDGE

    # 6. Pre-roll loot for every building tile
    building_data: dict[tuple[int, int], BuildingData] = {}
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] == Tile.BUILDING:
                building_data[(r, c)] = BuildingData(
                    wood=random.randint(LOOT_WOOD_MIN, LOOT_WOOD_MAX),
                    ammo=random.randint(LOOT_AMMO_MIN, LOOT_AMMO_MAX),
                    has_colonist=random.random() < LOOT_COLONIST_CHANCE,
                )

    return MapData(grid, building_data)
