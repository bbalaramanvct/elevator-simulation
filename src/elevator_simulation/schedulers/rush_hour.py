"""Rush-hour adaptive scheduler: SCAN during peak windows, fallback otherwise."""

from __future__ import annotations

from datetime import datetime

from elevator_simulation.models.elevator import Elevator
from elevator_simulation.models.passenger import Passenger
from elevator_simulation.rush_hour import active_rush_window, is_rush_hour

from .base import Scheduler
from .nearest_car import NearestCarScheduler
from .round_robin import RoundRobinScheduler
from .scan import ScanScheduler


class RushHourScheduler(Scheduler):
    """
    Selects SCAN or a fallback scheduler based on local system time at startup.

    Rush windows (local time, end exclusive):
      08:00-10:00, 12:00-13:00, 16:00-18:00
    """

    def __init__(
        self,
        fallback: Scheduler | None = None,
        moment: datetime | None = None,
    ) -> None:
        self._moment = moment
        self._fallback = fallback or NearestCarScheduler()
        self._scan = ScanScheduler()
        self._use_scan = is_rush_hour(moment)
        self._active = self._scan if self._use_scan else self._fallback
        self._window = active_rush_window(moment)

    @property
    def name(self) -> str:
        if self._use_scan:
            suffix = f"_{self._window.replace(':', '')}" if self._window else ""
            return f"rush_hour_scan{suffix}"
        return f"rush_hour_{self._fallback.name}"

    @property
    def uses_scan(self) -> bool:
        return self._use_scan

    @property
    def active_algorithm(self) -> str:
        return self._active.name

    def reset(self) -> None:
        self._active.reset()

    def assign_elevator(
        self,
        passenger: Passenger,
        elevators: list[Elevator],
    ) -> Elevator:
        return self._active.assign_elevator(passenger, elevators)
