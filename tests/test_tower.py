"""Tests for SniperTower — targeting, cooldown, ammo consumption."""

from types import SimpleNamespace
import pytest

from tower import SniperTower
from config import TOWER_FIRE_RATE, TOWER_RANGE_PX, TILE_SIZE

_H = TILE_SIZE // 2


def _world(r=5, c=5, block_los=False):
    def grid_center(row, col):
        return col * TILE_SIZE + _H, row * TILE_SIZE + _H
    def has_los(x0, y0, x1, y1):
        return not block_los
    return SimpleNamespace(grid_center=grid_center, has_los=has_los)


def _zombie(x, y, alive=True):
    dmg = []
    def take_damage(a):
        dmg.append(a)
        z.hp = max(0, z.hp - a)
        if z.hp <= 0:
            z.alive = False
    z = SimpleNamespace(x=float(x), y=float(y), alive=alive,
                        hp=60, take_damage=take_damage, damage_log=dmg)
    return z


def _resources(ammo=99):
    spent = {"ammo": 0}
    def spend(wood=0, ammo=0):
        if r.ammo < ammo:
            return False
        r.ammo -= ammo
        spent["ammo"] += ammo
        return True
    r = SimpleNamespace(ammo=ammo, wood=0, spend=spend, spent=spent)
    return r


def _tower(r=5, c=5):
    return SniperTower(r, c, _world(r, c))


def _at(tower, dx=0, dy=0):
    """Zombie at tower's position + offset."""
    return _zombie(tower.x + dx, tower.y + dy)


# ── Construction ──────────────────────────────────────────────────────────────

def test_tower_position_is_tile_centre():
    w = _world(3, 7)
    t = SniperTower(3, 7, w)
    assert t.x == pytest.approx(7 * TILE_SIZE + _H)
    assert t.y == pytest.approx(3 * TILE_SIZE + _H)


# ── Targeting ─────────────────────────────────────────────────────────────────

class TestTargeting:
    def test_returns_none_with_no_zombies(self):
        t = _tower()
        assert t.tick(1.0, [], _resources()) is None

    def test_returns_none_when_all_zombies_out_of_range(self):
        t = _tower()
        far = _zombie(t.x + TOWER_RANGE_PX + 10, t.y)
        assert t.tick(1.0, [far], _resources()) is None

    def test_returns_zombie_in_range(self):
        t = _tower()
        z = _at(t, dx=TOWER_RANGE_PX - 10)
        result = t.tick(1.0, [z], _resources())
        assert result is z

    def test_targets_nearest_zombie(self):
        t = _tower()
        near = _at(t, dx=50)
        far  = _at(t, dx=100)
        result = t.tick(1.0, [far, near], _resources())
        assert result is near

    def test_ignores_dead_zombies(self):
        t = _tower()
        dead = _at(t, dx=10)
        dead.alive = False
        assert t.tick(1.0, [dead], _resources()) is None

    def test_zombie_at_exact_range_boundary_is_not_targeted(self):
        t = _tower()
        z = _at(t, dx=TOWER_RANGE_PX)
        assert t.tick(1.0, [z], _resources()) is None


# ── Cooldown ──────────────────────────────────────────────────────────────────

class TestCooldown:
    def test_fires_on_first_tick(self):
        t = _tower()
        z = _at(t, dx=10)
        assert t.tick(1.0, [z], _resources()) is z

    def test_does_not_fire_while_cooling_down(self):
        t = _tower()
        z = _at(t, dx=10)
        r = _resources()
        t.tick(1.0, [z], r)            # first shot
        result = t.tick(0.01, [z], r)  # cooldown not expired
        assert result is None

    def test_fires_again_after_cooldown(self):
        t = _tower()
        z = _at(t, dx=10)
        r = _resources()
        t.tick(1.0, [z], r)
        result = t.tick(1.0 / TOWER_FIRE_RATE, [z], r)
        assert result is z


# ── Ammo ──────────────────────────────────────────────────────────────────────

class TestAmmo:
    def test_consumes_one_ammo_per_shot(self):
        t = _tower()
        z = _at(t, dx=10)
        r = _resources(ammo=5)
        t.tick(1.0, [z], r)
        assert r.ammo == 4

    def test_does_not_fire_with_no_ammo(self):
        t = _tower()
        z = _at(t, dx=10)
        r = _resources(ammo=0)
        assert t.tick(1.0, [z], r) is None

    def test_does_not_consume_ammo_when_no_target(self):
        t = _tower()
        r = _resources(ammo=5)
        t.tick(1.0, [], r)
        assert r.ammo == 5


# ── Line of sight ─────────────────────────────────────────────────────────────

class TestLOS:
    def test_does_not_target_zombie_behind_building(self):
        w = _world(block_los=True)
        t = SniperTower(5, 5, w)
        z = _at(t, dx=10)
        assert t.tick(1.0, [z], _resources()) is None

    def test_targets_zombie_with_clear_los(self):
        w = _world(block_los=False)
        t = SniperTower(5, 5, w)
        z = _at(t, dx=10)
        assert t.tick(1.0, [z], _resources()) is z

    def test_los_check_uses_real_world(self):
        """Integration: tower on open street cannot shoot zombie behind building."""
        from world import World
        from tiles import Tile
        # Layout: STREET(tower) BUILDING STREET(zombie)
        grid = [
            [Tile.STREET, Tile.BUILDING, Tile.STREET],
            [Tile.STREET, Tile.STREET,   Tile.STREET],
        ]
        world = World(grid)
        t = SniperTower(0, 0, world)
        # Place zombie far enough to be past the building but within range
        z = _zombie(2 * TILE_SIZE + _H, _H)
        assert t.tick(1.0, [z], _resources()) is None
