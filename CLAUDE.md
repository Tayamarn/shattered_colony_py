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
Command: right-click walkable tile (move), right-click building (scavenge).
Build: bottom panel → click "SNIPER TOWER" → click valid street tile to place.
`Esc` — quit (or cancel BUILD mode).
`RMB` in BUILD mode — cancel back to IDLE.

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

All phases complete.

### ✅ Phase 0 — Clean foundation
Scrollable map, free-pan camera, delta-time established.

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

### ✅ Phase 5 — Scavenging
Connected building tiles flood-filled into groups; each group is subdivided
into wall-sharing rectangular **parcels** (no alley gaps).  Each parcel has
its own `BuildingData` and entrance tile.  `ScavengeCommand` navigates to
the entrance and works for `SCAVENGE_DURATION` seconds.  Loot (wood, ammo,
optional colonist rescue) pre-rolled at map-gen time.  Scavenged buildings
darken; amber progress bar shown above the working colonist.

### ✅ Phase 6 + 7 — Zombies, combat, and death
`Zombie(Entity)` pursues nearest living colonist with wall-sliding movement.
Melee attack with cooldown.  `Spawner` fires escalating waves at all four
bridge ends (slow-burn curve, configurable in `config.py`).  Colonist death
decrements `resources.colonists`; game-over overlay when all are dead.

### ✅ Phase 8 — Towers and projectiles
`SniperTower` placed on street tiles via BUILD mode.  Targets nearest zombie
within `TOWER_RANGE_PX` with line-of-sight check (Bresenham through tile
grid).  `Projectile(Entity)` homes on its target; disappears if target dies
in flight.  Towers consume ammo; stop firing when ammo is zero.  Build ghost
shows per-tile LOS coverage preview.

---

## Update tick order  ← sequence matters

```python
dt = clock.tick(FPS) / 1000.0
events = pygame.event.get()

handle_system_events(events)           # quit / escape

actions = input_handler.process(events, mouse_pos, camera, ui, world)
route_actions(actions, ...)            # game.py dispatches each InputEvent

for c in colonists:  c.tick(dt, world)
separate(colonists, world)             # soft collision between colonists

for z in zombies:    z.tick(dt, world, colonists)
zombies.extend(spawner.tick(dt, world))

for tower in world.towers.values():
    target = tower.tick(dt, zombies, resources)   # returns Zombie or None
    if target: projectiles.append(Projectile(tower.x, tower.y, target))
for p in projectiles: p.tick(dt)

# Prune dead entities
projectiles = [p for p in projectiles if p.alive]
zombies     = [z for z in zombies     if z.alive]
colonists   = [c for c in colonists   if c.alive]
selection.selected &= set(colonists)
resources.colonists = len(colonists)
if not colonists: game_over = True

camera.update(key_dx, key_dy, mouse_pos, dt)
```

Rationale: input before entity ticks → commands land this frame; colonists
before zombies → can start fleeing; spawner after zombie ticks → new zombies
don't act until next frame; towers after zombies move → targeting is current;
prune after all updates → no entity reacts to a same-frame corpse.

Note: `tower.tick()` returns the *zombie* to shoot (not a `Projectile`).
`game.py` constructs the `Projectile` — this keeps `tower.py` free of a
`projectile` import and matches the stated dependency graph.

---

## Render layer order  ← back to front

```
1. screen.fill()          background clear (handles areas outside the map)
2. World tiles            water, streets, buildings (1-px parcel borders), parks, bridges
3. Entrance markers       door frame on building facade + doormat on entrance tile
4. Tower bases            purple square + ring on street tile
5. Projectiles            yellow dot
6. Zombies + health bars  green circle, red HP bar below
7. Colonists + health bars  blue circle, green HP bar below, amber scavenge bar above
8. Selection rings        after bodies so rings are always visible
9. Drag selection box     screen-space rect
10. Build ghost           per-tile LOS coverage preview in BUILD mode
11. UI panels             resource bar + build menu — always on top
12. Game-over overlay     semi-transparent dark screen + text (when all colonists dead)
```

---

## Architecture

