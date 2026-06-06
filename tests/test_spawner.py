"""
Tests for Spawner — wave timing, count, escalation, entry-point coverage.

Uses a mock world so we don't depend on map_gen in spawner tests.
"""

from types import SimpleNamespace
import pytest

from spawner import Spawner
from zombie import Zombie
from config import (
    TILE_SIZE, BRIDGE_COL, BRIDGE_ROW, ROWS, COLS,
    WAVE_FIRST_DELAY, WAVE_INTERVAL, WAVE_BASE_COUNT, WAVE_COUNT_GROWTH,
)

_H = TILE_SIZE // 2


def _mock_world():
    """Minimal world mock: grid_center returns a deterministic pixel position."""
    def grid_center(r, c):
        return c * TILE_SIZE + _H, r * TILE_SIZE + _H
    return SimpleNamespace(grid_center=grid_center)


WORLD = _mock_world()


def _tick(spawner, seconds, dt=0.1):
    """Advance spawner by `seconds` total time, returning all emitted zombies."""
    zombies = []
    elapsed = 0.0
    while elapsed < seconds:
        step = min(dt, seconds - elapsed)
        zombies.extend(spawner.tick(step, WORLD))
        elapsed += step
    return zombies


# ── Timing ────────────────────────────────────────────────────────────────────

def test_no_zombies_before_first_wave():
    s = Spawner(WORLD)
    zombies = _tick(s, WAVE_FIRST_DELAY - 0.5)
    assert zombies == []

def test_first_wave_fires_at_first_delay():
    s = Spawner(WORLD)
    zombies = _tick(s, WAVE_FIRST_DELAY + 0.1)
    assert len(zombies) > 0

def test_second_wave_fires_after_interval():
    s = Spawner(WORLD)
    _tick(s, WAVE_FIRST_DELAY + 0.1)   # first wave consumed
    zombies = _tick(s, WAVE_INTERVAL + 0.1)
    assert len(zombies) > 0

def test_no_second_wave_before_interval():
    s = Spawner(WORLD)
    _tick(s, WAVE_FIRST_DELAY + 0.1)
    zombies = _tick(s, WAVE_INTERVAL - 0.5)
    assert zombies == []


# ── Count and escalation ──────────────────────────────────────────────────────

def test_first_wave_has_base_count_per_bridge():
    s = Spawner(WORLD)
    zombies = _tick(s, WAVE_FIRST_DELAY + 0.1)
    assert len(zombies) == WAVE_BASE_COUNT * 4   # 4 bridges

def test_second_wave_has_more_zombies():
    s = Spawner(WORLD)
    _tick(s, WAVE_FIRST_DELAY + 0.1)
    zombies = _tick(s, WAVE_INTERVAL + 0.1)
    expected = (WAVE_BASE_COUNT + WAVE_COUNT_GROWTH) * 4
    assert len(zombies) == expected

def test_wave_counter_increments():
    s = Spawner(WORLD)
    assert s.wave == 0
    _tick(s, WAVE_FIRST_DELAY + 0.1)
    assert s.wave == 1
    _tick(s, WAVE_INTERVAL + 0.1)
    assert s.wave == 2


# ── Entry points ──────────────────────────────────────────────────────────────

def test_zombies_are_zombie_instances():
    s = Spawner(WORLD)
    zombies = _tick(s, WAVE_FIRST_DELAY + 0.1)
    assert all(isinstance(z, Zombie) for z in zombies)

def test_zombies_spawn_near_all_four_bridge_edges():
    """Each bridge end should produce zombies near its entry pixel."""
    s = Spawner(WORLD)
    zombies = _tick(s, WAVE_FIRST_DELAY + 0.1)

    # Expected centre positions for the four entries
    expected = [
        WORLD.grid_center(0,        BRIDGE_COL),
        WORLD.grid_center(ROWS - 1, BRIDGE_COL),
        WORLD.grid_center(BRIDGE_ROW, 0),
        WORLD.grid_center(BRIDGE_ROW, COLS - 1),
    ]
    jitter = TILE_SIZE * 0.3 + 1   # tolerance = max jitter + 1px
    for ex, ey in expected:
        close = [z for z in zombies
                 if abs(z.x - ex) <= jitter and abs(z.y - ey) <= jitter]
        assert len(close) >= WAVE_BASE_COUNT, \
            f"No zombies near entry ({ex},{ey})"


# ── seconds_to_next_wave ──────────────────────────────────────────────────────

def test_seconds_to_next_wave_starts_at_first_delay():
    s = Spawner(WORLD)
    assert s.seconds_to_next_wave == pytest.approx(WAVE_FIRST_DELAY)

def test_seconds_to_next_wave_never_negative():
    s = Spawner(WORLD)
    _tick(s, WAVE_FIRST_DELAY + 10)
    assert s.seconds_to_next_wave >= 0.0
