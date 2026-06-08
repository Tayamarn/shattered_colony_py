"""
Tests for ScavengeCommand.

Uses real World/pathfinding but a minimal hand-crafted grid so tests are fast
and deterministic.  All BuildingData is constructed manually — no randomness.
"""

from types import SimpleNamespace
import pytest

from commands import ScavengeCommand, MoveCommand
from map_gen import BuildingData
from world import World
from tiles import Tile
from config import TILE_SIZE, SCAVENGE_DURATION

T = TILE_SIZE
_HALF = T // 2


# ── Helpers ───────────────────────────────────────────────────────────────────

def _colonist(r: int, c: int, speed: float = 80.0):
    """Colonist standing at the centre of tile (r, c)."""
    return SimpleNamespace(
        x=float(c * T + _HALF),
        y=float(r * T + _HALF),
        speed=speed,
    )


def _resources():
    earned = {}

    def earn(colonists=0, wood=0, ammo=0):
        earned['colonists'] = earned.get('colonists', 0) + colonists
        earned['wood']      = earned.get('wood',      0) + wood
        earned['ammo']      = earned.get('ammo',      0) + ammo

    ns = SimpleNamespace(earn=earn, earned=earned)
    return ns


def _building(entrance_r=0, entrance_c=1, wood=10, ammo=5,
              has_colonist=False, scavenged=False):
    """BuildingData with entrance defaulting to (0,1) — the test world's entrance."""
    return BuildingData(entrance_r=entrance_r, entrance_c=entrance_c,
                        wood=wood, ammo=ammo,
                        has_colonist=has_colonist, scavenged=scavenged)


def _small_world(extra_building_data=None):
    """
    3×4 grid:
      row 0:  STREET  STREET  BUILDING  WATER
      row 1:  STREET  STREET  STREET    WATER
      row 2:  WATER   WATER   WATER     WATER

    Building group: {(0,2)}.  Entrance: (0,1) — the street tile to the left.
    """
    S, B, W = Tile.STREET, Tile.BUILDING, Tile.WATER
    grid = [
        [S, S, B, W],
        [S, S, S, W],
        [W, W, W, W],
    ]
    bd = {(0, 2): _building(entrance_r=0, entrance_c=1)}
    if extra_building_data:
        bd.update(extra_building_data)
    return World(grid, bd)


_BUILDING_R, _BUILDING_C = 0, 2


def _cmd(world, resources=None, on_rescue=None):
    if resources is None:
        resources = _resources()
    if on_rescue is None:
        on_rescue = lambda x, y: None
    return ScavengeCommand(_BUILDING_R, _BUILDING_C, resources, on_rescue)


def _tick_until_done(cmd, colonist, world, dt=0.1, max_ticks=500):
    for _ in range(max_ticks):
        if cmd.execute(colonist, dt, world):
            return True
    return False


# ── Already adjacent ──────────────────────────────────────────────────────────

class TestAlreadyAdjacent:
    def test_completes_after_scavenge_duration(self):
        world = _small_world()
        col   = _colonist(0, 1)   # adjacent to building (0,2)
        cmd   = _cmd(world)
        # Takes SCAVENGE_DURATION seconds; using large dt to speed through
        done  = _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert done

    def test_awards_wood_on_completion(self):
        world = _small_world({(0, 2): _building(wood=7, ammo=3, entrance_r=0, entrance_c=1)})
        res   = _resources()
        col   = _colonist(0, 1)
        cmd   = ScavengeCommand(_BUILDING_R, _BUILDING_C, res, lambda x, y: None)
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert res.earned.get('wood') == 7

    def test_awards_ammo_on_completion(self):
        world = _small_world({(0, 2): _building(wood=0, ammo=4, entrance_r=0, entrance_c=1)})
        res   = _resources()
        col   = _colonist(0, 1)
        cmd   = ScavengeCommand(_BUILDING_R, _BUILDING_C, res, lambda x, y: None)
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert res.earned.get('ammo') == 4

    def test_marks_building_scavenged(self):
        world = _small_world()
        col   = _colonist(0, 1)
        cmd   = _cmd(world)
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert world.get_building(_BUILDING_R, _BUILDING_C).scavenged

    def test_colonist_does_not_move_while_working(self):
        world = _small_world()
        col   = _colonist(0, 1)
        x0, y0 = col.x, col.y
        cmd   = _cmd(world)
        # Partial work tick — not done yet
        cmd.execute(col, SCAVENGE_DURATION * 0.5, world)
        assert col.x == x0 and col.y == y0