### File map

```
config.py          — all constants; balance changes go here only
tiles.py           — Tile enum, WALKABLE, base colours
map_gen.py         — pure generation: returns MapData(grid, building_data)
                     _flood_fill groups tiles; _make_parcels subdivides large
                     groups into wall-sharing parcels; _find_entrance picks
                     the best adjacent walkable tile per parcel

world.py           — World: tile grid, building_data dict, towers dict
                     has_los(x0,y0,x1,y1) — Bresenham LOS query
resources.py       — ResourcePool: colonists, wood, ammo

entity.py          — base: x, y, hp, speed, radius, alive, take_damage()
colonist.py        — Colonist(Entity): orders deque, tick(dt, world)
zombie.py          — Zombie(Entity): wall-sliding pursuit AI, melee attack
tower.py           — SniperTower (not an Entity): LOS targeting, cooldown
projectile.py      — Projectile(Entity): homing, hit on arrival
spawner.py         — wave timer; emits Zombie lists at bridge entry points

pathfinding.py     — A* on tile grid; called once per MoveCommand
commands.py        — MoveCommand, ScavengeCommand (own execute() + state)
steering.py        — separate(entities, world): soft collision push-apart

camera.py          — free-pan, edge scroll, clamp, screen↔world transforms
                     win_w/win_h injected at construction — not from config
input_handler.py   — mouse/key state machine; emits InputEvent objects upward
selection.py       — selected entity set; click-select and box-select logic

ui.py              — panel rects, tower_button rect, hit_test; no pygame import
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
commands                → pathfinding, config
world                   → tiles, config
steering                → tiles
colonist                → entity, commands, world, config
zombie                  → entity, tiles, config
tower                   → config
projectile              → entity, config
spawner                 → zombie, config
selection               → entity, config
camera                  → config
input_handler           → tiles, camera
ui                      → config
renderer                → world, camera, tiles, config
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
- `SelectClick(wx, wy)` — left click on world in IDLE mode
- `BoxSelect(world_x0, world_y0, world_x1, world_y1)` — drag released
- `MoveIntent(wx, wy, append)` — right-click on walkable tile
- `ScavengeIntent(r, c, append)` — right-click on building tile
- `UIClick(sx, sy)` — left-click consumed by a UI panel
- `BuildPlace(r, c, type)` — left-click on world in BUILD mode

In BUILD mode, LMB suppresses selection/drag and emits `BuildPlace` instead.
RMB or Escape cancels BUILD mode back to IDLE.

### input_handler is a state machine with two modes

```
IDLE   — normal: clicks select/command, drags box-select
BUILD  — waiting for placement click; RMB / Escape returns to IDLE
```

UI hit_test is always checked first.  Right-click in IDLE:
1. hit_test — if UI, eat the event.
2. Determine tile under cursor (world→grid transform).
3. BUILDING tile → `ScavengeIntent`; walkable tile → `MoveIntent`; else ignore.

### Buildings are parcels within connected groups

`map_gen._flood_fill` finds connected components of `Tile.BUILDING` tiles.
Large components (> `_SPLIT_THRESHOLD` tiles) are passed to `_make_parcels`,
which divides them into wall-sharing rectangular parcels **without touching the
grid** — no alley tiles are inserted.

Parcel layout (two-level split):
- **Wide/square block**: split in half horizontally (north half / south half),
  then subdivide each half into vertical column strips (2–4 tiles wide).
  North-half buildings face the north outer street; south-half buildings face
  the south outer street; the two halves share a back wall.
- **Tall block**: split in half vertically (west / east), then row strips per half.
- **Edge-block fallback**: if a sub-parcel has no adjacent walkable tile, its
  entrance falls back to the containing group's entrance so every BuildingData
  has a reachable entry point.

Each parcel gets its own `BuildingData` (separate scavenge target, own loot,
own entrance).  The renderer draws 1-pixel edge lines at parcel boundaries
(adjacent `Tile.BUILDING` tiles with different `BuildingData` identity) as well
as at exterior faces, making parcels visually distinct without walkable gaps.

Consequences:
- Scavenging any tile in a parcel scavenges that parcel only (not the whole block).
- Multiple colonists sent to different parcels in the same block can scavenge
  simultaneously without interfering.
- Colonists cannot walk between parcels within a block (shared wall, no alley).
- `ScavengeCommand` navigates directly to `bd.entrance_r/c` — no adjacent-tile
  search needed.

### Commands own their own state and sub-steps

`ScavengeCommand` manages navigation and the work timer internally.
`game.py` only sees `execute() → bool`.  The colonist spawning problem
(commands.py cannot import colonist.py — that would create a cycle) is
solved by callback injection: `ScavengeCommand.__init__` accepts
`on_rescue: Callable[[float, float], None]` which game.py provides.

### Tower LOS uses Bresenham on the tile grid

`world.has_los(x0, y0, x1, y1)` converts both pixel positions to grid coords
and walks `_bresenham(r0,c0,r1,c1)`, returning `False` the moment any
`Tile.BUILDING` is crossed.  `SniperTower` stores a reference to its world
and gates every targeting check through `has_los`.

The build ghost calls `world.has_los` for every tile within range and renders
visible tiles green, blocked tiles dim — giving an accurate coverage preview
before the player places the tower.

### Tower returns a zombie target; game.py creates the Projectile

`tower.tick()` returns the `Zombie` it chose to shoot (after consuming ammo),
or `None`.  `game.py` constructs `Projectile(tower.x, tower.y, target)`.
This keeps `tower.py` free of a `projectile` import, matching the dependency
graph.

`Projectile` homes on a live reference to its target zombie.  If the zombie
dies before the projectile arrives, the projectile disappears.

### Colonist spawning avoids import cycle

```
colonist → commands  (fine)
commands → colonist  (cycle!)
```

Solution: `ScavengeCommand` calls `self._on_rescue(x, y)` instead of
constructing a `Colonist` directly.  `game.py` provides the closure.

### Scavenge progress uses duck-typed `progress` property

`ScavengeCommand.progress` returns `float | None` — `None` when not in the
work state, `0.0–1.0` while the timer runs.  `renderer.draw_colonists` checks
`hasattr(cmd, "progress")` on the front order; no import of `commands.py` in
the renderer.  Any future command can opt into showing a progress bar by
adding the property.

### Entity separation (steering)

After all colonists tick each frame, `steering.separate(colonists, world)`
pushes overlapping pairs apart by half the overlap.  Each axis is tried
independently (sliding).  Colonists won't be pushed into buildings.

### Zombie wall-sliding movement

Zombies don't pathfind.  Each tick, the zombie computes a straight step toward
the nearest living colonist, then tries:
1. Full step (dx, dy)
2. x-only step
3. y-only step

This slides around wall corners without A*.  V2 (flow field) is deferred until
V1 feel is confirmed.

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

### Building and tower state live in side dicts, not in the Tile enum

`world.building_data: dict[(r,c), BuildingData]` and
`world.towers: dict[(r,c), SniperTower]` sit beside the tile grid.
The tile enum stays small; state combinations don't explode.

### Bridges are the strategic chokepoints

Four bridges = four entry points.  Tower placement near bridges is the core
defensive decision.  Single-tile bridge width is intentional.

---

## How to extend

### Add a new buildable structure
1. New class; store in a dict on `World`.
2. Add cost to `config.py`; button to `ui.py`; placement handler in
   `input_handler.py`; draw call in `renderer.py`.

### Add a new unit type
1. Subclass `Entity`; add list in `Game`; tick and draw it.

### Add a new resource
1. Field in `ResourcePool`; display in `_draw_resource_bar`; constants in
   `config.py`.

### Tune balance
All stats, loot ranges, wave parameters, build costs, timers → `config.py` only.

---

## Known issues / not yet implemented

- No formation logic — colonists stack at move destinations.
- Colonists don't flee from zombies or react to them at all.
- Zombie AI v2 (flow field) deferred until v1 feel confirmed.
- No tower destruction (towers have no HP).
- Only one tower type (Sniper).
- No win condition — game ends only on defeat.
