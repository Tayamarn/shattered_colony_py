"""
Tests for map_gen.generate().

All tests are structural — they verify invariants that the rest of the game
relies on (bridge continuity, park accessibility, grid dimensions) rather
than specific tile positions, so they stay valid as the map layout evolves.
"""

import pytest
from map_gen import generate, PARK_CENTERS, PARK_RADIUS, BuildingData, MapData
from tiles import Tile, WALKABLE
from config import ROWS, COLS, BRIDGE_COL, BRIDGE_ROW


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def map_data():
    return generate()

@pytest.fixture(scope="module")
def grid(map_data):
    return map_data.grid


def _cardinal_neighbours(r, c):
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            yield nr, nc


# ── Dimensions ────────────────────────────────────────────────────────────────

def test_grid_has_correct_row_count(grid):
    assert len(grid) == ROWS


def test_grid_has_correct_col_count(grid):
    assert all(len(row) == COLS for row in grid)


def test_all_tile_values_are_known(grid):
    valid = set(Tile)
    for r, row in enumerate(grid):
        for c, tile in enumerate(row):
            assert tile in valid, f"Unknown tile value {tile!r} at ({r},{c})"


# ── Island ────────────────────────────────────────────────────────────────────

def test_island_exists(grid):
    non_water = sum(1 for row in grid for t in row if t != Tile.WATER)
    assert non_water > 0


def test_corners_are_water(grid):
    assert grid[0][0]           == Tile.WATER
    assert grid[0][COLS - 1]    == Tile.WATER
    assert grid[ROWS - 1][0]    == Tile.WATER
    assert grid[ROWS - 1][COLS - 1] == Tile.WATER


# ── Bridges ───────────────────────────────────────────────────────────────────

def test_bridge_col_contains_no_buildings(grid):
    """A BUILDING anywhere on the bridge column would cut off top or bottom bridge."""
    for r in range(ROWS):
        assert grid[r][BRIDGE_COL] != Tile.BUILDING, \
            f"BUILDING blocks bridge column at row {r}"


def test_bridge_row_contains_no_buildings(grid):
    for c in range(COLS):
        assert grid[BRIDGE_ROW][c] != Tile.BUILDING, \
            f"BUILDING blocks bridge row at col {c}"


def test_top_bridge_exists(grid):
    assert any(grid[r][BRIDGE_COL] == Tile.BRIDGE for r in range(ROWS // 2))


def test_bottom_bridge_exists(grid):
    assert any(grid[r][BRIDGE_COL] == Tile.BRIDGE for r in range(ROWS // 2, ROWS))


def test_left_bridge_exists(grid):
    assert any(grid[BRIDGE_ROW][c] == Tile.BRIDGE for c in range(COLS // 2))


def test_right_bridge_exists(grid):
    assert any(grid[BRIDGE_ROW][c] == Tile.BRIDGE for c in range(COLS // 2, COLS))


def test_every_bridge_tile_neighbours_a_walkable_tile(grid):
    """No bridge tile should be isolated — each must touch another BRIDGE or STREET."""
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] != Tile.BRIDGE:
                continue
            neighbours = [grid[nr][nc] for nr, nc in _cardinal_neighbours(r, c)]
            assert any(t in (Tile.BRIDGE, Tile.STREET) for t in neighbours), \
                f"Isolated BRIDGE tile at ({r},{c}) — no walkable cardinal neighbour"


# ── Parks ─────────────────────────────────────────────────────────────────────

def test_parks_exist(grid):
    assert any(t == Tile.PARK for row in grid for t in row)


@pytest.mark.parametrize("pr,pc", PARK_CENTERS)
def test_park_patch_has_street_entrance(grid, pr, pc):
    """
    Every park patch must have at least one PARK tile that is cardinally
    adjacent to a STREET tile, guaranteeing a reachable entrance.
    """
    found_entrance = False
    for dr in range(-PARK_RADIUS, PARK_RADIUS + 1):
        for dc in range(-PARK_RADIUS, PARK_RADIUS + 1):
            r, c = pr + dr, pc + dc
            if not (0 <= r < ROWS and 0 <= c < COLS):
                continue
            if grid[r][c] != Tile.PARK:
                continue
            if any(grid[nr][nc] == Tile.STREET for nr, nc in _cardinal_neighbours(r, c)):
                found_entrance = True
    assert found_entrance, \
        f"Park centred at ({pr},{pc}) has no PARK tile adjacent to a STREET"


# ── MapData / BuildingData ────────────────────────────────────────────────────

def test_generate_returns_map_data(map_data):
    assert isinstance(map_data, MapData)

def test_building_data_keys_are_building_tiles(map_data):
    grid = map_data.grid
    for (r, c) in map_data.building_data:
        assert grid[r][c] == Tile.BUILDING, \
            f"building_data entry at ({r},{c}) but tile is {grid[r][c]!r}"

def test_every_building_tile_has_data(map_data):
    grid = map_data.grid
    bd   = map_data.building_data
    for r, row in enumerate(grid):
        for c, tile in enumerate(row):
            if tile == Tile.BUILDING:
                assert (r, c) in bd, f"BUILDING at ({r},{c}) missing from building_data"

def test_building_data_wood_in_range(map_data):
    from config import LOOT_WOOD_MIN, LOOT_WOOD_MAX
    for bd in map_data.building_data.values():
        assert LOOT_WOOD_MIN <= bd.wood <= LOOT_WOOD_MAX

def test_building_data_ammo_in_range(map_data):
    from config import LOOT_AMMO_MIN, LOOT_AMMO_MAX
    for bd in map_data.building_data.values():
        assert LOOT_AMMO_MIN <= bd.ammo <= LOOT_AMMO_MAX

def test_building_data_not_scavenged_on_start(map_data):
    assert all(not bd.scavenged for bd in map_data.building_data.values())
