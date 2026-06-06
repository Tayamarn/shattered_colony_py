"""
Pathfinding tests — all run on small hand-crafted grids.

Using real World objects (not mocks) so the full tile_at / bounds logic
runs, but the grids are tiny and deterministic so tests are fast and
independent of map_gen changes.

Grid notation used in make_world():
  '.' = STREET  (walkable)
  '#' = BUILDING (not walkable)
  'W' = WATER   (not walkable)
"""

from __future__ import annotations
from math import sqrt
import pytest

from tiles import Tile, WALKABLE
from world import World
from pathfinding import find_path


# ── Helpers ───────────────────────────────────────────────────────────────────

_CHAR = {'.': Tile.STREET, '#': Tile.BUILDING, 'W': Tile.WATER}

def make_world(rows: list[str]) -> World:
    grid = [[_CHAR[ch] for ch in row] for row in rows]
    return World(grid)

def path_is_valid(world: World, start_r: int, start_c: int, path: list) -> bool:
    """Structural invariants every returned path must satisfy."""
    if not path:
        return True
    # Start not in path
    if path[0] == (start_r, start_c):
        return False
    # All tiles walkable
    if any(world.tile_at(r, c) not in WALKABLE for r, c in path):
        return False
    # Consecutive steps are 8-directionally adjacent
    steps = [(start_r, start_c)] + path
    for (r0, c0), (r1, c1) in zip(steps, steps[1:]):
        if max(abs(r1 - r0), abs(c1 - c0)) != 1:
            return False
    return True


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_start_equals_goal_returns_empty(self):
        w = make_world(["..."])
        assert find_path(w, 0, 0, 0, 0) == []

    def test_goal_not_walkable_returns_empty(self):
        w = make_world(["..#"])
        assert find_path(w, 0, 0, 0, 2) == []

    def test_no_path_returns_empty(self):
        # Middle row is a solid wall — (0,0) and (2,0) are in separate regions
        w = make_world([".....", "#####", "....."])
        assert find_path(w, 0, 0, 2, 0) == []

    def test_goal_out_of_bounds_returns_empty(self):
        w = make_world(["..."])
        assert find_path(w, 0, 0, 5, 5) == []

    def test_single_step_horizontal(self):
        w = make_world([".."])
        path = find_path(w, 0, 0, 0, 1)
        assert path == [(0, 1)]

    def test_single_step_vertical(self):
        w = make_world([".", "."])
        path = find_path(w, 0, 0, 1, 0)
        assert path == [(1, 0)]

    def test_single_step_diagonal(self):
        w = make_world(["..", ".."])
        path = find_path(w, 0, 0, 1, 1)
        assert path == [(1, 1)]


# ── Path structure ────────────────────────────────────────────────────────────

class TestPathStructure:
    def test_start_excluded_from_path(self):
        w = make_world(["...."])
        path = find_path(w, 0, 0, 0, 3)
        assert (0, 0) not in path

    def test_goal_included_in_path(self):
        w = make_world(["...."])
        path = find_path(w, 0, 0, 0, 3)
        assert path[-1] == (0, 3)

    def test_all_tiles_walkable(self):
        w = make_world([".....", ".....", "....."])
        path = find_path(w, 0, 0, 2, 4)
        assert all(w.tile_at(r, c) in WALKABLE for r, c in path)

    def test_consecutive_steps_adjacent(self):
        w = make_world([".....", ".....", "....."])
        path = find_path(w, 0, 0, 2, 4)
        steps = [(0, 0)] + path
        for (r0, c0), (r1, c1) in zip(steps, steps[1:]):
            assert max(abs(r1 - r0), abs(c1 - c0)) == 1

    def test_path_validity_on_open_grid(self):
        w = make_world([".....", ".....", "....."])
        path = find_path(w, 0, 0, 2, 4)
        assert path_is_valid(w, 0, 0, path)


# ── Obstacle avoidance ────────────────────────────────────────────────────────

