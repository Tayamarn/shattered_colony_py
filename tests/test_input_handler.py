"""
Tests for InputHandler.

pygame is imported only for its integer constants (MOUSEBUTTONDOWN etc.),
which are accessible without calling pygame.init() or creating a display.
Events are passed as SimpleNamespace objects — InputHandler only reads
.type, .button, and .pos, so duck-typing is sufficient.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace
import pytest
import pygame

from input_handler import InputHandler, SelectClick, BoxSelect, MoveIntent, UIClick, Mode


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """Initialize pygame with headless drivers so key.get_mods() works in tests."""
    pygame.init()
    yield
    pygame.quit()


# ── Helpers ───────────────────────────────────────────────────────────────────

class _MockCamera:
    """Returns world = screen + offset so we can verify the conversion happens."""
    OFFSET = 500

    def screen_to_world(self, sx: int, sy: int) -> tuple[int, int]:
        return sx + self.OFFSET, sy + self.OFFSET


def _ev(type_: int, **kwargs):
    return SimpleNamespace(type=type_, **kwargs)

def _down(pos, button=1):
    return _ev(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)

def _up(pos, button=1):
    return _ev(pygame.MOUSEBUTTONUP, pos=pos, button=button)

def _move(pos):
    return _ev(pygame.MOUSEMOTION, pos=pos)

def _key(key):
    return _ev(pygame.KEYDOWN, key=key)

CAM = _MockCamera()
MID = (400, 300)   # a mouse position that won't trigger anything on its own


# ── Initial state ─────────────────────────────────────────────────────────────

def test_starts_in_idle_mode():
    assert InputHandler().mode == Mode.IDLE

def test_drag_rect_is_none_initially():
    assert InputHandler().drag_rect_screen is None


# ── SelectClick ───────────────────────────────────────────────────────────────

class TestSelectClick:
    def test_short_click_emits_select_click(self):
        h = InputHandler()
        events = [_down((100, 200)), _up((100, 200))]
        result = h.process(events, MID, CAM)
        assert len(result) == 1
        assert isinstance(result[0], SelectClick)

    def test_select_click_world_coords_converted_via_camera(self):
        h = InputHandler()
        events = [_down((100, 200)), _up((100, 200))]
        ev = h.process(events, MID, CAM)[0]
        assert ev.wx == 100 + _MockCamera.OFFSET
        assert ev.wy == 200 + _MockCamera.OFFSET

    def test_no_events_emitted_on_button_down_alone(self):
        h = InputHandler()
        result = h.process([_down((100, 200))], MID, CAM)
        assert result == []

    def test_right_button_click_ignored(self):
        h = InputHandler()
        events = [_down((100, 200), button=2), _up((100, 200), button=2)]
        assert h.process(events, MID, CAM) == []


# ── BoxSelect ─────────────────────────────────────────────────────────────────

class TestBoxSelect:
    def _drag(self, start, end):
        h = InputHandler()
        events = [
            _down(start),
            _move((start[0] + 10, start[1] + 10)),   # cross threshold
            _up(end),
        ]
        return h, h.process(events, MID, CAM)

    def test_drag_emits_box_select(self):
        _, result = self._drag((50, 50), (200, 200))
        assert len(result) == 1
        assert isinstance(result[0], BoxSelect)

    def test_box_select_corners_converted_via_camera(self):
        _, result = self._drag((50, 50), (200, 200))
        ev = result[0]
        assert ev.world_x0 == 50  + _MockCamera.OFFSET
        assert ev.world_y0 == 50  + _MockCamera.OFFSET
        assert ev.world_x1 == 200 + _MockCamera.OFFSET
        assert ev.world_y1 == 200 + _MockCamera.OFFSET


# ── Drag threshold ────────────────────────────────────────────────────────────

class TestDragThreshold:
    def test_move_below_threshold_stays_click(self):
        h = InputHandler()
        events = [
            _down((100, 100)),
            _move((103, 100)),   # 3 px < threshold of 5
            _up((103, 100)),
        ]
        result = h.process(events, MID, CAM)
        assert isinstance(result[0], SelectClick)

    def test_move_above_threshold_becomes_drag(self):
        h = InputHandler()
        events = [
            _down((100, 100)),
            _move((106, 100)),   # 6 px > threshold of 5
            _up((200, 200)),
        ]
        result = h.process(events, MID, CAM)
        assert isinstance(result[0], BoxSelect)

    def test_diagonal_move_uses_euclidean_distance(self):
        # 3px in x and 3px in y = ~4.24 px < 5 → still a click
        h = InputHandler()
        events = [
            _down((100, 100)),
            _move((103, 103)),
            _up((103, 103)),
        ]
        result = h.process(events, MID, CAM)
        assert isinstance(result[0], SelectClick)


# ── Drag rect ─────────────────────────────────────────────────────────────────

class TestDragRect:
    def test_no_drag_rect_before_threshold(self):
        h = InputHandler()
        h.process([_down((100, 100)), _move((103, 100))], (103, 100), CAM)
        assert h.drag_rect_screen is None

    def test_drag_rect_present_after_threshold(self):
        h = InputHandler()
        h.process([_down((100, 100)), _move((110, 100))], (110, 100), CAM)
        assert h.drag_rect_screen is not None

    def test_drag_rect_cleared_after_release(self):
        h = InputHandler()
        events = [_down((100, 100)), _move((110, 100)), _up((200, 200))]
        h.process(events, MID, CAM)
        assert h.drag_rect_screen is None

    def test_drag_rect_contains_start_and_current(self):
        h = InputHandler()
        h.process([_down((50, 60)), _move((80, 90))], (80, 90), CAM)
        rect = h.drag_rect_screen
        assert rect is not None
        x0, y0, x1, y1 = rect
        assert (x0, y0) == (50, 60)
        assert (x1, y1) == (80, 90)


# ── Mode ──────────────────────────────────────────────────────────────────────

class TestMode:
    def test_escape_in_build_mode_returns_to_idle(self):
        h = InputHandler()
        h.mode = Mode.BUILD
        h.process([_key(pygame.K_ESCAPE)], MID, CAM)
        assert h.mode == Mode.IDLE

    def test_escape_in_idle_mode_does_not_change_mode(self):
        h = InputHandler()
        h.process([_key(pygame.K_ESCAPE)], MID, CAM)
        assert h.mode == Mode.IDLE   # Escape in IDLE is handled by game.py (quit)


# ── UI click-eating ───────────────────────────────────────────────────────────

def _ui_always_hit():
    return SimpleNamespace(hit_test=lambda sx, sy: True)

def _ui_never_hit():
    return SimpleNamespace(hit_test=lambda sx, sy: False)

def _ui_hits_top(threshold_y: int = 30):
    """Simulates a resource bar: hit if sy < threshold_y."""
    return SimpleNamespace(hit_test=lambda sx, sy: sy < threshold_y)


class TestUIClickEating:
    def test_left_click_on_ui_emits_ui_click(self):
        h = InputHandler()
        result = h.process([_down((100, 10)), _up((100, 10))], MID, CAM, _ui_always_hit())
        assert any(isinstance(e, UIClick) for e in result)

    def test_left_click_on_ui_does_not_emit_select_click(self):
        h = InputHandler()
        result = h.process([_down((100, 10)), _up((100, 10))], MID, CAM, _ui_always_hit())
        assert not any(isinstance(e, SelectClick) for e in result)

    def test_ui_click_carries_screen_coords(self):
        h = InputHandler()
        result = h.process([_down((123, 10))], MID, CAM, _ui_always_hit())
        ui_ev = next(e for e in result if isinstance(e, UIClick))
        assert ui_ev.sx == 123
        assert ui_ev.sy == 10

    def test_left_click_on_world_with_ui_still_emits_select_click(self):
        h = InputHandler()
        # UI only hits y < 30; click at y=200 is in the world
        result = h.process([_down((100, 200)), _up((100, 200))], MID, CAM, _ui_hits_top())
        assert any(isinstance(e, SelectClick) for e in result)

    def test_drag_cannot_start_on_ui(self):
        h = InputHandler()
        # Button down on UI: no drag state recorded
        h.process([_down((100, 10)), _move((200, 10))], MID, CAM, _ui_always_hit())
        assert h.drag_rect_screen is None

    def test_right_click_on_ui_does_not_emit_move_intent(self):
        h = InputHandler()
        result = h.process([_down((100, 10), button=3)], MID, CAM, _ui_always_hit())
        assert not any(isinstance(e, MoveIntent) for e in result)

    def test_right_click_on_world_with_ui_emits_move_intent(self):
        h = InputHandler()
        result = h.process([_down((100, 200), button=3)], MID, CAM, _ui_hits_top())
        assert any(isinstance(e, MoveIntent) for e in result)

    def test_no_ui_passed_behaves_as_before(self):
        h = InputHandler()
        result = h.process([_down((100, 10)), _up((100, 10))], MID, CAM)
        assert any(isinstance(e, SelectClick) for e in result)
