"""
Renderer — all pygame drawing lives here.

Nothing outside this module calls pygame.draw directly.  Visual detail
constants (roof colours, plank spacing, etc.) are renderer-private; they
are not game logic and do not belong in tiles.py or config.py.

Font note: pygame.font.Font is broken on Python 3.14 + pygame 2.6 (circular
import in pygame.font).  We use pygame.freetype instead, which is unaffected.
pygame.freetype.Font.render() returns (surface, rect) rather than just a
surface — _blit_text() wraps this so call sites stay readable.
"""

import os
import pygame
import pygame._freetype   # C extension — avoids the pygame.font↔pygame.sysfont
from config import TILE_SIZE, BRIDGE_COL, TOWER_RANGE_PX, TOWER_WOOD_COST
from tiles import Tile, COLORS, WALKABLE
from world import World
from camera import Camera

# ── Visual detail constants ───────────────────────────────────────────────────
_ROOF_FILL      = (195, 175, 155)
_ROOF_SCAVENGED = ( 90,  78,  65)   # darker tint — building has been looted
_ROOF_EDGE      = ( 80,  65,  50)
_PLANK        = (125,  95,  45)
_TREE         = ( 30, 115,  30)
_SHADOW       = ( 20,  20,  20)
_COLONIST     = ( 70, 160, 220)
_COLONIST_HI  = (160, 210, 245)
_WORK_BAR_BG  = ( 40,  40,  40)
_WORK_BAR_FG  = (220, 180,  60)   # amber — scavenge progress
_ZOMBIE       = ( 55, 170,  55)
_ZOMBIE_HI    = (110, 220, 110)
_HP_BAR_BG         = ( 50,  20,  20)
_HP_BAR_FG         = (210,  40,  40)
_COLONIST_HP_FG    = ( 60, 200, 100)
_SEL_RING     = (255, 220,  50)
_SEL_BOX_FILL = (100, 200, 255,  40)
_SEL_BOX_EDGE = (100, 200, 255)
_TOWER_BASE   = ( 70,  60,  90)
_TOWER_RING   = (150, 130, 190)
_PROJ_COL     = (255, 240, 120)
_GHOST_OK     = (  0, 200, 100)
_GHOST_BAD    = (200,  50,  50)
_BTN_BG       = ( 45,  45,  65)
_BTN_BG_LIVE  = ( 60,  90,  60)   # green tint when BUILD mode active
_BTN_EDGE     = (120, 120, 160)
_PANEL_BG     = ( 30,  32,  44)   # dark blue-grey, clearly distinct from black
_PANEL_EDGE   = (100, 105, 140)   # brighter border so panels are easy to spot
_UI_TEXT      = (210, 210, 215)
_UI_LABEL     = (200, 170,  80)   # warm amber for section labels
_CLEAR_COL    = ( 10,  10,  15)   # background fill for areas outside the map

