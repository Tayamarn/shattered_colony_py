# Colony

A top-down real-time strategy game set on a city island.  No protagonist.
The player controls the god-view camera and issues orders to colonists via
mouse.  Zombies pour in across the four bridges in escalating waves.  The
player scavenges buildings, manages resources, and builds sniper towers to
hold the perimeter.

Resources: **colonists** (selectable units), **wood** (building material),
**ammo** (consumed by towers).

## Running

```bash
pip install -r requirements.txt
python main.py
```

Launches in **fullscreen** at native resolution.  Window size is determined
at runtime from `pygame.display.set_mode((0,0), pygame.FULLSCREEN)` — all
subsystems that need screen dimensions receive them via constructor arguments,
not from `config.py` constants.

Camera: `WASD` / arrow keys or mouse edge-scroll.
Select: left-click a unit; left-drag for box selection.
Command: right-click ground (move), right-click building (scavenge),
         right-click zombie (attack — Phase 7).
Build: bottom panel → click item → click valid tile to place (Phase 8).
`Esc` — quit.

---

## Coordinate systems  ← establish this first, everything depends on it

Three systems in use.  Every cross-system transform must be explicit:

```
Screen  (sx, sy)   pixels from top-left of the window
                   source: pygame.mouse.get_pos()

World   (wx, wy)   pixels from top-left of the full map
                   wx = sx + cam.x,  wy = sy + cam.y

Grid    (r,  c)    tile indices, row-major
                   r = int(wy) // TILE_SIZE
                   c = int(wx) // TILE_SIZE
```

`Camera` provides `screen_to_world` and `world_to_screen`.
`World` provides `pixel_to_grid(wx,wy)→(r,c)` and `grid_center(r,c)→(wx,wy)`.
Never compute these inline — always call the method.

---

## Build plan

Each phase ends with a runnable game.  Do not start phase N+1 until phase N
runs without errors.

### ✅ Phase 0 — Clean foundation
Scrollable map, free-pan camera, delta-time established.  `player.py` deleted.

### ✅ Phase 1 — Entities on screen
`ResourcePool`, `Entity` base class, `Colonist`.  5 colonists spawned near
the map centre; drawn as coloured circles.

### ✅ Phase 2 — Selection
`InputHandler` state machine (IDLE / BUILD modes).  Left-click selects one
colonist; drag box-selects multiple.  Selection ring drawn around selected
units.  UI panels eat clicks before world logic sees them.

### ✅ Phase 3 — Movement
A* pathfinding (8-directional, diagonal corner check).  `MoveCommand` with
internal waypoint deque.  Right-click on walkable tile issues move orders.
Shift+right-click appends to queue.  `steering.separate()` prevents colonists
from walking through each other.

### ✅ Phase 4 — UI scaffold
Resource bar (top, 45 px) and build menu panel (bottom, 90 px).  Resource
counts (colonists / wood / ammo) displayed.  Clicks on panels never reach
world logic.  Game runs fullscreen.

### Phase 5 — Scavenging  ← next
*Goal: send colonists to buildings; resources increase.*

- `map_gen.py`: also produce `building_data: dict[(r,c), BuildingData]`.
  `BuildingData`: `scavenged`, `wood`, `ammo`, `has_colonist`.
  Return `MapData(grid, building_data)` named tuple from `generate()`.
- `world.py`: store `building_data`; expose `get_building(r,c)→BuildingData|None`.
- `commands.py`: `ScavengeCommand` — sub-states: init → navigate → work → done.
  Callback injection (`on_rescue`) for colonist spawning (avoids import cycle).
- `input_handler.py`: right-click on BUILDING tile → `ScavengeIntent(r,c,append)`.
- `renderer.py`: scavenged buildings drawn with darker roof tint.

### Phase 6 — Zombies and spawning
- `zombie.py`: `Zombie(Entity)` — direct-pursuit AI v1, melee attack.
- `spawner.py`: wave timer; spawn at four bridge entry points.

### Phase 7 — Combat and death
- `entity.py`: `take_damage()` already implemented.
- Colonist death removes from list, decrements `resources.colonists`.
- Game-over when `resources.colonists == 0`.

### Phase 8 — Towers and projectiles
- `projectile.py`, `tower.py`, `spawner.py`.
- Build menu "Sniper Tower" button; BUILD mode in input_handler.
- Towers auto-target nearest zombie in range; consume ammo.

---

## Update tick order  ← sequence matters