class TestObstacleAvoidance:
    def test_routes_around_wall(self):
        # Gap in wall at right end — path must go through (1,4)
        w = make_world([
            ".....",
            "####.",
            ".....",
        ])
        path = find_path(w, 0, 0, 2, 0)
        assert path is not None
        assert path[-1] == (2, 0)
        assert path_is_valid(w, 0, 0, path)

    def test_avoids_non_walkable_tiles(self):
        w = make_world([
            ".#.",
            "...",
            ".#.",
        ])
        path = find_path(w, 0, 0, 2, 2)
        assert all(w.tile_at(r, c) in WALKABLE for r, c in path)
        assert path[-1] == (2, 2)


# ── Diagonal corner-cut rule ─────────────────────────────────────────────────

class TestDiagonalCornerCut:
    def test_diagonal_blocked_by_bottom_left_wall(self):
        # Going from (0,0) diagonally to (1,1):
        # cardinal neighbour (1,0) = '#' → diagonal must be blocked.
        # Path must detour via (0,1)→(1,1).
        w = make_world(["..", "#."])
        path = find_path(w, 0, 0, 1, 1)
        assert (1, 1) == path[-1]
        assert (1, 0) not in path          # wall tile never in path
        steps = [(0, 0)] + path
        # Verify no step goes directly from (0,0) to (1,1)
        for (r0, c0), (r1, c1) in zip(steps, steps[1:]):
            assert not ((r0, c0) == (0, 0) and (r1, c1) == (1, 1)), \
                "Diagonal corner cut must be blocked"

    def test_diagonal_blocked_by_top_right_wall(self):
        # (0,1) = '#', going from (0,0) diagonally to (1,1) blocked.
        w = make_world([".#", ".."])
        path = find_path(w, 0, 0, 1, 1)
        assert path[-1] == (1, 1)
        steps = [(0, 0)] + path
        for (r0, c0), (r1, c1) in zip(steps, steps[1:]):
            assert not ((r0, c0) == (0, 0) and (r1, c1) == (1, 1))

    def test_diagonal_allowed_when_both_cardinals_clear(self):
        # No walls adjacent to the diagonal — should take direct diagonal step.
        w = make_world(["..", ".."])
        path = find_path(w, 0, 0, 1, 1)
        assert path == [(1, 1)]            # single diagonal step


# ── Optimality ────────────────────────────────────────────────────────────────

class TestOptimality:
    def test_straight_path_length(self):
        # 1×5 grid — straight horizontal path has 4 steps
        w = make_world(["....." ])
        path = find_path(w, 0, 0, 0, 4)
        assert len(path) == 4

    def test_diagonal_path_shorter_than_manhattan(self):
        # 3×3 open grid — optimal (0,0)→(2,2) takes 2 diagonal steps
        w = make_world(["...", "...", "..."])
        path = find_path(w, 0, 0, 2, 2)
        assert len(path) == 2   # two diagonal steps

    def test_cost_preferred_over_longer_detour(self):
        # Two routes: short straight (cols 0→4, row 0) and long detour via row 1.
        # Straight route should be found.
        w = make_world([
            ".....",
            ".....",
        ])
        path = find_path(w, 0, 0, 0, 4)
        # Optimal is straight along row 0, length 4
        assert len(path) == 4
        assert all(r == 0 for r, c in path)


# ── Integration: generated map ────────────────────────────────────────────────

class TestOnGeneratedMap:
    """Sanity checks using the real island map."""

    def test_path_across_island_is_valid(self, world):
        from config import BRIDGE_ROW, BRIDGE_COL
        # Path along the main E-W boulevard (all STREET)
        path = find_path(world, BRIDGE_ROW, BRIDGE_COL - 4, BRIDGE_ROW, BRIDGE_COL + 4)
        assert path, "Path along boulevard must exist"
        assert path[-1] == (BRIDGE_ROW, BRIDGE_COL + 4)
        assert path_is_valid(world, BRIDGE_ROW, BRIDGE_COL - 4, path)

    def test_bridge_to_bridge_path_exists(self, world):
        from config import BRIDGE_ROW, BRIDGE_COL
        # Path from top bridge entrance to bottom bridge entrance
        path = find_path(world, 0, BRIDGE_COL, BRIDGE_ROW, BRIDGE_COL)
        assert path, "Must be able to reach island centre from top bridge"
        assert path[-1] == (BRIDGE_ROW, BRIDGE_COL)