_FONT_SIZE = 18


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self._screen = screen
        # pygame.freetype (Python wrapper) imports pygame.sysfont, which has a
        # circular import with pygame.font on Python 3.14.  pygame._freetype is
        # the underlying C extension — no Python-level imports, no circular dep.
        # freesansbold.ttf is always bundled inside the pygame package dir.
        try:
            pygame._freetype.init()
            _ttf = os.path.join(os.path.dirname(pygame.__file__), "freesansbold.ttf")
            self._font = pygame._freetype.Font(_ttf, _FONT_SIZE)
        except Exception:
            self._font = None

    # ── Public draw calls (called once per frame in game.py) ─────────────────

    def draw_world(self, world: World, camera: Camera) -> None:
        self._screen.fill(_CLEAR_COL)   # clear areas not covered by map tiles
        T = TILE_SIZE
        win_w = self._screen.get_width()
        win_h = self._screen.get_height()
        cx, cy = int(camera.x), int(camera.y)
        c0 = max(0, cx // T)
        c1 = min(world.cols, (cx + win_w) // T + 2)
        r0 = max(0, cy // T)
        r1 = min(world.rows, (cy + win_h) // T + 2)
        for r in range(r0, r1):
            for c in range(c0, c1):
                self._draw_tile(world.tile_at(r, c), r, c, cx, cy, world)

    def draw_towers(self, world, camera: Camera) -> None:
        T = TILE_SIZE
        for tower in world.towers.values():
            sx, sy = camera.world_to_screen(tower.x, tower.y)
            inner = T - 10
            pygame.draw.rect(
                self._screen, _TOWER_BASE,
                pygame.Rect(sx - inner // 2, sy - inner // 2, inner, inner),
            )
            pygame.draw.circle(self._screen, _TOWER_RING, (sx, sy), 5)

    def draw_projectiles(self, projectiles: list, camera: Camera) -> None:
        for p in projectiles:
            sx, sy = camera.world_to_screen(p.x, p.y)
            pygame.draw.circle(self._screen, _PROJ_COL, (sx, sy), p.radius)

    def draw_build_ghost(
        self,
        ghost_rc: tuple[int, int] | None,
        world,
        camera: Camera,
    ) -> None:
        if ghost_rc is None:
            return
        r, c = ghost_rc
        valid = (
            world.tile_at(r, c) == Tile.STREET
            and (r, c) not in world.towers
        )
        T  = TILE_SIZE
        sx = c * T - int(camera.x)
        sy = r * T - int(camera.y)

        # Ghost tile highlight for the placement position
        tile_surf = pygame.Surface((T, T), pygame.SRCALPHA)
        tile_surf.fill((*(_GHOST_OK if valid else _GHOST_BAD), 90))
        self._screen.blit(tile_surf, (sx, sy))

        if not valid:
            return

        # LOS-aware range preview: shade each tile green (visible) or dim (blocked)
        wx, wy   = world.grid_center(r, c)
        tile_rad = int(TOWER_RANGE_PX / T) + 1
        surf_w   = (2 * tile_rad + 1) * T
        range_surf = pygame.Surface((surf_w, surf_w), pygame.SRCALPHA)

        for dr in range(-tile_rad, tile_rad + 1):
            for dc in range(-tile_rad, tile_rad + 1):
                tr, tc   = r + dr, c + dc
                twx, twy = world.grid_center(tr, tc)
                ddx      = twx - wx
                ddy      = twy - wy
                if ddx * ddx + ddy * ddy > TOWER_RANGE_PX ** 2:
                    continue
                visible = world.has_los(float(wx), float(wy), float(twx), float(twy))
                tile_x  = (dc + tile_rad) * T
                tile_y  = (dr + tile_rad) * T
                col     = (*_GHOST_OK, 40) if visible else (80, 80, 80, 20)
                range_surf.fill(col, pygame.Rect(tile_x, tile_y, T, T))

        self._screen.blit(
            range_surf,
            ((c - tile_rad) * T - int(camera.x),
             (r - tile_rad) * T - int(camera.y)),
        )

    def draw_zombies(self, zombies: list, camera: Camera) -> None:
        for z in zombies:
            sx, sy = camera.world_to_screen(z.x, z.y)
            r = z.radius
            pygame.draw.circle(self._screen, _SHADOW,    (sx + 2, sy + 2), r)
            pygame.draw.circle(self._screen, _ZOMBIE,    (sx,     sy),     r)
            pygame.draw.circle(self._screen, _ZOMBIE_HI, (sx - 2, sy - 2), r // 3)
            self._draw_hp_bar(sx, sy + r + 3, z.hp / z.max_hp)

    def draw_colonists(self, colonists: list, camera: Camera) -> None:
        for col in colonists:
            sx, sy = camera.world_to_screen(col.x, col.y)
            r = col.radius
            pygame.draw.circle(self._screen, _SHADOW,      (sx + 2, sy + 2), r)
            pygame.draw.circle(self._screen, _COLONIST,    (sx,     sy),     r)
            pygame.draw.circle(self._screen, _COLONIST_HI, (sx - 2, sy - 2), r // 3)
            self._draw_hp_bar(sx, sy + r + 3, col.hp / col.max_hp, _COLONIST_HP_FG)
            cmd = col.orders[0] if col.orders else None
            if cmd is not None and hasattr(cmd, "progress"):
                p = cmd.progress
                if p is not None:
                    self._draw_work_bar(sx, sy - r - 7, p)

    def _draw_hp_bar(self, cx: int, top_y: int, fraction: float, color=_HP_BAR_FG) -> None:
        W, H = 20, 3
        x = cx - W // 2
        pygame.draw.rect(self._screen, _HP_BAR_BG, pygame.Rect(x, top_y, W,                   H))
        pygame.draw.rect(self._screen, color,       pygame.Rect(x, top_y, int(W * fraction),   H))

    def _draw_work_bar(self, cx: int, top_y: int, progress: float) -> None:
        W, H = 24, 4
        x = cx - W // 2
        pygame.draw.rect(self._screen, _WORK_BAR_BG,  pygame.Rect(x, top_y, W,                  H))
        pygame.draw.rect(self._screen, _WORK_BAR_FG,  pygame.Rect(x, top_y, int(W * progress),  H))

    def draw_selection_rings(self, selected: set, camera: Camera) -> None:
        for e in selected:
            sx, sy = camera.world_to_screen(e.x, e.y)
            pygame.draw.circle(self._screen, _SEL_RING, (sx, sy), e.radius + 4, 2)

    def draw_selection_box(
        self, rect_screen: tuple[int, int, int, int] | None
    ) -> None:
        if rect_screen is None:
            return
        x0, y0, x1, y1 = rect_screen
        rect = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        if rect.w < 1 or rect.h < 1:
            return
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        surf.fill(_SEL_BOX_FILL)
        self._screen.blit(surf, (rect.x, rect.y))
        pygame.draw.rect(self._screen, _SEL_BOX_EDGE, rect, 1)

    def draw_ui(self, ui, resources, build_active: bool = False) -> None:
        """Draw all UI panels on top of the world.  Must be called last."""
        self._draw_panel(ui.resource_bar)
        self._draw_panel(ui.build_panel)
        if self._font is None:
            return
        self._draw_resource_bar(ui.resource_bar, resources)
        self._draw_build_panel(ui, resources, build_active)

    # ── Private UI helpers ────────────────────────────────────────────────────

    def _draw_panel(self, rect: tuple) -> None:
        x, y, w, h = rect
        r = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self._screen, _PANEL_BG,  r)
        pygame.draw.rect(self._screen, _PANEL_EDGE, r, 1)

    def _blit_text(
        self, text: str, color: tuple, x: int, y: int
    ) -> tuple[int, int]:
        """Render text with freetype and blit it.  Returns (width, height)."""
        surf, rect = self._font.render(text, color)
        self._screen.blit(surf, (x, y))
        return rect.width, rect.height

    def _text_size(self, text: str) -> tuple[int, int]:
        """Return (width, height) of text without blitting."""
        _, rect = self._font.render(text, _UI_TEXT)
        return rect.width, rect.height

    def _draw_resource_bar(self, rect: tuple, resources) -> None:
        x, y, w, h = rect
        text = (
            f"COLONISTS  {resources.colonists}"
            f"        WOOD  {resources.wood}"
            f"        AMMO  {resources.ammo}"
        )
        _, th = self._text_size(text)
        self._blit_text(text, _UI_TEXT, x + 12, y + (h - th) // 2)

    def _draw_build_panel(self, ui, resources, build_active: bool) -> None:
        x, y, w, h = ui.build_panel
        cy = y + h // 2

        # Tower button
        bx, by, bw, bh = ui.tower_button
        can_afford  = resources.wood >= TOWER_WOOD_COST
        btn_bg      = _BTN_BG_LIVE if build_active else _BTN_BG
        pygame.draw.rect(self._screen, btn_bg,   pygame.Rect(bx, by, bw, bh))
        pygame.draw.rect(self._screen, _BTN_EDGE, pygame.Rect(bx, by, bw, bh), 1)

        label_col = _UI_TEXT if can_afford else (120, 100, 80)
        lw, lh = self._text_size("SNIPER")
        self._blit_text("SNIPER", label_col, bx + (bw - lw) // 2, by + 6)
        tw, th = self._text_size("TOWER")
        self._blit_text("TOWER",  label_col, bx + (bw - tw) // 2, by + 6 + lh + 2)
        cost  = f"{TOWER_WOOD_COST} wood"
        cw, _ = self._text_size(cost)
        self._blit_text(cost, _UI_LABEL if can_afford else (100, 80, 50),
                        bx + (bw - cw) // 2, by + bh - _FONT_SIZE - 4)

        hint = ("LMB — place tower    RMB / Esc — cancel"
                if build_active else
                "WASD — scroll    LMB — select    RMB — move / scavenge    Esc — quit")
        hw, hh = self._text_size(hint)
        self._blit_text(hint, _UI_TEXT, x + w - hw - 12, cy - hh // 2)

    def draw_game_over(self) -> None:
        """Semi-transparent overlay with GAME OVER text."""
        W = self._screen.get_width()
        H = self._screen.get_height()
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self._screen.blit(overlay, (0, 0))
        if self._font is None:
            return
        title = "GAME OVER"
        tw, th = self._text_size(title)
        self._blit_text(title, (220, 60, 60), (W - tw) // 2, H // 2 - th - 8)
        hint = "Press Esc to quit"
        hw, hh = self._text_size(hint)
        self._blit_text(hint, _UI_TEXT, (W - hw) // 2, H // 2 + 8)

    # ── Private tile drawing ──────────────────────────────────────────────────

    def _draw_tile(
        self, tile: Tile, r: int, c: int, cam_x: int, cam_y: int, world=None
    ) -> None:
        T = TILE_SIZE
        x = c * T - cam_x
        y = r * T - cam_y
        rect = pygame.Rect(x, y, T, T)
        pygame.draw.rect(self._screen, COLORS[tile], rect)

        if tile == Tile.BUILDING:
            bd = world.get_building(r, c) if world is not None else None
            roof = _ROOF_SCAVENGED if (bd and bd.scavenged) else _ROOF_FILL
            pygame.draw.rect(self._screen, roof, rect.inflate(-8, -8))
            pygame.draw.rect(self._screen, _ROOF_EDGE, rect, 1)

        elif tile == Tile.BRIDGE:
            if c == BRIDGE_COL:          # vertical bridge → horizontal planks
                for i in range(4, T, 7):
                    pygame.draw.line(
                        self._screen, _PLANK,
                        (x + 2, y + i), (x + T - 3, y + i),
                    )
            else:                        # horizontal bridge → vertical planks
                for i in range(4, T, 7):
                    pygame.draw.line(
                        self._screen, _PLANK,
                        (x + i, y + 2), (x + i, y + T - 3),
                    )

        elif tile == Tile.PARK:
            for tx, ty in [(-9, -9), (9, -9), (-9, 9), (9, 9), (0, 0)]:
                pygame.draw.circle(
                    self._screen, _TREE,
                    (x + T // 2 + tx, y + T // 2 + ty), 5,
                )
