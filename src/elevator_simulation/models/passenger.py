"""Passenger model and request representation."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PassengerRequest:
    """A passenger request parsed from CSV input."""

    time: int
    passenger_id: str
    start_floor: int
    destination_floor: int


@dataclass
class Passenger:
    """Passenger tracked through the simulation lifecycle."""

    passenger_id: str
    start_floor: int
    destination_floor: int
    request_time: int
    assigned_elevator_id: Optional[int] = None
    pickup_time: Optional[int] = None
    dropoff_time: Optional[int] = None

    @property
    def wait_time(self) -> Optional[int]:
        if self.pickup_time is None:
            return None
        return self.pickup_time - self.request_time

    @property
    def travel_time(self) -> Optional[int]:
        if self.pickup_time is None or self.dropoff_time is None:
            return None
        return self.dropoff_time - self.pickup_time

    @property
    def total_time(self) -> Optional[int]:
        if self.dropoff_time is None:
            return None
        return self.dropoff_time - self.request_time

    @property
    def is_waiting(self) -> bool:
        return self.pickup_time is None

    @property
    def is_on_elevator(self) -> bool:
        return self.pickup_time is not None and self.dropoff_time is None

    @property
    def is_complete(self) -> bool:
        return self.dropoff_time is not None
