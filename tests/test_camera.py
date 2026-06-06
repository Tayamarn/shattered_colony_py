"""
Tests for the Camera class.

Covers: initial position, key-driven panning, edge-scroll panning, world-bound
clamping, delta-time scaling, and the screen↔world coordinate round-trips.
"""

import pytest
from camera import Camera
from config import WIN_W, WIN_H, CAMERA_PAN_SPEED, CAMERA_EDGE_MARGIN

WORLD_W = 2000
WORLD_H = 1600
MID_SCREEN = (WIN_W // 2, WIN_H // 2)   # mouse far from any edge → no edge-scroll


def make_cam(**kwargs) -> Camera:
    """Construct a Camera with sensible test defaults, overridable via kwargs."""
    return Camera(
        world_pixel_w=kwargs.get("world_pixel_w", WORLD_W),
        world_pixel_h=kwargs.get("world_pixel_h", WORLD_H),
        win_w=kwargs.get("win_w", WIN_W),
        win_h=kwargs.get("win_h", WIN_H),
    )


@pytest.fixture
def cam() -> Camera:
    return make_cam()


# ── Initial state ─────────────────────────────────────────────────────────────

class TestInitialState:
    def test_starts_horizontally_centred(self, cam):
        expected = (WORLD_W - WIN_W) / 2
        assert abs(cam.x - expected) < 1.0

    def test_starts_vertically_centred(self, cam):
        expected = (WORLD_H - WIN_H) / 2
        assert abs(cam.y - expected) < 1.0

    def test_initial_position_is_within_bounds(self, cam):
        assert 0 <= cam.x <= WORLD_W - WIN_W
        assert 0 <= cam.y <= WORLD_H - WIN_H


# ── Key panning ───────────────────────────────────────────────────────────────

class TestKeyPanning:
    def test_key_right_increases_x(self, cam):
        before = cam.x
        cam.update(1, 0, MID_SCREEN, dt=0.1)
        assert cam.x > before

    def test_key_left_decreases_x(self, cam):
        cam.update(1, 0, MID_SCREEN, dt=1.0)
        before = cam.x
        cam.update(-1, 0, MID_SCREEN, dt=0.1)
        assert cam.x < before

    def test_key_down_increases_y(self, cam):
        before = cam.y
        cam.update(0, 1, MID_SCREEN, dt=0.1)
        assert cam.y > before

    def test_key_up_decreases_y(self, cam):
        cam.update(0, 1, MID_SCREEN, dt=1.0)
        before = cam.y
        cam.update(0, -1, MID_SCREEN, dt=0.1)
        assert cam.y < before

    def test_zero_dt_means_no_movement(self, cam):
        x, y = cam.x, cam.y
        cam.update(1, 1, MID_SCREEN, dt=0.0)
        assert cam.x == x
        assert cam.y == y

    def test_movement_scales_linearly_with_dt(self):
        cam_a = make_cam()
        cam_b = make_cam()
        origin = make_cam()
        cam_a.update(1, 0, MID_SCREEN, dt=0.1)
        cam_b.update(1, 0, MID_SCREEN, dt=0.2)
        assert pytest.approx(cam_b.x - origin.x, abs=1) == 2 * (cam_a.x - origin.x)

    def test_pan_speed_constant_matches_config(self):
        cam = make_cam()
        start = cam.x
        cam.update(1, 0, MID_SCREEN, dt=1.0)
        assert pytest.approx(cam.x - start, abs=1) == CAMERA_PAN_SPEED


# ── Clamping ──────────────────────────────────────────────────────────────────

class TestClamping:
    def test_cannot_scroll_left_of_origin(self, cam):
        for _ in range(300):
            cam.update(-1, 0, MID_SCREEN, dt=0.1)
        assert cam.x == 0.0

    def test_cannot_scroll_right_of_max(self, cam):
        for _ in range(300):
            cam.update(1, 0, MID_SCREEN, dt=0.1)
        assert cam.x == float(WORLD_W - WIN_W)

    def test_cannot_scroll_above_origin(self, cam):
        for _ in range(300):
            cam.update(0, -1, MID_SCREEN, dt=0.1)
        assert cam.y == 0.0

    def test_cannot_scroll_below_max(self, cam):
        for _ in range(300):
            cam.update(0, 1, MID_SCREEN, dt=0.1)
        assert cam.y == float(WORLD_H - WIN_H)


# ── Edge scrolling ────────────────────────────────────────────────────────────

class TestEdgeScroll:
    def test_mouse_at_left_edge_scrolls_left(self, cam):
        cam.update(1, 0, MID_SCREEN, dt=1.0)
        before = cam.x
        cam.update(0, 0, (0, WIN_H // 2), dt=0.1)
        assert cam.x < before

    def test_mouse_at_right_edge_scrolls_right(self, cam):
        before = cam.x
        cam.update(0, 0, (WIN_W - 1, WIN_H // 2), dt=0.1)
        assert cam.x > before

    def test_mouse_at_top_edge_scrolls_up(self, cam):
        cam.update(0, 1, MID_SCREEN, dt=1.0)
        before = cam.y
        cam.update(0, 0, (WIN_W // 2, 0), dt=0.1)
        assert cam.y < before

    def test_mouse_at_bottom_edge_scrolls_down(self, cam):
        before = cam.y
        cam.update(0, 0, (WIN_W // 2, WIN_H - 1), dt=0.1)
        assert cam.y > before

    def test_mouse_one_pixel_inside_margin_does_not_scroll(self, cam):
        before = cam.x
        cam.update(0, 0, (CAMERA_EDGE_MARGIN, WIN_H // 2), dt=0.5)
        assert cam.x == before

    def test_none_mouse_pos_does_not_trigger_edge_scroll(self):
        cam = make_cam()
        x, y = cam.x, cam.y
        cam.update(0, 0, None, dt=1.0)
        assert cam.x == x
        assert cam.y == y

    def test_key_and_edge_in_same_direction_do_not_double_speed(self):
        """key_dx=1 + edge_dx=1 should clamp to 1, not produce 2× movement."""
        cam_key_only = make_cam()
        cam_key_edge = make_cam()
        right_edge = (WIN_W - 1, WIN_H // 2)
        cam_key_only.update(1, 0, MID_SCREEN, dt=0.1)
        cam_key_edge.update(1, 0, right_edge,  dt=0.1)
        assert cam_key_only.x == cam_key_edge.x

    def test_edge_scroll_uses_actual_win_dimensions(self):
        """Camera with a different win size should edge-scroll at its own boundaries."""
        small_win_w, small_win_h = 400, 300
        cam = make_cam(win_w=small_win_w, win_h=small_win_h)
        before = cam.x
        # Right edge of a 400-wide window
        cam.update(0, 0, (small_win_w - 1, small_win_h // 2), dt=0.1)
        assert cam.x > before


# ── Coordinate transforms ─────────────────────────────────────────────────────

class TestCoordinateTransforms:
    def test_world_to_screen_round_trip(self, cam):
        for wx, wy in [(500, 400), (0, 0), (WORLD_W - 1, WORLD_H - 1)]:
            sx, sy = cam.world_to_screen(wx, wy)
            wx2, wy2 = cam.screen_to_world(sx, sy)
            assert (wx2, wy2) == (wx, wy), \
                f"Round-trip failed for world ({wx},{wy})"

    def test_screen_to_world_round_trip(self, cam):
        for sx, sy in [(0, 0), (WIN_W // 2, WIN_H // 2), (WIN_W - 1, WIN_H - 1)]:
            wx, wy = cam.screen_to_world(sx, sy)
            sx2, sy2 = cam.world_to_screen(wx, wy)
            assert (sx2, sy2) == (sx, sy), \
                f"Round-trip failed for screen ({sx},{sy})"

    def test_world_to_screen_respects_camera_offset(self, cam):
        sx, sy = cam.world_to_screen(int(cam.x) + 100, int(cam.y) + 50)
        assert sx == 100
        assert sy == 50

    def test_screen_to_world_respects_camera_offset(self, cam):
        wx, wy = cam.screen_to_world(0, 0)
        assert wx == int(cam.x)
        assert wy == int(cam.y)
