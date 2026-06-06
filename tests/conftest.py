"""Shared fixtures available to all test modules."""

import pytest
from map_gen import generate
from world import World
from camera import Camera


@pytest.fixture(scope="module")
def grid():
    """A generated tile grid — created once per test module."""
    return generate().grid


@pytest.fixture(scope="module")
def world(grid):
    """A World wrapping the generated grid — created once per test module."""
    return World(grid)


@pytest.fixture
def cam():
    """A fresh Camera for each test — state must not bleed between tests."""
    from config import WIN_W, WIN_H
    return Camera(world_pixel_w=2000, world_pixel_h=1600, win_w=WIN_W, win_h=WIN_H)
