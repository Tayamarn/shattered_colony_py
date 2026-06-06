import pytest
from entity import Entity


def make_entity(hp=100):
    return Entity(x=10.0, y=20.0, hp=hp, speed=50.0, radius=8)


class TestInit:
    def test_position_stored(self):
        e = Entity(x=3.0, y=7.0, hp=50, speed=10.0, radius=5)
        assert e.x == 3.0
        assert e.y == 7.0

    def test_hp_equals_max_hp_at_birth(self):
        e = make_entity(hp=80)
        assert e.hp == 80
        assert e.max_hp == 80

    def test_speed_and_radius_stored(self):
        e = Entity(x=0, y=0, hp=10, speed=99.0, radius=12)
        assert e.speed == 99.0
        assert e.radius == 12

    def test_alive_is_true_at_birth(self):
        assert make_entity().alive is True


class TestTakeDamage:
    def test_reduces_hp(self):
        e = make_entity(hp=100)
        e.take_damage(30)
        assert e.hp == 70

    def test_does_not_go_below_zero(self):
        e = make_entity(hp=10)
        e.take_damage(999)
        assert e.hp == 0

    def test_alive_remains_true_after_partial_damage(self):
        e = make_entity(hp=100)
        e.take_damage(50)
        assert e.alive is True

    def test_sets_alive_false_when_hp_reaches_zero(self):
        e = make_entity(hp=50)
        e.take_damage(50)
        assert e.alive is False

    def test_sets_alive_false_on_overkill(self):
        e = make_entity(hp=10)
        e.take_damage(999)
        assert e.alive is False

    def test_max_hp_unchanged_after_damage(self):
        e = make_entity(hp=100)
        e.take_damage(40)
        assert e.max_hp == 100

    def test_zero_damage_has_no_effect(self):
        e = make_entity(hp=100)
        e.take_damage(0)
        assert e.hp == 100
        assert e.alive is True

    @pytest.mark.parametrize("hp,damage,expected_alive", [
        (100, 99,  True),
        (100, 100, False),
        (100, 101, False),
        (1,   1,   False),
    ])
    def test_alive_boundary(self, hp, damage, expected_alive):
        e = make_entity(hp=hp)
        e.take_damage(damage)
        assert e.alive is expected_alive
