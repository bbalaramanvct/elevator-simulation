"""Round-robin scheduler."""

from elevator_simulation.models.elevator import Elevator
from elevator_simulation.models.passenger import Passenger

from .base import Scheduler


class RoundRobinScheduler(Scheduler):
    """Assign requests to elevators in rotating order."""

    def __init__(self) -> None:
        self._next_index = 0

    @property
    def name(self) -> str:
        return "round_robin"

    def reset(self) -> None:
        self._next_index = 0

    def assign_elevator(
        self,
        passenger: Passenger,
        elevators: list[Elevator],
    ) -> Elevator:
        elevator = elevators[self._next_index % len(elevators)]
        self._next_index += 1
        passenger.assigned_elevator_id = elevator.elevator_id
        elevator.add_stop(passenger.start_floor)
        elevator.add_stop(passenger.destination_floor)
        return elevator
