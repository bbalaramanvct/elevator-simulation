"""Elevator model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from .passenger import Passenger


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    IDLE = "IDLE"


@dataclass
class Elevator:
    """An elevator car that moves one floor per discrete time unit."""

    elevator_id: int
    current_floor: int
    max_capacity: int
    direction: Direction = Direction.IDLE
    passengers: list[Passenger] = field(default_factory=list)
    stops: Set[int] = field(default_factory=set)

    @property
    def passenger_count(self) -> int:
        return len(self.passengers)

    @property
    def is_full(self) -> bool:
        return self.passenger_count >= self.max_capacity

    def add_stop(self, floor: int) -> None:
        self.stops.add(floor)

    def remove_stop(self, floor: int) -> None:
        self.stops.discard(floor)

    def has_stops(self) -> bool:
        return bool(self.stops)

    def choose_direction(self) -> Direction:
        """SCAN-style direction: keep sweeping until no stops ahead, then reverse."""
        return self.choose_scan_direction()

    def choose_scan_direction(self) -> Direction:
        if not self.stops:
            return Direction.IDLE

        floors_above = [f for f in self.stops if f > self.current_floor]
        floors_below = [f for f in self.stops if f < self.current_floor]

        if self.direction == Direction.UP and floors_above:
            return Direction.UP
        if self.direction == Direction.DOWN and floors_below:
            return Direction.DOWN
        if floors_above:
            return Direction.UP
        if floors_below:
            return Direction.DOWN
        return Direction.IDLE

    def move_one_floor(self) -> None:
        if self.direction == Direction.UP:
            self.current_floor += 1
        elif self.direction == Direction.DOWN:
            self.current_floor -= 1

    def distance_to(self, floor: int) -> int:
        return abs(self.current_floor - floor)
