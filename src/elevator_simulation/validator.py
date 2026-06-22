"""Input validation for passenger requests."""

from elevator_simulation.config import BuildingConfig
from elevator_simulation.models.passenger import PassengerRequest


class ValidationError(Exception):
    """Raised when CSV input fails validation."""


def validate_request(request: PassengerRequest, config: BuildingConfig) -> None:
    """Validate a single passenger request against building constraints."""
    if request.time < 0:
        raise ValidationError(
            f"Passenger {request.passenger_id}: time must be non-negative, got {request.time}"
        )

    if not config.is_valid_floor(request.start_floor):
        raise ValidationError(
            f"Passenger {request.passenger_id}: start floor {request.start_floor} "
            f"is outside valid range [{config.min_floor}, {config.max_floor}]"
        )

    if not config.is_valid_floor(request.destination_floor):
        raise ValidationError(
            f"Passenger {request.passenger_id}: destination floor {request.destination_floor} "
            f"is outside valid range [{config.min_floor}, {config.max_floor}]"
        )

    if request.start_floor == request.destination_floor:
        raise ValidationError(
            f"Passenger {request.passenger_id}: start and destination floors must differ"
        )


def validate_requests(requests: list[PassengerRequest], config: BuildingConfig) -> None:
    """Validate all requests and check for duplicate passenger IDs."""
    seen_ids: set[str] = set()
    for request in requests:
        validate_request(request, config)
        if request.passenger_id in seen_ids:
            raise ValidationError(f"Duplicate passenger id: {request.passenger_id}")
        seen_ids.add(request.passenger_id)
