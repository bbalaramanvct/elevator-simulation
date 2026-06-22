"""CSV input parsing."""

import csv
from pathlib import Path

from elevator_simulation.models.passenger import PassengerRequest


REQUIRED_COLUMNS = ("time", "passenger_id", "start_floor", "destination_floor")


def load_requests(csv_path: Path) -> list[PassengerRequest]:
    """Load and parse passenger requests from a CSV file."""
    requests: list[PassengerRequest] = []

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file is empty: {csv_path}")

        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        for row_num, row in enumerate(reader, start=2):
            try:
                requests.append(
                    PassengerRequest(
                        time=int(row["time"]),
                        passenger_id=str(row["passenger_id"]).strip(),
                        start_floor=int(row["start_floor"]),
                        destination_floor=int(row["destination_floor"]),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid data on CSV row {row_num}: {row}") from exc

    requests.sort(key=lambda r: (r.time, r.passenger_id))
    return requests
