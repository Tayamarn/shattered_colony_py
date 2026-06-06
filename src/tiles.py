from enum import IntEnum


class Tile(IntEnum):
    WATER    = 0
    STREET   = 1
    BUILDING = 2
    BRIDGE   = 3
    PARK     = 4


WALKABLE: frozenset["Tile"] = frozenset({Tile.STREET, Tile.BRIDGE, Tile.PARK})

# Base fill colour for each tile type — rendering details live in renderer.py
COLORS: dict["Tile", tuple[int, int, int]] = {
    Tile.WATER:    ( 28, 108, 200),
    Tile.STREET:   ( 88,  88,  88),
    Tile.BUILDING: (155, 135, 115),
    Tile.BRIDGE:   (165, 130,  70),
    Tile.PARK:     ( 55, 165,  55),
}
