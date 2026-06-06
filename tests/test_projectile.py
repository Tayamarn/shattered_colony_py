"""Tests for Projectile — homing movement, hit detection, dead-target cleanup."""

from types import SimpleNamespace
import pytest

from projectile import Projectile
from config import PROJ_SPEED, TOWER_DAMAGE


def _target(x, y, alive=True):
    dmg = []
    def take_damage(a):
        dmg.append(a)
        t.hp = max(0, t.hp - a)
        if t.hp <= 0:
            t.alive = False
    t = SimpleNamespace(x=float(x), y=float(y), alive=alive,
                        hp=60, take_damage=take_damage, damage_log=dmg)
    return t


# ── Construction ──────────────────────────────────────────────────────────────

def test_projectile_starts_alive():
    t = _target(100, 0)
    assert Projectile(0, 0, t).alive

def test_projectile_starts_at_given_position():
    t = _target(100, 0)
    p = Projectile(10.0, 20.0, t)
    assert p.x == pytest.approx(10.0)
    assert p.y == pytest.approx(20.0)


# ── Movement ──────────────────────────────────────────────────────────────────

class TestMovement:
    def test_moves_toward_target(self):
        t = _target(200, 0)
        p = Projectile(0, 0, t)
        p.tick(0.1)
        assert p.x > 0   # moved right toward target

    def test_does_not_overshoot(self):
        t = _target(5, 0)
        p = Projectile(0, 0, t)
        p.tick(1.0)   # would travel 300px but target is only 5px away
        assert p.alive is False   # hit and died

    def test_speed_scales_with_dt(self):
        t1 = _target(1000, 0)
        t2 = _target(1000, 0)
        p1 = Projectile(0, 0, t1)
        p2 = Projectile(0, 0, t2)
        p1.tick(0.1)
        p2.tick(0.2)
        assert p2.x == pytest.approx(p1.x * 2, abs=0.01)


# ── Hit detection ─────────────────────────────────────────────────────────────

class TestHit:
    def test_deals_tower_damage_on_arrival(self):
        t = _target(1, 0)   # 1px away — arrives immediately
        p = Projectile(0, 0, t)
        p.tick(0.1)
        assert TOWER_DAMAGE in t.damage_log

    def test_marks_itself_dead_on_arrival(self):
        t = _target(1, 0)
        p = Projectile(0, 0, t)
        p.tick(0.1)
        assert not p.alive

    def test_does_not_damage_target_each_tick_after_arrival(self):
        t = _target(1, 0)
        p = Projectile(0, 0, t)
        p.tick(0.1)   # arrives
        p.tick(0.1)   # already dead — should do nothing
        assert len(t.damage_log) == 1


# ── Dead target ───────────────────────────────────────────────────────────────

class TestDeadTarget:
    def test_disappears_when_target_dies_mid_flight(self):
        t = _target(1000, 0)
        p = Projectile(0, 0, t)
        p.tick(0.01)      # moving toward target
        t.alive = False   # target killed by something else
        p.tick(0.01)      # should notice and die
        assert not p.alive

    def test_does_not_move_after_target_dies(self):
        t = _target(1000, 0)
        p = Projectile(0, 0, t)
        p.tick(0.01)
        t.alive = False
        x_before = p.x
        p.tick(0.1)
        assert p.x == x_before   # didn't move (died on target-dead check)
