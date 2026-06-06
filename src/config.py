# Display
TILE_SIZE = 40
WIN_W     = 800
WIN_H     = 600
FPS       = 60

# World grid dimensions
COLS = 50
ROWS = 40

# Island ellipse — centred in the grid
ISLAND_CX: int   = COLS // 2   # 25
ISLAND_CY: int   = ROWS // 2   # 20
ISLAND_RX: float = 19.5
ISLAND_RY: float = 15.5

# Bridge axes — the column and row that cross the water to the map edges
BRIDGE_COL: int = ISLAND_CX
BRIDGE_ROW: int = ISLAND_CY

# Camera
CAMERA_PAN_SPEED: float = 400.0   # pixels per second
CAMERA_EDGE_MARGIN: int = 40      # pixels from viewport edge that triggers edge-scroll

# Colonist
COLONIST_HP: int       = 100
COLONIST_SPEED: float  = 80.0     # pixels per second
COLONIST_RADIUS: int   = 8
ARRIVAL_RADIUS: float  = 6.0      # pixels — waypoint considered reached within this distance

# UI panels
UI_BAR_H: int   = 45   # resource bar height (top of screen)
UI_PANEL_H: int = 90   # build panel height  (bottom of screen)

# Scavenging
SCAVENGE_DURATION: float    = 3.0   # seconds a colonist works at a building
LOOT_WOOD_MIN: int          = 5
LOOT_WOOD_MAX: int          = 15
LOOT_AMMO_MIN: int          = 2
LOOT_AMMO_MAX: int          = 8
LOOT_COLONIST_CHANCE: float = 0.25  # probability a building holds a survivor

# Zombie
ZOMBIE_HP: int             = 60
ZOMBIE_SPEED: float        = 45.0   # pixels/second (slower than colonist)
ZOMBIE_RADIUS: int         = 8
ZOMBIE_DAMAGE: int         = 10     # hp per hit
ZOMBIE_ATTACK_RATE: float  = 0.8   # hits per second
ZOMBIE_ATTACK_REACH: int   = 2     # extra px beyond radius sum to trigger attack

# Spawner (slow burn)
WAVE_FIRST_DELAY: float  = 20.0   # seconds before the first wave
WAVE_INTERVAL: float     = 45.0   # seconds between subsequent waves
WAVE_BASE_COUNT: int     = 2      # zombies per bridge on wave 1
WAVE_COUNT_GROWTH: int   = 1      # additional zombies per bridge per wave

# Sniper tower
TOWER_WOOD_COST: int   = 10
TOWER_RANGE_PX: float  = 200.0   # attack radius in world pixels (~5 tiles)
TOWER_FIRE_RATE: float = 1.0     # shots per second
TOWER_DAMAGE: int      = 30      # hp per hit (zombie has 60 hp → 2 shots)

# Projectile
PROJ_SPEED: float = 300.0   # pixels per second
PROJ_RADIUS: int  = 3
