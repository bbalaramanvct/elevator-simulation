"""Building and simulation configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingConfig:
    """Configurable parameters for the elevator system."""

    num_elevators: int
    min_floor: int
    max_floor: int
    max_passengers_per_elevator: int

    @property
    def num_floors(self) -> int:
        return self.max_floor - self.min_floor + 1

    def validate(self) -> None:
        if self.num_elevators < 1:
            raise ValueError("num_elevators must be at least 1")
        if self.min_floor >= self.max_floor:
            raise ValueError("min_floor must be less than max_floor")
        if self.max_passengers_per_elevator < 1:
            raise ValueError("max_passengers_per_elevator must be at least 1")

    def is_valid_floor(self, floor: int) -> bool:
        return self.min_floor <= floor <= self.max_floor
