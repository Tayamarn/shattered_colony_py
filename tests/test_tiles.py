from tiles import Tile, WALKABLE, COLORS


def test_tile_values_are_unique():
    values = [t.value for t in Tile]
    assert len(values) == len(set(values))


def test_walkable_excludes_impassable_tiles():
    assert Tile.WATER    not in WALKABLE
    assert Tile.BUILDING not in WALKABLE


def test_walkable_includes_traversable_tiles():
    assert Tile.STREET in WALKABLE
    assert Tile.BRIDGE in WALKABLE
    assert Tile.PARK   in WALKABLE


def test_every_tile_has_a_colour():
    for tile in Tile:
        assert tile in COLORS, f"Tile.{tile.name} missing from COLORS"


def test_all_colours_are_valid_rgb():
    for tile, colour in COLORS.items():
        assert len(colour) == 3, f"Tile.{tile.name} colour is not an RGB triple"
        assert all(0 <= v <= 255 for v in colour), \
            f"Tile.{tile.name} colour {colour} has out-of-range component"
