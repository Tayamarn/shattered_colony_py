from colonist import Colonist
from entity import Entity
from config import COLONIST_HP, COLONIST_SPEED, COLONIST_RADIUS


class TestColonist:
    def test_is_entity(self):
        assert isinstance(Colonist(0.0, 0.0), Entity)

    def test_alive_at_birth(self):
        assert Colonist(0.0, 0.0).alive is True

    def test_position_stored(self):
        c = Colonist(100.0, 200.0)
        assert c.x == 100.0
        assert c.y == 200.0

    def test_hp_matches_config(self):
        c = Colonist(0.0, 0.0)
        assert c.hp == COLONIST_HP
        assert c.max_hp == COLONIST_HP

    def test_speed_matches_config(self):
        assert Colonist(0.0, 0.0).speed == COLONIST_SPEED

    def test_radius_matches_config(self):
        assert Colonist(0.0, 0.0).radius == COLONIST_RADIUS

    def test_take_damage_inherited(self):
        c = Colonist(0.0, 0.0)
        c.take_damage(COLONIST_HP)
        assert c.alive is False
