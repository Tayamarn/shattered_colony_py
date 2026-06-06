"""
Camera — free-pan viewport over the world.

Moved by key input (passed in as dx/dy) and edge-scrolling (mouse near the
viewport boundary).  Clamped to world bounds so the viewport never shows
outside the map.

win_w and win_h are the actual window dimensions passed at construction time,
not read from config — this lets them reflect the true fullscreen resolution.

No pygame import — camera.py stays in the no-pygame zone.
"""

from config import CAMERA_PAN_SPEED, CAMERA_EDGE_MARGIN


class Camera:
    def __init__(
        self,
        world_pixel_w: int,
        world_pixel_h: int,
        win_w: int,
        win_h: int,
    ) -> None:
        self._win_w = win_w
        self._win_h = win_h
        self._max_x = max(0, world_pixel_w - win_w)
        self._max_y = max(0, world_pixel_h - win_h)
        # Start centred on the map
        self.x: float = max(0.0, min(float(self._max_x),
                                     world_pixel_w / 2 - win_w / 2))
        self.y: float = max(0.0, min(float(self._max_y),
                                     world_pixel_h / 2 - win_h / 2))

    def update(
        self,
        key_dx: int,
        key_dy: int,
        mouse_pos: tuple[int, int] | None,
        dt: float,
    ) -> None:
        """Pan the camera.  key_dx/key_dy are −1/0/+1 from held keys.
        Pass mouse_pos=None when the window lacks focus to suppress edge-scroll."""
        edge_dx = 0
        edge_dy = 0
        if mouse_pos is not None:
            mx, my = mouse_pos
            if mx < CAMERA_EDGE_MARGIN:                   edge_dx = -1
            elif mx >= self._win_w - CAMERA_EDGE_MARGIN:  edge_dx =  1
            if my < CAMERA_EDGE_MARGIN:                   edge_dy = -1
            elif my >= self._win_h - CAMERA_EDGE_MARGIN:  edge_dy =  1

        # Clamp combined direction to ±1 so keys + edge don't double speed
        dx = max(-1, min(1, key_dx + edge_dx))
        dy = max(-1, min(1, key_dy + edge_dy))

        self.x = max(0.0, min(float(self._max_x), self.x + dx * CAMERA_PAN_SPEED * dt))
        self.y = max(0.0, min(float(self._max_y), self.y + dy * CAMERA_PAN_SPEED * dt))

    # ── Coordinate transforms ─────────────────────────────────────────────────

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx) - int(self.x), int(wy) - int(self.y)

    def screen_to_world(self, sx: int, sy: int) -> tuple[int, int]:
        return sx + int(self.x), sy + int(self.y)
