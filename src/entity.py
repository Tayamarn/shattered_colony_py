"""
Entity — base class for all positioned, health-bearing objects.

Subclasses (Colonist, Zombie, Projectile) call super().__init__() and add
their own tick() method with whatever signature their logic requires.
There is intentionally no abstract tick() here — zombie and colonist ticks
take different arguments and a forced common signature would be dishonest.
"""


class Entity:
    def __init__(
        self,
        x: float,
        y: float,
        hp: int,
        speed: float,
        radius: int,
    ) -> None:
        self.x       = x
        self.y       = y
        self.hp      = hp
        self.max_hp  = hp
        self.speed   = speed
        self.radius  = radius
        self.alive   = True

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.alive = False
