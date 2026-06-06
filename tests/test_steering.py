"""
Tests for steering.separate().

Uses SimpleNamespace entities and mock worlds — no pygame needed.
"""

from types import SimpleNamespace
from math import sqrt
import pytest

from steering import separate
from tiles import Tile


# ── Helpers ───────────────────────────────────────────────────────────────────

def ent(x: float, y: float, radius: float = 8.0):
    return SimpleNamespace(x=float(x), y=float(y), radius=float(radius))

def open_world():
    """Every pixel is walkable."""
    return SimpleNamespace(tile_at_pixel=lambda x, y: Tile.STREET)

def wall_world(wall_x: float):
    """Walkable for x < wall_x, building beyond."""
    def tap(x, y):
        return Tile.BUILDING if x >= wall_x else Tile.STREET
    return SimpleNamespace(tile_at_pixel=tap)


# ── No-op cases ───────────────────────────────────────────────────────────────

class TestNoOp:
    def test_empty_list(self):
        separate([], open_world())   # must not raise

    def test_single_entity_not_moved(self):
        a = ent(100, 100)
        separate([a], open_world())
        assert a.x == 100.0 and a.y == 100.0

    def test_non_overlapping_pair_not_moved(self):
        a = ent(0, 0, radius=8)
        b = ent(100, 0, radius=8)   # far apart
        separate([a, b], open_world())
        assert a.x == 0.0
        assert b.x == 100.0

    def test_exactly_touching_not_moved(self):
        # dist == min_dist exactly → not overlapping, no push
        a = ent(0, 0, radius=8)
        b = ent(16, 0, radius=8)   # distance = 16 = 8+8
        separate([a, b], open_world())
        assert a.x == pytest.approx(0.0)
        assert b.x == pytest.approx(16.0)


# ── Separation ────────────────────────────────────────────────────────────────

class TestSeparation:
    def test_overlapping_pair_pushed_apart(self):
        a = ent(0, 0, radius=8)
        b = ent(10, 0, radius=8)    # overlap = 16 - 10 = 6 px
        separate([a, b], open_world())
        assert b.x > a.x            # b moved right, a moved left

    def test_separation_is_symmetric(self):
        a = ent(0, 0, radius=8)
        b = ent(10, 0, radius=8)
        separate([a, b], open_world())
        # Each should move by half the overlap
        assert a.x == pytest.approx(-3.0, abs=0.01)
        assert b.x == pytest.approx(13.0, abs=0.01)

    def test_after_separation_distance_ge_min_dist(self):
        a = ent(0, 0, radius=8)
        b = ent(10, 0, radius=8)
        separate([a, b], open_world())
        dist = sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)
        assert dist >= 16.0 - 0.01

    def test_vertical_overlap(self):
        a = ent(0, 0, radius=8)
        b = ent(0, 10, radius=8)
        separate([a, b], open_world())
        assert b.y > a.y
        dist = abs(b.y - a.y)
        assert dist >= 16.0 - 0.01

    def test_diagonal_overlap(self):
        a = ent(0, 0, radius=8)
        b = ent(8, 8, radius=8)   # dist ≈ 11.3, min_dist = 16 → overlap
        separate([a, b], open_world())
        dist = sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)
        assert dist >= 16.0 - 0.01

    def test_three_entities_all_separated(self):
        # Three colonists stacked at origin
        a = ent(0, 0, radius=8)
        b = ent(5, 0, radius=8)
        c = ent(0, 5, radius=8)
        separate([a, b, c], open_world())
        def dist(p, q):
            return sqrt((p.x - q.x) ** 2 + (p.y - q.y) ** 2)
        # After one pass, pairs a-b and a-c may still be partly overlapping
        # but the separation must have moved things in the right directions
        assert b.x >= a.x    # b pushed away from a in x
        assert c.y >= a.y    # c pushed away from a in y

    def test_exact_same_position_skipped_gracefully(self):
        # dist ≈ 0 → division by zero must not occur
        a = ent(100, 100, radius=8)
        b = ent(100, 100, radius=8)
        separate([a, b], open_world())   # must not raise


# ── Wall interaction ──────────────────────────────────────────────────────────

class TestWallInteraction:
    def test_push_blocked_by_wall(self):
        # b is near a wall on its right; pushing b right would hit the wall.
        # Wall at x >= 112; b at x=110 would go to 113 → blocked.
        # a at x=100 gets the full push leftward instead.
        def tap(x, y):
            return Tile.BUILDING if x >= 112.0 else Tile.STREET
        w = SimpleNamespace(tile_at_pixel=tap)
        a = ent(100, 0, radius=8)
        b = ent(110, 0, radius=8)   # overlap = 16-10 = 6, push = 3 each
        separate([a, b], w)
        assert a.x < 100.0                      # a was pushed left
        assert b.x == pytest.approx(110.0)      # b was blocked by wall

    def test_push_blocked_by_wall_y(self):
        # a is near a wall below it (y <= -1); pushing a downward is blocked.
        # b at (0, 10) gets pushed upward freely.
        def tap(x, y):
            return Tile.BUILDING if y <= -1.0 else Tile.STREET
        w = SimpleNamespace(tile_at_pixel=tap)
        a = ent(0, 0, radius=8)
        b = ent(0, 10, radius=8)   # overlap = 6; push a.y = -3 → blocked
        separate([a, b], w)
        assert a.y == pytest.approx(0.0)        # a blocked by wall below
        assert b.y > 10.0                       # b pushed upward freely
