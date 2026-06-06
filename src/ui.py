"""
UI — panel layout and hit-testing.

Defines the two screen panels (resource bar, build menu) as plain
(x, y, w, h) tuples.  No pygame import — the renderer constructs
pygame.Rects from these when drawing.

game.py passes a UI instance to input_handler so clicks on panels
are consumed before reaching world logic.
"""

from config import UI_BAR_H, UI_PANEL_H


_BTN_W = 110
_BTN_H = 50


class UI:
    def __init__(self, win_w: int, win_h: int) -> None:
        self.resource_bar: tuple[int, int, int, int] = (0, 0, win_w, UI_BAR_H)
        self.build_panel:  tuple[int, int, int, int] = (0, win_h - UI_PANEL_H, win_w, UI_PANEL_H)
        _, py, _, ph = self.build_panel
        self.tower_button: tuple[int, int, int, int] = (
            60, py + (ph - _BTN_H) // 2, _BTN_W, _BTN_H
        )

    def hit_test(self, sx: int, sy: int) -> bool:
        """True if the screen point (sx, sy) falls inside any UI panel."""
        return _in_rect(self.resource_bar, sx, sy) or \
               _in_rect(self.build_panel,  sx, sy)

    def tower_button_hit(self, sx: int, sy: int) -> bool:
        return _in_rect(self.tower_button, sx, sy)


def _in_rect(rect: tuple[int, int, int, int], sx: int, sy: int) -> bool:
    x, y, w, h = rect
    return x <= sx < x + w and y <= sy < y + h
