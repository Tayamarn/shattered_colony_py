"""
Tests for the World class.

Covers tile access (in-bounds, out-of-bounds, pixel-based), coordinate
helpers (pixel_to_grid / grid_center), and passability queries.
"""

import pytest
from map_gen import generate
from world import World
from tiles import Tile, WALKABLE
from config import TILE_SIZE, BRIDGE_COL, BRIDGE_ROW, COLS, ROWS


@pytest.fixture(scope="module")
def world():
    md = generate()
    return World(md.grid, md.building_data)


# ── tile_at ───────────────────────────────────────────────────────────────────

class TestTileAt:
    def test_returns_water_for_negative_row(self, world):
        assert world.tile_at(-1, 0) == Tile.WATER

    def test_returns_water_for_negative_col(self, world):
        assert world.tile_at(0, -1) == Tile.WATER

    def test_returns_water_for_row_too_large(self, world):
        assert world.tile_at(ROWS, 0) == Tile.WATER

    def test_returns_water_for_col_too_large(self, world):
        assert world.tile_at(0, COLS) == Tile.WATER

    def test_bridge_intersection_is_street(self, world):
        assert world.tile_at(BRIDGE_ROW, BRIDGE_COL) == Tile.STREET

    def test_top_left_corner_is_water(self, world):
        assert world.tile_at(0, 0) == Tile.WATER


# ── tile_at_pixel ─────────────────────────────────────────────────────────────

class TestTileAtPixel:
    def test_centre_of_tile_matches_tile_at(self, world):
        wx, wy = world.grid_center(BRIDGE_ROW, BRIDGE_COL)
        assert world.tile_at_pixel(wx, wy) == world.tile_at(BRIDGE_ROW, BRIDGE_COL)

    def test_pixel_at_tile_boundary_belongs_to_next_tile(self, world):
        # Exact boundary pixel (c * TILE_SIZE, 0) maps to col c, not c-1
        assert world.tile_at_pixel(TILE_SIZE, 0) == world.tile_at(0, 1)

    def test_negative_pixel_returns_water(self, world):
        assert world.tile_at_pixel(-1, 0) == Tile.WATER
        assert world.tile_at_pixel(0, -1) == Tile.WATER


# ── pixel_to_grid / grid_center ───────────────────────────────────────────────

class TestCoordinateHelpers:
    def test_grid_center_of_origin_tile(self, world):
        wx, wy = world.grid_center(0, 0)
        assert wx == TILE_SIZE // 2
        assert wy == TILE_SIZE // 2

    def test_grid_center_round_trips_through_pixel_to_grid(self, world):
        for r, c in [(0, 0), (BRIDGE_ROW, BRIDGE_COL), (ROWS - 1, COLS - 1)]:
            wx, wy = world.grid_center(r, c)
            gr, gc = world.pixel_to_grid(wx, wy)
            assert (gr, gc) == (r, c), \
                f"Round-trip failed for ({r},{c}): got ({gr},{gc})"

    def test_pixel_to_grid_top_left_of_tile(self, world):
        # Top-left corner of tile (2, 3) is (3*T, 2*T)
        r, c = world.pixel_to_grid(3 * TILE_SIZE, 2 * TILE_SIZE)
        assert (r, c) == (2, 3)

    def test_grid_center_x_increases_with_col(self, world):
        wx0, _ = world.grid_center(0, 0)
        wx1, _ = world.grid_center(0, 1)
        assert wx1 > wx0

    def test_grid_center_y_increases_with_row(self, world):
        _, wy0 = world.grid_center(0, 0)
        _, wy1 = world.grid_center(1, 0)
        assert wy1 > wy0


# ── is_passable ───────────────────────────────────────────────────────────────