```python
dt = clock.tick(FPS) / 1000.0
events = pygame.event.get()

# System events (quit / escape) handled first
handle_system_events(events)

# Input → actions → subsystems
actions = input_handler.process(events, mouse_pos, camera, ui, world)
route_actions(actions, ...)

# Entity ticks
for c in colonists:  c.tick(dt, world)
separate(colonists, world)               # soft collision between colonists

for z in zombies:    z.tick(dt, world, colonists)

new_proj = []
for tower in world.towers.values():
    p = tower.tick(dt, zombies, resources)
    if p: new_proj.append(p)
projectiles.extend(new_proj)

for p in projectiles: p.tick(dt)

zombies.extend(spawner.tick(dt, world))

# Prune dead entities
zombies     = [z for z in zombies     if z.alive]
colonists   = [c for c in colonists   if c.alive]
projectiles = [p for p in projectiles if p.alive]

camera.update(key_dx, key_dy, mouse_pos, dt)
```

Rationale: input before entity ticks → commands land this frame; colonists
before zombies → can start fleeing; towers after zombies move → targeting is
current; prune after all updates → no entity reacts to a same-frame corpse.

---

## Render layer order  ← back to front

```
1. screen.fill()          background clear (handles areas outside the map)
2. World tiles            water, streets, buildings, parks, bridges
3. Scavenge overlays      darker roof tint on scavenged buildings  (Phase 5)
4. Tower bases            icon on street tile  (Phase 8)
5. Projectiles            (Phase 8)
6. Zombies + health bars  (Phase 6)
7. Colonists + health bars
8. Selection rings        after bodies so rings are always visible
9. Drag selection box     screen-space rect
10. Build ghost           tile highlight under mouse in BUILD mode  (Phase 8)
11. UI panels             resource bar + build menu — always on top
```

---

## Architecture

### File map

```
config.py          — all constants; balance changes go here only
tiles.py           — Tile enum, WALKABLE, base colours
map_gen.py         — pure generation: returns MapData(grid, building_data)

world.py           — World: tile grid, building_data dict, towers dict
resources.py       — ResourcePool: colonists, wood, ammo

entity.py          — base: x, y, hp, speed, radius, alive, take_damage()
colonist.py        — Colonist(Entity): orders deque, tick(dt, world)
zombie.py          — Zombie(Entity): pursuit AI, melee  [Phase 6]
tower.py           — SniperTower (not an Entity): targeting, cooldown  [Phase 8]
projectile.py      — Projectile(Entity): straight-line, hit on arrival  [Phase 8]
spawner.py         — wave timer; emits Zombie lists at bridge positions  [Phase 6]

pathfinding.py     — A* on tile grid; called once per MoveCommand
commands.py        — MoveCommand, ScavengeCommand (own execute() + state)
steering.py        — separate(entities, world): soft collision push-apart

camera.py          — free-pan, edge scroll, clamp, screen↔world transforms
                     win_w/win_h injected at construction — not from config
input_handler.py   — mouse/key state machine; emits InputEvent objects upward
selection.py       — selected entity set; click-select and box-select logic

ui.py              — panel rects, hit_test(sx,sy)→bool; no pygame import
renderer.py        — all pygame drawing; receives data, never mutates state
                     uses pygame._freetype (C extension) to avoid circular
                     import bug in pygame.font + pygame.sysfont on Python 3.14

game.py            — owns all subsystems; runs the update and render loops
main.py            — entry point
```

### Dependency graph (no cycles)

```
config, tiles           → nothing
map_gen                 → tiles, config
entity                  → config
resources               → config
pathfinding             → world, tiles, config
commands                → pathfinding, tiles, config
world                   → tiles, config
steering                → tiles
colonist                → entity, commands, world, config
zombie                  → entity, world, config          [Phase 6]
tower                   → config                         [Phase 8]
projectile              → entity, config                 [Phase 8]
spawner                 → zombie, config                 [Phase 6]
selection               → entity, config
camera                  → config
input_handler           → tiles, commands, world, camera, ui, config
ui                      → config
renderer                → world, entity, colonist, zombie, tower, projectile,
                          selection, camera, ui, tiles, config
game                    → all of the above
```

No-pygame zone (testable without display): `config`, `tiles`, `map_gen`,
`world`, `resources`, `entity`, `colonist`, `zombie`, `tower`, `projectile`,
`spawner`, `pathfinding`, `commands`, `steering`, `selection`, `camera`, `ui`.

---

## Key design decisions

### Input handler emits events upward — never calls things directly

