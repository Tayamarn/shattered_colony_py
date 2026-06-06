"""
Command tests — MoveCommand logic, no pygame needed.

Uses SimpleNamespace mocks for colonist and world so tests are pure and fast.
grid_center mirrors the real formula: (c*T + T//2, r*T + T//2).
"""

from types import SimpleNamespace
from math import sqrt
import pytest

from commands import MoveCommand
from config import TILE_SIZE, ARRIVAL_RADIUS

T = TILE_SIZE
_HALF = T // 2


def mock_world():
    def grid_center(r, c):
        return c * T + _HALF, r * T + _HALF
    return SimpleNamespace(grid_center=grid_center)


def mock_colonist(x: float, y: float, speed: float = 80.0):
    return SimpleNamespace(x=float(x), y=float(y), speed=speed)


# Centre of tile (r, c) in world pixels
def center(r: int, c: int) -> tuple[float, float]:
    return float(c * T + _HALF), float(r * T + _HALF)


WORLD = mock_world()


# ── Empty / trivial ───────────────────────────────────────────────────────────

class TestEmpty:
    def test_no_waypoints_returns_true_immediately(self):
        cmd = MoveCommand([])
        col = mock_colonist(*center(0, 0))
        assert cmd.execute(col, 0.1, WORLD) is True

    def test_no_waypoints_does_not_move_colonist(self):
        cmd = MoveCommand([])
        col = mock_colonist(100.0, 200.0)
        cmd.execute(col, 0.1, WORLD)
        assert col.x == 100.0
        assert col.y == 200.0


# ── Single waypoint ───────────────────────────────────────────────────────────

class TestSingleWaypoint:
    def test_returns_false_while_moving(self):
        cx, cy = center(0, 0)
        tx, ty = center(0, 3)            # 3 tiles to the right
        col = mock_colonist(cx, cy, speed=80.0)
        cmd = MoveCommand([(0, 3)])
        # dt=0.1 → step=8px, target is 3*T=120px away → still moving
        result = cmd.execute(col, 0.1, WORLD)
        assert result is False

    def test_colonist_moves_toward_waypoint(self):
        cx, cy = center(0, 0)
        col = mock_colonist(cx, cy, speed=80.0)
        cmd = MoveCommand([(0, 3)])
        cmd.execute(col, 0.1, WORLD)
        assert col.x > cx             # moved right

    def test_arrival_within_radius_returns_true(self):
        tx, ty = center(0, 1)
        # Place colonist just inside ARRIVAL_RADIUS of target
        col = mock_colonist(tx - ARRIVAL_RADIUS + 1, ty)
        cmd = MoveCommand([(0, 1)])
        assert cmd.execute(col, 0.1, WORLD) is True

    def test_overshoot_snaps_to_target(self):
        # dist must be > ARRIVAL_RADIUS so arrival-radius branch is NOT hit;
        # speed×dt must exceed that distance to trigger the overshoot branch.
        tx, ty = center(0, 1)
        gap = ARRIVAL_RADIUS + 2        # 8 px — just past the arrival threshold
        col = mock_colonist(tx - gap, ty, speed=1000.0)
        cmd = MoveCommand([(0, 1)])
        cmd.execute(col, 1.0, WORLD)
        assert col.x == pytest.approx(tx)
        assert col.y == pytest.approx(ty)

    def test_exact_one_step_arrival_returns_true(self):
        cx, cy = center(0, 0)
        tx, ty = center(0, 1)
        dist = tx - cx                # = T = 40
        # speed × dt exactly equals distance → snap + return True
        col = mock_colonist(cx, cy, speed=dist)
        cmd = MoveCommand([(0, 1)])
        assert cmd.execute(col, 1.0, WORLD) is True

    def test_movement_scales_with_dt(self):
        cx, cy = center(0, 0)
        col_a = mock_colonist(cx, cy, speed=80.0)
        col_b = mock_colonist(cx, cy, speed=80.0)
        MoveCommand([(0, 5)]).execute(col_a, 0.1, WORLD)
        MoveCommand([(0, 5)]).execute(col_b, 0.2, WORLD)
        assert col_b.x - cx == pytest.approx(2 * (col_a.x - cx), abs=0.01)


# ── Multiple waypoints ────────────────────────────────────────────────────────

class TestMultipleWaypoints:
    def test_returns_false_after_reaching_first_of_two(self):
        cx, cy = center(0, 0)
        tx, ty = center(0, 1)
        # Snap to first waypoint
        col = mock_colonist(cx, cy, speed=float(T))
        cmd = MoveCommand([(0, 1), (0, 2)])
        result = cmd.execute(col, 1.0, WORLD)
        assert result is False             # still has second waypoint

    def test_colonist_at_first_waypoint_after_snap(self):
        cx, cy = center(0, 0)
        tx, ty = center(0, 1)
        col = mock_colonist(cx, cy, speed=float(T))
        cmd = MoveCommand([(0, 1), (0, 2)])
        cmd.execute(col, 1.0, WORLD)
        assert col.x == pytest.approx(tx)

    def test_second_waypoint_becomes_target_on_next_tick(self):
        cx, cy = center(0, 0)
        col = mock_colonist(cx, cy, speed=float(T))
        cmd = MoveCommand([(0, 1), (0, 2)])
        cmd.execute(col, 1.0, WORLD)   # arrives at (0,1), still False
        result = cmd.execute(col, 1.0, WORLD)  # snaps to (0,2), done
        assert result is True

    def test_returns_true_when_last_waypoint_reached(self):
        cx, cy = center(0, 0)
        col = mock_colonist(cx, cy, speed=float(T))
        cmd = MoveCommand([(0, 1)])
        assert cmd.execute(col, 1.0, WORLD) is True

    def test_movement_direction_correct_for_each_waypoint(self):
        # Start at (0,0), go right to (0,2) then down to (1,2)
        cx, cy = center(0, 0)
        col = mock_colonist(cx, cy, speed=float(T))
        cmd = MoveCommand([(0, 1), (0, 2), (1, 2)])

        cmd.execute(col, 1.0, WORLD)   # arrives (0,1)
        assert col.x == pytest.approx(center(0, 1)[0])

        cmd.execute(col, 1.0, WORLD)   # arrives (0,2)
        assert col.x == pytest.approx(center(0, 2)[0])

        cmd.execute(col, 1.0, WORLD)   # arrives (1,2)
        assert col.y == pytest.approx(center(1, 2)[1])


# ── MoveIntent append behaviour (tested via colonist.orders) ─────────────────

class TestOrdersQueueBehaviour:
    """Verify the append-vs-replace logic game.py applies to colonist.orders."""

    def _colonist_with_orders(self):
        from colonist import Colonist
        from config import BRIDGE_ROW, BRIDGE_COL, TILE_SIZE
        wx = float(BRIDGE_COL * TILE_SIZE + TILE_SIZE // 2)
        wy = float(BRIDGE_ROW * TILE_SIZE + TILE_SIZE // 2)
        return Colonist(wx, wy)

    def test_replace_clears_existing_orders(self):
        col = self._colonist_with_orders()
        col.orders.append(MoveCommand([(5, 5)]))
        col.orders.clear()
        col.orders.append(MoveCommand([(6, 6)]))
        assert len(col.orders) == 1

    def test_append_adds_to_existing_orders(self):
        col = self._colonist_with_orders()
        col.orders.append(MoveCommand([(5, 5)]))
        col.orders.append(MoveCommand([(6, 6)]))
        assert len(col.orders) == 2
