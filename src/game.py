"""
Game — top-level orchestrator.

Creates all subsystems and runs the main loop.  Adding a new subsystem
(entities, UI, spawner, etc.) means instantiating it here and wiring it
into _update and _render.
"""

import sys
import pygame
from config import FPS, BRIDGE_ROW, TOWER_WOOD_COST
from map_gen import generate
from world import World
from camera import Camera
from renderer import Renderer
from ui import UI
from colonist import Colonist
from resources import ResourcePool
from input_handler import (
    InputHandler, SelectClick, BoxSelect, MoveIntent, UIClick,
    ScavengeIntent, BuildPlace, Mode,
)
from selection import Selection
from pathfinding import find_path
from commands import MoveCommand, ScavengeCommand
from steering import separate
from zombie import Zombie
from spawner import Spawner
from tower import SniperTower
from projectile import Projectile
from tiles import Tile


# Grid columns for the 5 starting colonists — all on the main E-W boulevard,
# which is guaranteed STREET by map_gen.
_SPAWN_COLS = [21, 23, 25, 27, 29]


class Game:
    def __init__(self) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Colony")
        self._clock  = pygame.time.Clock()
        win_w, win_h = self._screen.get_size()

        map_data       = generate()
        self._world    = World(map_data.grid, map_data.building_data)
        self._camera   = Camera(self._world.pixel_w, self._world.pixel_h, win_w, win_h)
        self._renderer = Renderer(self._screen)
        self._ui       = UI(win_w, win_h)

        self._colonists: list[Colonist] = self._spawn_colonists()
        self._zombies:      list[Zombie]      = []
        self._projectiles:  list[Projectile]  = []
        self._resources  = ResourcePool(colonists=len(self._colonists))
        self._input      = InputHandler()
        self._selection  = Selection()
        self._spawner    = Spawner(self._world)
        self._game_over  = False

    def run(self) -> None:
        while True:
            dt     = self._clock.tick(FPS) / 1000.0
            events = pygame.event.get()
            self._handle_system_events(events)
            self._update(dt, events)
            self._render()

    # ── Private ───────────────────────────────────────────────────────────────

    def _spawn_colonists(self) -> list[Colonist]:
        colonists = []
        for c in _SPAWN_COLS:
            wx, wy = self._world.grid_center(BRIDGE_ROW, c)
            colonists.append(Colonist(float(wx), float(wy)))
        return colonists

    def _handle_system_events(self, events: list) -> None:
        for ev in events:
            if ev.type == pygame.QUIT:
                self._quit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._quit()

    def _update(self, dt: float, events: list) -> None:
        if self._game_over:
            return

        # Camera
        keys   = pygame.key.get_pressed()
        key_dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) \
               - int(keys[pygame.K_LEFT]  or keys[pygame.K_a])
        key_dy = int(keys[pygame.K_DOWN]  or keys[pygame.K_s]) \
               - int(keys[pygame.K_UP]    or keys[pygame.K_w])
        mouse  = pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
        self._camera.update(key_dx, key_dy, mouse, dt)

        # Input events → subsystems
        mouse_pos = pygame.mouse.get_pos()
        for action in self._input.process(events, mouse_pos, self._camera, self._ui, self._world):
            if isinstance(action, SelectClick):
                self._selection.click_select(action.wx, action.wy, self._colonists)
            elif isinstance(action, BoxSelect):
                self._selection.box_select(
                    action.world_x0, action.world_y0,
                    action.world_x1, action.world_y1,
                    self._colonists,
                )
            elif isinstance(action, MoveIntent):
                self._issue_move(action)
            elif isinstance(action, ScavengeIntent):
                self._issue_scavenge(action)
            elif isinstance(action, BuildPlace):
                self._place_tower(action.r, action.c)
            elif isinstance(action, UIClick):
                if self._ui.tower_button_hit(action.sx, action.sy):
                    self._input.mode = Mode.BUILD

        # Entity ticks
        for colonist in self._colonists:
            colonist.tick(dt, self._world)
        separate(self._colonists, self._world)

        for zombie in self._zombies:
            zombie.tick(dt, self._world, self._colonists)
        self._zombies.extend(self._spawner.tick(dt, self._world))

        for tower in self._world.towers.values():
            target = tower.tick(dt, self._zombies, self._resources)
            if target is not None:
                self._projectiles.append(Projectile(tower.x, tower.y, target))
        for proj in self._projectiles:
            proj.tick(dt)

        # Prune dead entities; sync colonist count; check game-over
        self._projectiles = [p for p in self._projectiles if p.alive]
        self._zombies     = [z for z in self._zombies     if z.alive]
        self._colonists   = [c for c in self._colonists   if c.alive]
        self._selection.selected &= set(self._colonists)
        self._resources.colonists = len(self._colonists)
        if not self._colonists:
            self._game_over = True

    def _issue_scavenge(self, action: ScavengeIntent) -> None:
        for colonist in self._selection.selected:
            cmd = ScavengeCommand(
                action.r, action.c,
                self._resources,
                self._rescue_colonist,
            )
            if action.append:
                colonist.orders.append(cmd)
            else:
                colonist.orders.clear()
                colonist.orders.append(cmd)

    def _place_tower(self, r: int, c: int) -> None:
        if self._world.tile_at(r, c) != Tile.STREET:
            return
        if (r, c) in self._world.towers:
            return
        if not self._resources.spend(wood=TOWER_WOOD_COST):
            return
        self._world.towers[(r, c)] = SniperTower(r, c, self._world)

    def _rescue_colonist(self, wx: float, wy: float) -> None:
        new_col = Colonist(wx, wy)
        self._colonists.append(new_col)
        self._resources.earn(colonists=1)

    def _issue_move(self, action: MoveIntent) -> None:
        goal_r, goal_c = self._world.pixel_to_grid(action.wx, action.wy)
        for colonist in self._selection.selected:
            start_r, start_c = self._world.pixel_to_grid(colonist.x, colonist.y)
            path = find_path(self._world, start_r, start_c, goal_r, goal_c)
            if not path:
                continue
            cmd = MoveCommand(path)
            if action.append:
                colonist.orders.append(cmd)
            else:
                colonist.orders.clear()
                colonist.orders.append(cmd)

    def _render(self) -> None:
        # Compute build ghost tile (grid coords under cursor, or None)
        ghost_rc = None
        if self._input.mode == Mode.BUILD:
            mx, my = pygame.mouse.get_pos()
            wx, wy = self._camera.screen_to_world(mx, my)
            ghost_rc = self._world.pixel_to_grid(wx, wy)

        build_active = self._input.mode == Mode.BUILD
        self._renderer.draw_world(self._world, self._camera)
        self._renderer.draw_entrances(self._world, self._camera)
        self._renderer.draw_towers(self._world, self._camera)
        self._renderer.draw_projectiles(self._projectiles, self._camera)
        self._renderer.draw_zombies(self._zombies, self._camera)
        self._renderer.draw_colonists(self._colonists, self._camera)
        self._renderer.draw_selection_rings(self._selection.selected, self._camera)
        self._renderer.draw_selection_box(self._input.drag_rect_screen)
        self._renderer.draw_build_ghost(ghost_rc, self._world, self._camera)
        self._renderer.draw_ui(self._ui, self._resources, build_active)
        if self._game_over:
            self._renderer.draw_game_over()
        pygame.display.flip()

    @staticmethod
    def _quit() -> None:
        pygame.quit()
        sys.exit()
