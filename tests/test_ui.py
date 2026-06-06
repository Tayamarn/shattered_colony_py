"""Tests for UI panel layout and hit-testing."""

import pytest
from ui import UI
from config import UI_BAR_H, UI_PANEL_H

WIN_W = 800
WIN_H = 600


@pytest.fixture
def ui():
    return UI(WIN_W, WIN_H)


# ── Panel geometry ────────────────────────────────────────────────────────────

class TestPanelGeometry:
    def test_resource_bar_starts_at_top_left(self, ui):
        x, y, w, h = ui.resource_bar
        assert x == 0 and y == 0

    def test_resource_bar_spans_full_width(self, ui):
        _, _, w, _ = ui.resource_bar
        assert w == WIN_W

    def test_resource_bar_has_correct_height(self, ui):
        _, _, _, h = ui.resource_bar
        assert h == UI_BAR_H

    def test_build_panel_is_at_bottom(self, ui):
        _, y, _, h = ui.build_panel
        assert y + h == WIN_H

    def test_build_panel_spans_full_width(self, ui):
        _, _, w, _ = ui.build_panel
        assert w == WIN_W

    def test_build_panel_has_correct_height(self, ui):
        _, _, _, h = ui.build_panel
        assert h == UI_PANEL_H

    def test_panels_adapt_to_win_size(self):
        ui = UI(1920, 1080)
        assert ui.resource_bar[2] == 1920
        _, y, _, h = ui.build_panel
        assert y + h == 1080


# ── hit_test: resource bar ────────────────────────────────────────────────────

class TestHitTestResourceBar:
    def test_centre_of_resource_bar_is_hit(self, ui):
        assert ui.hit_test(WIN_W // 2, UI_BAR_H // 2)

    def test_top_left_pixel_is_hit(self, ui):
        assert ui.hit_test(0, 0)

    def test_last_pixel_of_bar_is_hit(self, ui):
        assert ui.hit_test(WIN_W - 1, UI_BAR_H - 1)

    def test_first_pixel_below_bar_is_not_hit(self, ui):
        assert not ui.hit_test(WIN_W // 2, UI_BAR_H)

    def test_right_edge_pixel_inside_bar_is_hit(self, ui):
        assert ui.hit_test(WIN_W - 1, 0)

    def test_one_past_right_edge_is_not_hit(self, ui):
        assert not ui.hit_test(WIN_W, 0)


# ── hit_test: build panel ─────────────────────────────────────────────────────

class TestHitTestBuildPanel:
    def test_centre_of_build_panel_is_hit(self, ui):
        panel_y = WIN_H - UI_PANEL_H
        assert ui.hit_test(WIN_W // 2, panel_y + UI_PANEL_H // 2)

    def test_top_pixel_of_build_panel_is_hit(self, ui):
        assert ui.hit_test(WIN_W // 2, WIN_H - UI_PANEL_H)

    def test_bottom_right_pixel_is_hit(self, ui):
        assert ui.hit_test(WIN_W - 1, WIN_H - 1)

    def test_one_pixel_above_build_panel_is_not_hit(self, ui):
        assert not ui.hit_test(WIN_W // 2, WIN_H - UI_PANEL_H - 1)


# ── hit_test: world area ──────────────────────────────────────────────────────

class TestHitTestWorld:
    def test_centre_of_screen_is_not_hit(self, ui):
        assert not ui.hit_test(WIN_W // 2, WIN_H // 2)

    def test_world_area_returns_false(self, ui):
        # Anywhere between the two panels
        for y in range(UI_BAR_H, WIN_H - UI_PANEL_H):
            assert not ui.hit_test(0, y), f"y={y} should be world area"
