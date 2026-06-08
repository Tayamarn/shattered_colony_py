"""
Map generation — no pygame dependency, fully unit-testable.

The city street network is defined as a set of horizontal and vertical
segments at irregular intervals.  Gaps of different widths between segments
produce blocks of varied shapes and sizes, avoiding a uniform grid look.
"""

import random
from dataclasses import dataclass
from typing import NamedTuple

from tiles import Tile, WALKABLE
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
    """Shared state for one connected building group."""
    entrance_r: int | None = None   # street tile where colonists must stand
    entrance_c: int | None = None
    scavenged: bool        = False
    wood: int              = 0
    ammo: int              = 0
    has_colonist: bool     = False


class MapData(NamedTuple):
    grid: list
    building_data: dict  # (r, c) → BuildingData  (multiple tiles share one object)

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

# Building subdivision — large blocks are split into smaller individual buildings
_BMIN: int = 2              # minimum building dimension (tiles per side)
_BMAX: int = 4              # maximum building dimension (tiles per side)
_SPLIT_THRESHOLD: int = 6   # connected groups larger than this get subdivided


# ── Building group helpers ────────────────────────────────────────────────────

def _flood_fill(grid: list, rows: int, cols: int, sr: int, sc: int) -> frozenset:
    """Return the connected set of BUILDING tiles reachable from (sr, sc)."""
    group: set = set()
    stack = [(sr, sc)]
    while stack:
        r, c = stack.pop()
        if (r, c) in group:
            continue
        group.add((r, c))
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows and 0 <= nc < cols
                    and grid[nr][nc] == Tile.BUILDING
                    and (nr, nc) not in group):
                stack.append((nr, nc))
    return frozenset(group)


def _make_parcels(group: frozenset, rows: int, cols: int) -> list[frozenset]:
    """
    Divide a large building group into rectangular parcels WITHOUT modifying the
    grid — no alleys are inserted.

    Strategy (two-level split):
      Wide/square blocks → split in half HORIZONTALLY first (north half / south
        half), then divide each half into vertical column strips.
      Tall blocks → split in half VERTICALLY first (west half / east half),
        then divide each half into horizontal row strips.

    Result: the north half's buildings face the north outer street; the south
    half's face the south outer street.  The two halves share a back wall —
    no walkable path exists between them.  Every parcel faces at least one
    outer street, so _find_entrance always succeeds.
    """
    if not group:
        return [group]

    rs = [r for r, c in group]
    cs = [c for r, c in group]
    r_min, r_max = min(rs), max(rs)
    c_min, c_max = min(cs), max(cs)
    block_h = r_max - r_min + 1
    block_w = c_max - c_min + 1

    parcels: list[frozenset] = []

    if block_w >= block_h:
        # Wide / square: halve horizontally, then vertical column strips per half
        r_mid = r_min + (block_h - 1) // 2
        for h_r_min, h_r_max in ((r_min, r_mid), (r_mid + 1, r_max)):
            if h_r_min > h_r_max:
                continue
            col = c_min
            while col <= c_max:
                remaining = c_max - col + 1
                if remaining < 2 * _BMIN:
                    bw = remaining
                else:
                    bw = random.randint(_BMIN, min(_BMAX, remaining - _BMIN))
                parcel = frozenset(
                    (gr, gc)
                    for gr in range(h_r_min, h_r_max + 1)
                    for gc in range(col, col + bw)
                    if (gr, gc) in group
                )
                if parcel:
                    parcels.append(parcel)
                col += bw
    else:
        # Tall: halve vertically, then horizontal row strips per half
        c_mid = c_min + (block_w - 1) // 2
        for h_c_min, h_c_max in ((c_min, c_mid), (c_mid + 1, c_max)):
            if h_c_min > h_c_max:
                continue
            row = r_min
            while row <= r_max:
                remaining = r_max - row + 1
                if remaining < 2 * _BMIN:
                    bh = remaining
                else:
                    bh = random.randint(_BMIN, min(_BMAX, remaining - _BMIN))
                parcel = frozenset(
                    (gr, gc)
                    for gr in range(row, row + bh)
                    for gc in range(h_c_min, h_c_max + 1)
                    if (gr, gc) in group
                )
                if parcel:
                    parcels.append(parcel)
                row += bh

    # Safety net: tiles outside the bounding-box column/row ranges (irregular
    # shapes) are collected into a final catch-all parcel.
    covered = frozenset().union(*parcels) if parcels else frozenset()
    remainder = group - covered
    if remainder:
        parcels.append(remainder)

    return parcels


def _find_entrance(group: frozenset, grid: list, rows: int, cols: int):
    """Return (r, c) of the best adjacent WALKABLE tile, or None."""
    best, best_score = None, -1
    for r, c in sorted(group):   # sorted for determinism across runs
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if grid[nr][nc] not in WALKABLE:
                continue
            # Prefer tiles with more walkable neighbours (less pinched corners)
            score = sum(
                1 for dr2, dc2 in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 <= nr + dr2 < rows and 0 <= nc + dc2 < cols
                and grid[nr + dr2][nc + dc2] in WALKABLE
            )
            if score > best_score:
                best_score, best = score, (nr, nc)
    return best


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

    # 6. Assign BuildingData per parcel.
    #    Large connected groups are split into wall-sharing parcels via
    #    _make_parcels (no alleys added to the grid).  Each parcel gets its own
    #    BuildingData so they are separate scavenge targets.
    building_data: dict[tuple[int, int], BuildingData] = {}
    visited: set[tuple[int, int]] = set()

    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] != Tile.BUILDING or (r, c) in visited:
                continue
            group    = _flood_fill(grid, ROWS, COLS, r, c)
            visited |= group
            parcels  = _make_parcels(group, ROWS, COLS) if len(group) > _SPLIT_THRESHOLD else [group]
            group_entrance = _find_entrance(group, grid, ROWS, COLS)
            for parcel in parcels:
                entrance = _find_entrance(parcel, grid, ROWS, COLS) or group_entrance
                bd = BuildingData(
                    entrance_r   = entrance[0] if entrance else None,
                    entrance_c   = entrance[1] if entrance else None,
                    wood         = random.randint(LOOT_WOOD_MIN, LOOT_WOOD_MAX),
                    ammo         = random.randint(LOOT_AMMO_MIN, LOOT_AMMO_MAX),
                    has_colonist = random.random() < LOOT_COLONIST_CHANCE,
                )
                for tr, tc in parcel:
                    building_data[(tr, tc)] = bd

    return MapData(grid, building_data)
