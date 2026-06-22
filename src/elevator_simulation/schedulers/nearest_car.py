"""Nearest-car (shortest travel distance) scheduler."""

from elevator_simulation.models.elevator import Direction, Elevator
from elevator_simulation.models.passenger import Passenger

from .base import Scheduler


class NearestCarScheduler(Scheduler):
    """Assign each request to the elevator with the smallest cost to reach the start floor."""

    @property
    def name(self) -> str:
        return "nearest_car"

    def assign_elevator(
        self,
        passenger: Passenger,
        elevators: list[Elevator],
    ) -> Elevator:
        best = min(elevators, key=lambda e: self._cost(e, passenger.start_floor))
        self._register_passenger(best, passenger)
        return best

    def _cost(self, elevator: Elevator, target_floor: int) -> int:
        if elevator.direction == Direction.IDLE:
            return elevator.distance_to(target_floor)

        current = elevator.current_floor
        if elevator.direction == Direction.UP:
            if target_floor >= current:
                return target_floor - current
            upward_stops = [f for f in elevator.stops if f >= current] or [current]
            highest = max(upward_stops)
            return (highest - current) + (highest - target_floor)

        if target_floor <= current:
            return current - target_floor
        downward_stops = [f for f in elevator.stops if f <= current] or [current]
        lowest = min(downward_stops)
        return (current - lowest) + (target_floor - lowest)

    def _register_passenger(self, elevator: Elevator, passenger: Passenger) -> None:
        passenger.assigned_elevator_id = elevator.elevator_id
        elevator.add_stop(passenger.start_floor)
        elevator.add_stop(passenger.destination_floor)