# ── Colonist rescue callback ──────────────────────────────────────────────────

class TestRescueCallback:
    def test_on_rescue_called_when_has_colonist(self):
        world   = _small_world({(0, 2): _building(has_colonist=True, entrance_r=0, entrance_c=1)})
        rescued = []
        col     = _colonist(0, 1)
        cmd     = ScavengeCommand(
            _BUILDING_R, _BUILDING_C,
            _resources(),
            lambda x, y: rescued.append((x, y)),
        )
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert len(rescued) == 1

    def test_on_rescue_not_called_when_no_colonist(self):
        world   = _small_world({(0, 2): _building(has_colonist=False, entrance_r=0, entrance_c=1)})
        rescued = []
        col     = _colonist(0, 1)
        cmd     = ScavengeCommand(
            _BUILDING_R, _BUILDING_C,
            _resources(),
            lambda x, y: rescued.append((x, y)),
        )
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert rescued == []


# ── Already scavenged ─────────────────────────────────────────────────────────

class TestAlreadyScavenged:
    def test_no_loot_if_already_scavenged(self):
        world = _small_world({(0, 2): _building(wood=10, ammo=5, scavenged=True, entrance_r=0, entrance_c=1)})
        res   = _resources()
        col   = _colonist(0, 1)
        cmd   = ScavengeCommand(_BUILDING_R, _BUILDING_C, res, lambda x, y: None)
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert res.earned.get('wood', 0) == 0
        assert res.earned.get('ammo', 0) == 0

    def test_on_rescue_not_called_if_already_scavenged(self):
        world   = _small_world({(0, 2): _building(has_colonist=True, scavenged=True, entrance_r=0, entrance_c=1)})
        rescued = []
        col     = _colonist(0, 1)
        cmd     = ScavengeCommand(
            _BUILDING_R, _BUILDING_C,
            _resources(),
            lambda x, y: rescued.append((x, y)),
        )
        _tick_until_done(cmd, col, world, dt=SCAVENGE_DURATION)
        assert rescued == []


# ── Navigation needed ─────────────────────────────────────────────────────────

class TestNavigation:
    def test_colonist_not_done_immediately_when_far(self):
        world = _small_world()
        col   = _colonist(1, 0)   # needs to navigate to reach building
        cmd   = _cmd(world)
        # Single tiny tick should not complete the command
        done  = cmd.execute(col, 0.01, world)
        assert not done

    def test_colonist_eventually_completes_from_far(self):
        world = _small_world()
        col   = _colonist(1, 0)
        cmd   = _cmd(world)
        done  = _tick_until_done(cmd, col, world, dt=0.05, max_ticks=2000)
        assert done

    def test_loot_awarded_after_navigation(self):
        world = _small_world({(0, 2): _building(wood=9, ammo=3, entrance_r=0, entrance_c=1)})
        res   = _resources()
        col   = _colonist(1, 0)
        cmd   = ScavengeCommand(_BUILDING_R, _BUILDING_C, res, lambda x, y: None)
        _tick_until_done(cmd, col, world, dt=0.05, max_ticks=2000)
        assert res.earned.get('wood') == 9


# ── No accessible neighbor ────────────────────────────────────────────────────

class TestInaccessible:
    def test_completes_immediately_if_entrance_is_none(self):
        # BuildingData with no entrance (entrance_r=None) → command is a no-op
        grid = [
            [Tile.WATER,    Tile.WATER,    Tile.WATER],
            [Tile.WATER,    Tile.BUILDING, Tile.WATER],
            [Tile.WATER,    Tile.WATER,    Tile.WATER],
        ]
        # Explicitly no entrance
        bd = BuildingData(entrance_r=None, entrance_c=None, wood=5, ammo=2)
        world = World(grid, {(1, 1): bd})
        col   = _colonist(0, 0)
        cmd   = ScavengeCommand(1, 1, _resources(), lambda x, y: None)
        done  = cmd.execute(col, 0.1, world)
        assert done
