"""
ResourcePool — tracks the three player resources.

All mutation goes through earn() and spend() so call sites get a single
place to add validation, events, or logging later.
"""


class ResourcePool:
    def __init__(
        self,
        colonists: int = 0,
        wood: int = 0,
        ammo: int = 0,
    ) -> None:
        self.colonists = colonists
        self.wood      = wood
        self.ammo      = ammo

    def earn(
        self,
        colonists: int = 0,
        wood: int = 0,
        ammo: int = 0,
    ) -> None:
        self.colonists += colonists
        self.wood      += wood
        self.ammo      += ammo

    def spend(self, wood: int = 0, ammo: int = 0) -> bool:
        """Deduct resources and return True.  Returns False without mutating
        if the pool has insufficient wood or ammo."""
        if self.wood < wood or self.ammo < ammo:
            return False
        self.wood -= wood
        self.ammo -= ammo
        return True
