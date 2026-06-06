"""
Tests for Zombie — pursuit AI, wall-slide movement, melee attack.

Uses minimal hand-crafted worlds so tests are pure and fast.
Colonist / world objects are SimpleNamespace mocks unless a real World is
needed for tile-aware slide tests.
"""

from types import SimpleNamespace
from math import sqrt
import pytest

from zombie import Zombie
from world import World
from tiles import Tile
from config import (
    TILE_SIZE, ZOMBIE_HP, ZOMBIE_SPEED,
    ZOMBIE_DAMAGE, ZOMBIE_ATTACK_RATE, ZOMBIE_ATTACK_REACH, ZOMBIE_RADIUS,
    COLONIST_RADIUS,
)

T = TILE_SIZE
_H = T // 2


def _colonist(x, y, alive=True):
    dmg = []
    def take_damage(amount):
        dmg.append(amount)
        col.hp = max(0, col.hp - amount)
        if col.hp <= 0:
            col.alive = False
    col = SimpleNamespace(
        x=float(x), y=float(y),
        alive=alive,
        radius=COLONIST_RADIUS,
        hp=100, max_hp=100,
        take_damage=take_damage,
        damage_log=dmg,
    )
    return col


def _all_street_world(rows=5, cols=5):
    """A world where every tile is STREET — zombies can move anywhere."""
    grid = [[Tile.STREET] * cols for _ in range(rows)]
    return World(grid)


def _wall_world():
    """
    3×3:  STREET BUILDING STREET
          STREET STREET   STREET
          STREET BUILDING STREET

    Zombie at (1,0), colonist at (1,2).
    Direct path (through BUILDING at (0,1)/(2,1)) is blocked.
    Zombie should slide through the middle row.
    """
    S, B = Tile.STREET, Tile.BUILDING
    grid = [
        [S, B, S],
        [S, S, S],
        [S, B, S],
    ]
    return World(grid)


# ── Construction ──────────────────────────────────────────────────────────────

def test_zombie_starts_alive():
    z = Zombie(0.0, 0.0)
    assert z.alive

def test_zombie_hp_equals_config():
    z = Zombie(0.0, 0.0)
    assert z.hp == ZOMBIE_HP

def test_zombie_radius_equals_config():
    z = Zombie(0.0, 0.0)
    assert z.radius == ZOMBIE_RADIUS


# ── Pursuit movement ──────────────────────────────────────────────────────────

class TestPursuit:
    def test_zombie_moves_toward_colonist(self):
        world = _all_street_world()
        z = Zombie(float(_H), float(_H))           # tile (0,0) centre
        col = _colonist(4 * T + _H, _H)            # tile (0,4) centre, far right
        z.tick(0.1, world, [col])
        assert z.x > _H   # moved right

    def test_zombie_does_not_move_with_no_colonists(self):
        world = _all_street_world()
        z = Zombie(float(2 * T + _H), float(2 * T + _H))
        x0, y0 = z.x, z.y
        z.tick(0.1, world, [])
        assert z.x == x0 and z.y == y0

    def test_zombie_ignores_dead_colonist(self):
        world = _all_street_world()
        z = Zombie(float(_H), float(_H))
        dead = _colonist(4 * T + _H, _H, alive=False)
        x0, y0 = z.x, z.y
        z.tick(0.1, world, [dead])
        assert z.x == x0 and z.y == y0

    def test_zombie_targets_nearest_of_two_colonists(self):
        world = _all_street_world()
        z = Zombie(float(2 * T + _H), float(_H))
        near = _colonist(3 * T + _H, _H)   # 1 tile right
        far  = _colonist(0 * T + _H, _H)   # 2 tiles left
        z.tick(0.1, world, [near, far])
        assert z.x > 2 * T + _H   # moved right toward near


# ── Wall-slide ────────────────────────────────────────────────────────────────

class TestWallSlide:
    def test_zombie_does_not_enter_building_tile(self):
        """Zombie at (1,0) targeting (1,2) must stay on STREET tiles."""
        world = _wall_world()
        z = Zombie(float(_H), float(T + _H))        # (1,0) centre
        col = _colonist(2 * T + _H, T + _H)         # (1,2) centre
        for _ in range(100):
            z.tick(0.016, world, [col])
            r = int(z.y) // T
            c = int(z.x) // T
            assert world.tile_at(r, c) == Tile.STREET, \
                f"Zombie entered non-street tile at ({r},{c})"

    def test_zombie_eventually_reaches_colonist_via_slide(self):
        world = _wall_world()
        z = Zombie(float(_H), float(T + _H))
        col = _colonist(2 * T + _H, T + _H)
        for _ in range(600):
            if z.tick(0.016, world, [col]) is None:
                pass
            dx = z.x - col.x
            dy = z.y - col.y
            if dx * dx + dy * dy <= (z.radius + col.radius + 2) ** 2:
                break
        else:
            pytest.fail("Zombie never reached colonist after 600 ticks")


# ── Melee attack ──────────────────────────────────────────────────────────────

class TestAttack:
    def _place_adjacent(self):
        """Zombie touching colonist (within attack range)."""
        world = _all_street_world()
        reach = ZOMBIE_RADIUS + COLONIST_RADIUS + ZOMBIE_ATTACK_REACH
        z = Zombie(float(_H), float(_H))
        col = _colonist(float(_H + reach - 1), float(_H))
        return z, col, world

    def test_attack_deals_damage(self):
        z, col, world = self._place_adjacent()
        z.tick(0.1, world, [col])
        assert col.hp < 100

    def test_attack_deals_configured_damage(self):
        z, col, world = self._place_adjacent()
        z.tick(0.1, world, [col])
        assert col.hp == 100 - ZOMBIE_DAMAGE

    def test_attack_respects_cooldown(self):
        z, col, world = self._place_adjacent()
        z.tick(0.1, world, [col])   # first hit
        z.tick(0.01, world, [col])  # cooldown not yet expired
        assert len(col.damage_log) == 1

    def test_attack_fires_again_after_cooldown(self):
        z, col, world = self._place_adjacent()
        z.tick(0.01, world, [col])                  # first hit
        z.tick(1.0 / ZOMBIE_ATTACK_RATE, world, [col])  # cooldown fully expired
        assert len(col.damage_log) == 2

    def test_no_attack_when_out_of_range(self):
        world = _all_street_world()
        z = Zombie(float(_H), float(_H))
        col = _colonist(float(4 * T + _H), float(_H))  # far away
        z.tick(0.1, world, [col])
        assert col.hp == 100   # no damage

    def test_zombie_does_not_move_while_attacking(self):
        z, col, world = self._place_adjacent()
        x0, y0 = z.x, z.y
        z.tick(0.1, world, [col])
        assert z.x == pytest.approx(x0) and z.y == pytest.approx(y0)


# ── Death ─────────────────────────────────────────────────────────────────────

def test_dead_zombie_does_not_move():
    world = _all_street_world()
    z = Zombie(float(_H), float(_H))
    z.alive = False
    col = _colonist(4 * T + _H, _H)
    x0, y0 = z.x, z.y
    z.tick(0.1, world, [col])
    assert z.x == x0 and z.y == y0

def test_zombie_dies_when_hp_reaches_zero():
    z = Zombie(0.0, 0.0)
    z.take_damage(ZOMBIE_HP)
    assert not z.alive
