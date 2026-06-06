"""
World — owns the tile grid and answers spatial queries.

Deliberately has no pygame dependency so it can be tested in isolation.
The grid is injected at construction time; use map_gen.generate() to
produce one, or pass a hand-crafted grid in tests.
"""

from tiles import Tile, WALKABLE
from config import TILE_SIZE


def _bresenham(r0: int, c0: int, r1: int, c1: int):
    """Yield every grid cell on the Bresenham line from (r0,c0) to (r1,c1)."""
    dr = abs(r1 - r0)
    dc = abs(c1 - c0)
    sr = 1 if r1 > r0 else -1
    sc = 1 if c1 > c0 else -1
    err = dr - dc
    r, c = r0, c0
    while True:
        yield r, c
        if r == r1 and c == c1:
            break
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r   += sr
        if e2 < dr:
            err += dr
            c   += sc


class World:
    def __init__(
        self, grid: list[list[Tile]], building_data: dict | None = None
    ) -> None:
        self._grid          = grid
        self._building_data = building_data or {}
        self.towers: dict   = {}   # (r, c) → SniperTower; populated at runtime
        self.rows    = len(grid)
        self.cols    = len(grid[0]) if grid else 0
        self.pixel_w = self.cols * TILE_SIZE
        self.pixel_h = self.rows * TILE_SIZE

    # ── Building data ─────────────────────────────────────────────────────────

    def get_building(self, r: int, c: int):
        """Return BuildingData for tile (r, c), or None if not a building."""
        return self._building_data.get((r, c))

    # ── Line-of-sight ─────────────────────────────────────────────────────────

    def has_los(self, x0: float, y0: float, x1: float, y1: float) -> bool:
        """True when no BUILDING tile interrupts the straight line from (x0,y0) to (x1,y1)."""
        r0, c0 = self.pixel_to_grid(x0, y0)
        r1, c1 = self.pixel_to_grid(x1, y1)
        for r, c in _bresenham(r0, c0, r1, c1):
            if self.tile_at(r, c) == Tile.BUILDING:
                return False
        return True

    # ── Grid access ───────────────────────────────────────────────────────────

    def tile_at(self, r: int, c: int) -> Tile:
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self._grid[r][c]
        return Tile.WATER

    def tile_at_pixel(self, px: float, py: float) -> Tile:
        return self.tile_at(int(py) // TILE_SIZE, int(px) // TILE_SIZE)

    # ── Movement queries ──────────────────────────────────────────────────────

    def is_passable(self, px: float, py: float, margin: int) -> bool:
        """True if all four corner points at ±margin from (px, py) are walkable."""
        return all(
            self.tile_at_pixel(px + dx, py + dy) in WALKABLE
            for dx in (-margin, margin)
            for dy in (-margin, margin)
        )

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def pixel_to_grid(self, wx: float, wy: float) -> tuple[int, int]:
        """World pixel → (row, col).  May be out of bounds — caller must check."""
        return int(wy) // TILE_SIZE, int(wx) // TILE_SIZE

    def grid_center(self, r: int, c: int) -> tuple[int, int]:
        """Centre of tile (r, c) in world pixels."""
        return c * TILE_SIZE + TILE_SIZE // 2, r * TILE_SIZE + TILE_SIZE // 2

    # ── Raw grid (read-only) ──────────────────────────────────────────────────

    @property
    def grid(self) -> list[list[Tile]]:
        return self._grid