`input_handler.process()` returns a list of typed `InputEvent` objects.
`game.py` routes these to subsystems.  Current event types:
- `SelectClick(wx, wy)` — left click in world
- `BoxSelect(world_x0, world_y0, world_x1, world_y1)` — drag released
- `MoveIntent(wx, wy, append)` — right-click on walkable tile
- `ScavengeIntent(r, c, append)` — right-click on building tile  [Phase 5]
- `UIClick(sx, sy)` — left-click consumed by a UI panel
- `AttackIntent(entity)` — right-click on zombie  [Phase 7]
- `BuildPlace(r, c, type)` — placement click in BUILD mode  [Phase 8]

### input_handler is a state machine with two modes

```
IDLE   — normal: clicks select/command, drags box-select
BUILD  — waiting for placement click; Escape returns to IDLE
```

UI hit_test is always checked first.  Right-click logic:
1. hit_test — if UI, eat the event.
2. Determine tile under cursor (world→grid transform).
3. Emit the appropriate *Intent.

### Commands own their own state and sub-steps

`ScavengeCommand` manages navigation and the work timer internally.
`game.py` only sees `execute() → bool`.  The colonist spawning problem
(commands.py cannot import colonist.py — that would create a cycle) is
solved by callback injection: `ScavengeCommand.__init__` accepts
`on_rescue: Callable[[float, float], None]` which game.py provides.

### Colonist spawning avoids import cycle

```
colonist → commands  (fine)
commands → colonist  (cycle!)
```

Solution: `ScavengeCommand` calls `self._on_rescue(x, y)` instead of
constructing a `Colonist` directly.  `game.py` provides the closure.

### Entity separation (steering)

After all colonists tick each frame, `steering.separate(colonists, world)`
pushes overlapping pairs apart by half the overlap.  Each axis is tried
independently (sliding, same logic as camera edge-scroll).  Colonists won't
be pushed into buildings.

### WIN_W / WIN_H are not global constants at runtime

The game opens fullscreen with `pygame.display.set_mode((0,0), FULLSCREEN)`.
Actual dimensions are read from the surface via `screen.get_size()` and
injected into `Camera(world_w, world_h, win_w, win_h)` and `UI(win_w, win_h)`.
`Renderer` queries `self._screen.get_width() / get_height()` directly.
`config.WIN_W = 800` and `config.WIN_H = 600` exist only as test defaults.

### pygame._freetype — not pygame.freetype

`pygame.freetype` (the Python wrapper) imports `pygame.sysfont`, which has a
circular dependency with `pygame.font` on Python 3.14.  `pygame._freetype`
is the underlying C extension — no Python-level imports, no circular dep.
`Renderer` uses it with `freesansbold.ttf` from the pygame package directory.

### Building state lives in a side dict, not in the Tile enum

`world.building_data: dict[(r,c), BuildingData]` sits beside the tile grid.
Same pattern for towers: `world.towers: dict[(r,c), SniperTower]`.
The tile enum stays small; state combinations don't explode.

### Towers are not Entities

Towers don't move.  `SniperTower` stored in `world.towers` is simpler than
subclassing `Entity`.  Add `hp` directly if towers need to be destroyable.

### Zombie AI: naive v1, flow field v2

**V1:** each zombie moves directly toward the nearest living colonist (~5 lines).
**V2:** flow field — BFS from all colonist positions, O(grid) to compute,
O(1) per zombie.  Do not implement until V1 feel is confirmed.

### Pathfinding: 8-directional A* with diagonal corner check

Diagonal step `(dr,dc)` only allowed when both cardinal neighbours `(r+dr, c)`
and `(r, c+dc)` are walkable.  Octile heuristic.  Called once per command
creation, never per frame.

### Bridges are the strategic chokepoints

Four bridges = four entry points.  Tower placement near bridges is the core
defensive decision.  Single-tile bridge width is intentional.

---

## How to extend

### Add a new buildable structure
1. New class; store in a dict on `World`.
2. Add cost to `config.py`; button to `ui.py`; placement handler in `input_handler.py`; draw call in `renderer.py`.

### Add a new unit type
1. Subclass `Entity`; add list in `Game`; tick and draw it.

### Add a new resource
1. Field in `ResourcePool`; display in `_draw_resource_bar`; constants in `config.py`.

### Tune balance
All stats, loot ranges, wave parameters, build costs, timers → `config.py` only.

---

## Known issues / not yet implemented

- Phases 5–8 outstanding (scavenging, zombies, combat, towers).
- No visual feedback during scavenge work timer (colonist just stands still).
- No formation logic — colonists stack at move destinations.
- Zombie AI v2 (flow field) deferred until v1 feel confirmed.
