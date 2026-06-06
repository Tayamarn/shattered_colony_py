from resources import ResourcePool


class TestInit:
    def test_defaults_to_zero(self):
        r = ResourcePool()
        assert r.colonists == 0
        assert r.wood == 0
        assert r.ammo == 0

    def test_custom_initial_values(self):
        r = ResourcePool(colonists=5, wood=10, ammo=20)
        assert r.colonists == 5
        assert r.wood == 10
        assert r.ammo == 20


class TestEarn:
    def test_earn_wood(self):
        r = ResourcePool()
        r.earn(wood=5)
        assert r.wood == 5

    def test_earn_ammo(self):
        r = ResourcePool()
        r.earn(ammo=3)
        assert r.ammo == 3

    def test_earn_colonists(self):
        r = ResourcePool()
        r.earn(colonists=2)
        assert r.colonists == 2

    def test_earn_multiple_resources_at_once(self):
        r = ResourcePool()
        r.earn(colonists=1, wood=10, ammo=5)
        assert r.colonists == 1
        assert r.wood == 10
        assert r.ammo == 5

    def test_earn_accumulates(self):
        r = ResourcePool(wood=3)
        r.earn(wood=4)
        assert r.wood == 7


class TestSpend:
    def test_spend_deducts_wood(self):
        r = ResourcePool(wood=10)
        r.spend(wood=4)
        assert r.wood == 6

    def test_spend_deducts_ammo(self):
        r = ResourcePool(ammo=10)
        r.spend(ammo=3)
        assert r.ammo == 7

    def test_spend_returns_true_on_success(self):
        r = ResourcePool(wood=10, ammo=10)
        assert r.spend(wood=5, ammo=5) is True

    def test_spend_returns_false_when_insufficient_wood(self):
        r = ResourcePool(wood=2, ammo=10)
        assert r.spend(wood=5, ammo=1) is False

    def test_spend_returns_false_when_insufficient_ammo(self):
        r = ResourcePool(wood=10, ammo=1)
        assert r.spend(wood=1, ammo=5) is False

    def test_spend_does_not_mutate_on_failure(self):
        r = ResourcePool(wood=2, ammo=10)
        r.spend(wood=5, ammo=1)
        assert r.wood == 2
        assert r.ammo == 10

    def test_spend_exact_amount_leaves_zero(self):
        r = ResourcePool(wood=5, ammo=3)
        result = r.spend(wood=5, ammo=3)
        assert result is True
        assert r.wood == 0
        assert r.ammo == 0

    def test_spend_does_not_affect_colonists(self):
        r = ResourcePool(colonists=3, wood=10, ammo=10)
        r.spend(wood=5, ammo=5)
        assert r.colonists == 3
