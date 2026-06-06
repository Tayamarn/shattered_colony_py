"""
InputHandler — mouse/keyboard state machine.

Returns a list of typed InputEvent objects each frame; never calls anything
directly.  game.py routes the events to the right subsystems.

Two modes:
  IDLE  — normal play: clicks select/command, drags box-select
  BUILD — waiting for a placement click; Escape returns to IDLE
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import pygame

from camera import Camera
from tiles import Tile, WALKABLE

# Pixels the mouse must travel from button-down before it becomes a drag.
_DRAG_THRESHOLD_SQ = 5 ** 2


# ── Mode ──────────────────────────────────────────────────────────────────────

class Mode(Enum):
    IDLE  = auto()
    BUILD = auto()


# ── Event types ───────────────────────────────────────────────────────────────

@dataclass
class SelectClick:
    """Left click on the world (not on UI) — no drag."""
    wx: int
    wy: int

@dataclass
class BoxSelect:
    """Left drag released — corners in world coordinates."""
    world_x0: int
    world_y0: int
    world_x1: int
    world_y1: int

@dataclass
class MoveIntent:
    """Right-click on the world — move selected units here."""
    wx: int
    wy: int
    append: bool   # True when Shift was held — appends rather than replaces orders

@dataclass
class UIClick:
    """Left-click that landed on a UI panel — consumed before world logic."""
    sx: int
    sy: int

@dataclass
class ScavengeIntent:
    """Right-click on a building tile — scavenge it with selected colonists."""
    r: int
    c: int
    append: bool

@dataclass
class BuildPlace:
    """Left-click on the world while in BUILD mode — place a structure."""
    r: int
    c: int
    type: str = "sniper"


# ── Handler ───────────────────────────────────────────────────────────────────

class InputHandler:
    def __init__(self) -> None:
        self.mode: Mode = Mode.IDLE

        self._button_down:    bool                    = False
        self._down_screen:    tuple[int, int] | None  = None
        self._current_screen: tuple[int, int]         = (0, 0)
        self._dragging:       bool                    = False

    # ── Per-frame entry point ─────────────────────────────────────────────────

    def process(
        self,
        events: list,
        mouse_pos: tuple[int, int],
        camera: Camera,
        ui=None,
        world=None,
    ) -> list:
        """Process this frame's events and return a list of InputEvent objects.

        Pass ui to enable click-eating: any mouse-button-down that lands on a
        UI panel emits UIClick and is not forwarded to world logic.  ui=None
        disables hit-testing.

        Pass world to enable tile-aware right-click routing: BUILDING tiles
        emit ScavengeIntent; walkable tiles emit MoveIntent; water/void is
        ignored.  world=None falls back to always-emit-MoveIntent behavior.
        """
        self._current_screen = mouse_pos
        result: list = []

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if ui is not None and ui.hit_test(*ev.pos):
                    result.append(UIClick(ev.pos[0], ev.pos[1]))
                elif self.mode == Mode.IDLE:
                    # Only start selection drag in IDLE mode
                    self._button_down = True
                    self._down_screen = ev.pos
                    self._dragging    = False

            elif ev.type == pygame.MOUSEMOTION:
                if self._button_down and self._down_screen is not None:
                    dx = ev.pos[0] - self._down_screen[0]
                    dy = ev.pos[1] - self._down_screen[1]
                    if dx * dx + dy * dy > _DRAG_THRESHOLD_SQ:
                        self._dragging = True

            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self.mode == Mode.BUILD:
                    if not (ui is not None and ui.hit_test(*ev.pos)):
                        wx, wy = camera.screen_to_world(*ev.pos)
                        if world is not None:
                            r, c = world.pixel_to_grid(wx, wy)
                            result.append(BuildPlace(r, c, "sniper"))
                else:
                    if self._down_screen is not None:
                        if self._dragging:
                            wx0, wy0 = camera.screen_to_world(*self._down_screen)
                            wx1, wy1 = camera.screen_to_world(*ev.pos)
                            result.append(BoxSelect(wx0, wy0, wx1, wy1))
                        else:
                            wx, wy = camera.screen_to_world(*ev.pos)
                            result.append(SelectClick(wx, wy))
                    self._button_down = False
                    self._down_screen = None
                    self._dragging    = False

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
                if self.mode == Mode.BUILD:
                    self.mode = Mode.IDLE   # right-click cancels build placement
                    continue
                if ui is not None and ui.hit_test(*ev.pos):
                    continue   # right-click on UI: no command
                wx, wy = camera.screen_to_world(*ev.pos)
                shift  = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                if world is not None:
                    r, c = world.pixel_to_grid(wx, wy)
                    tile = world.tile_at(r, c)
                    if tile == Tile.BUILDING:
                        result.append(ScavengeIntent(r, c, append=shift))
                    elif tile in WALKABLE:
                        result.append(MoveIntent(wx, wy, append=shift))
                    # else: water / void — ignore
                else:
                    result.append(MoveIntent(wx, wy, append=shift))

            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                if self.mode == Mode.BUILD:
                    self.mode = Mode.IDLE

        return result

    # ── State exposed for rendering ───────────────────────────────────────────

    @property
    def drag_rect_screen(self) -> tuple[int, int, int, int] | None:
        """Current drag box in screen coords, or None when not dragging."""
        if self._dragging and self._down_screen is not None:
            return (*self._down_screen, *self._current_screen)  # type: ignore[return-value]
        return None