class TestIsPassable:
    def test_bridge_centre_is_passable(self, world):
        wx, wy = world.grid_center(BRIDGE_ROW, BRIDGE_COL)
        assert world.is_passable(wx, wy, margin=4)

    def test_water_corner_is_not_passable(self, world):
        wx, wy = world.grid_center(0, 0)
        assert not world.is_passable(wx, wy, margin=4)

    def test_building_tile_is_not_passable(self, world):
        building_pos = next(
            (r, c)
            for r in range(ROWS) for c in range(COLS)
            if world.tile_at(r, c) == Tile.BUILDING
        )
        wx, wy = world.grid_center(*building_pos)
        assert not world.is_passable(wx, wy, margin=4)

    def test_margin_zero_only_checks_centre_point(self, world):
        # With margin=0, a street tile's centre must pass
        wx, wy = world.grid_center(BRIDGE_ROW, BRIDGE_COL)
        assert world.is_passable(wx, wy, margin=0)

    def test_large_margin_detects_nearby_obstacle(self, world):
        # Standing in the middle of a 1-tile-wide bridge with a huge margin
        # should hit water on either side and fail
        bridge_r = BRIDGE_ROW
        # Find the leftmost bridge tile on bridge row
        left_bridge_c = next(
            c for c in range(COLS) if world.tile_at(bridge_r, c) == Tile.BRIDGE
        )
        wx, wy = world.grid_center(bridge_r, left_bridge_c)
        # margin large enough to reach the water tile to the left
        assert not world.is_passable(wx, wy, margin=TILE_SIZE)


# ── world dimensions ──────────────────────────────────────────────────────────

class TestDimensions:
    def test_pixel_dimensions_match_config(self, world):
        assert world.pixel_w == COLS * TILE_SIZE
        assert world.pixel_h == ROWS * TILE_SIZE

    def test_cols_and_rows_match_config(self, world):
        assert world.cols == COLS
        assert world.rows == ROWS


# ── get_building ──────────────────────────────────────────────────────────────

class TestGetBuilding:
    def test_returns_none_for_street_tile(self, world):
        assert world.get_building(BRIDGE_ROW, BRIDGE_COL) is None

    def test_returns_building_data_for_building_tile(self, world):
        # Find any BUILDING tile on the map
        r, c = next(
            (r, c)
            for r in range(ROWS) for c in range(COLS)
            if world.tile_at(r, c) == Tile.BUILDING
        )
        bd = world.get_building(r, c)
        assert bd is not None

    def test_building_data_starts_unscavenged(self, world):
        r, c = next(
            (r, c)
            for r in range(ROWS) for c in range(COLS)
            if world.tile_at(r, c) == Tile.BUILDING
        )
        assert not world.get_building(r, c).scavenged

    def test_returns_none_when_no_building_data_provided(self):
        grid = [[Tile.BUILDING]]
        w = World(grid)   # no building_data arg
        assert w.get_building(0, 0) is None


# ── has_los ───────────────────────────────────────────────────────────────────

class TestHasLos:
    def _los_world(self):
        """
        Row 0:  STREET  BUILDING  STREET
        Row 1:  STREET  STREET    STREET
        """
        S, B = Tile.STREET, Tile.BUILDING
        return World([[S, B, S], [S, S, S]])

    def test_clear_line_returns_true(self):
        w = self._los_world()
        wx0, wy0 = w.grid_center(0, 0)
        wx1, wy1 = w.grid_center(1, 0)
        assert w.has_los(wx0, wy0, wx1, wy1)

    def test_building_in_path_returns_false(self):
        w = self._los_world()
        # Horizontal line from (0,0) to (0,2) passes through (0,1) = BUILDING
        wx0, wy0 = w.grid_center(0, 0)
        wx1, wy1 = w.grid_center(0, 2)
        assert not w.has_los(wx0, wy0, wx1, wy1)

    def test_same_tile_returns_true(self):
        w = self._los_world()
        wx, wy = w.grid_center(0, 0)
        assert w.has_los(wx, wy, wx, wy)

    def test_diagonal_clear_path_returns_true(self):
        # All-street grid — diagonal from corner to corner has no buildings
        S = Tile.STREET
        w = World([[S] * 5 for _ in range(5)])
        wx0, wy0 = w.grid_center(0, 0)
        wx1, wy1 = w.grid_center(4, 4)
        assert w.has_los(wx0, wy0, wx1, wy1)
