"""Abstract scheduler interface."""

from abc import ABC, abstractmethod

from elevator_simulation.models.elevator import Elevator
from elevator_simulation.models.passenger import Passenger


class Scheduler(ABC):
    """Assigns waiting passengers to elevator cars."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Base Scheduler Algorithm."""

    @abstractmethod
    def assign_elevator(
        self,
        passenger: Passenger,
        elevators: list[Elevator],
    ) -> Elevator:
        """Select an elevator for the passenger and register required stops."""

    def reset(self) -> None:
        """Reset scheduler state between simulation runs."""
