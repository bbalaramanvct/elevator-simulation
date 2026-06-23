# Elevator Simulation

A discrete-time Python simulation of multiple elevators serving passenger requests in a configurable building. Each time unit represents one floor of travel (up or down). The simulation compares standard dispatch algorithms and reports passenger wait and total travel times.

## Features

- **Discrete time model**: time advances one unit per tick; one unit equals one floor of movement
- **Object-oriented design**: `Elevator`, `Passenger`, `BuildingConfig`, and scheduler classes
- **Configurable building**: number of elevators, floor range, and elevator capacity
- **CSV input**: passenger requests with arrival time, ID, start floor, and destination
- **Input validation**: floors must be within building bounds; start and destination must differ
- **Dispatch algorithms**:
  - **Nearest car**: assigns the elevator with the lowest estimated cost to reach the passenger
  - **Round robin**: rotates assignments across elevators
  - **SCAN**: direction-aware sweep; prefers cars already moving toward the passenger
  - **Rush-hour adaptive** (optional): uses SCAN during local peak windows, nearest car off-peak
- **Per-timestep logging**: one CSV row per time step with every elevator's floor, direction, and load
- **Statistics**: min, max, and average wait time and total time per algorithm

## Project Structure

```
elevator-simulation/
├── main.py                          # CLI entry point
├── data/
│   ├── sample_requests.csv
│   └── scenarios/                 # Benchmark input scenarios
├── run_benchmarks.py              # Compare algorithms across scenarios
├── tests/test_algorithm_evaluation.py
├── output/                          # Generated logs and summaries (created at runtime)
└── src/elevator_simulation/
    ├── config.py                    # Building configuration
    ├── csv_reader.py                # CSV parsing
    ├── validator.py                 # Input validation
    ├── simulation.py                # Discrete-time engine
    ├── stats.py                     # Result aggregation
    ├── visualize.py                 # Visual stats
    ├── models/
    │   ├── elevator.py
    │   └── passenger.py
    └── schedulers/
        ├── base.py
        ├── nearest_car.py
        ├── round_robin.py
        ├── scan.py
        └── rush_hour.py
```

## Requirements

- Python 3.10 or newer
- Standard library only (no third-party dependencies)

## How to Run

From the project root:

```bash
python main.py data/sample_requests.csv --max-floor 10
```

On Windows, if `python` is not on your PATH, use the launcher:

```bash
py -3 main.py data/sample_requests.csv --max-floor 10
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `csv_file` | (required) | Path to passenger request CSV |
| `--elevators` | `2` | Number of elevator cars |
| `--min-floor` | `0` | Lowest floor in the building |
| `--max-floor` | (required) | Highest floor in the building |
| `--capacity` | `8` | Max passengers per elevator |
| `--output-dir` | `output` | Directory for logs and summary |
| `--algorithms` | `all` | `nearest_car`, `round_robin`, `scan`, `rush_hour`, or `all` |
| `--rush-hour-scan` | off | Add rush-hour adaptive mode when using `--algorithms all` |
| `--rush-hour-fallback` | `nearest_car` | Off-peak algorithm for rush-hour mode (`nearest_car` or `round_robin`) |

Rush-hour windows use **local system time** at program start (end exclusive):

- 08:00–10:00
- 12:00–13:00
- 16:00–18:00

During these windows, rush-hour mode selects **SCAN**; otherwise it uses the fallback algorithm.

### Examples

Run both algorithms on the sample data with three elevators:

```bash
python main.py data/sample_requests.csv --max-floor 10 --elevators 3 --algorithms all
```

Run only nearest-car dispatch:

```bash
python main.py data/sample_requests.csv --max-floor 10 --algorithms nearest_car
```

Run SCAN dispatch:

```bash
python main.py data/sample_requests.csv --max-floor 10 --algorithms scan
```

Run rush-hour adaptive mode (SCAN if local time is in a peak window):

```bash
python main.py data/sample_requests.csv --max-floor 10 --algorithms rush_hour
```

Include rush-hour mode alongside all standard algorithms:

```bash
python main.py data/sample_requests.csv --max-floor 10 --algorithms all --rush-hour-scan
```

Building with basement floors:

```bash
python main.py data/sample_requests.csv --min-floor -2 --max-floor 10 --elevators 2
```

## Input CSV Format

Required columns:

| Column | Type | Description |
|--------|------|-------------|
| `time` | integer | Discrete time step when the request arrives |
| `passenger_id` | string | Unique passenger identifier |
| `start_floor` | integer | Floor where the passenger waits |
| `destination_floor` | integer | Target floor (cannot equal start floor) |

Example:

```csv
time,passenger_id,start_floor,destination_floor
0,P001,0,5
2,P002,3,8
```

## Output

For each algorithm, the program writes:

1. **`output/elevator_positions_<algorithm>.csv`** — one row per time step:

   ```csv
   time,elevator_0_floor,elevator_0_direction,elevator_0_passengers,...
   0,0,IDLE,0,...
   1,1,UP,0,...
   ```

2. **`output/simulation_summary.txt`** — aggregate and per-passenger statistics:

   - Wait time: request until boarding
   - Travel time: boarding until arrival at destination
   - Total time: wait + travel

Console output mirrors the summary file.

## Algorithm Benchmarks

Eight built-in scenarios stress different traffic patterns (morning rush, evening rush, sparse, bursty, fairness outlier, bidirectional, high-rise, capacity stress).

Run all scenarios and generate comparison reports:

```bash
py -3 run_benchmarks.py
```

Run selected scenarios only:

```bash
py -3 run_benchmarks.py --scenario morning_rush fairness_outlier capacity_stress
```

Output:

- `output/benchmarks/benchmark_comparison.txt` — readable table per scenario with best algorithm per metric
- `output/benchmarks/benchmark_comparison.csv` — full stats for spreadsheet analysis

Metrics include **avg wait**, **max wait**, **wait spread** (fairness), **avg total time** (efficiency), and **simulation end time**.

Run automated evaluation tests:

```bash
py -3 -m pip install -r requirements-dev.txt
py -3 -m pytest tests/test_algorithm_evaluation.py -v
```

### Scenario summary (example findings)

| Scenario | Best for efficiency | Best for fairness (max wait) |
|----------|---------------------|------------------------------|
| Morning rush | nearest_car / scan | nearest_car |
| Evening rush | round_robin | round_robin |
| Capacity stress | round_robin | round_robin |
| High rise | nearest_car / scan | nearest_car |
| Fairness outlier | all tied (instant pickup) | all tied |

No single algorithm wins every scenario — use benchmarks to pick based on your building's traffic profile.

## Visualization

Generate interactive HTML dashboards from benchmark and simulation output:

```bash
# Benchmark bar charts + fairness vs efficiency scatter plot
py -3 run_benchmarks.py --visualize --open

# Or generate from existing CSV
py -3 visualize.py --benchmark-csv output/benchmarks/benchmark_comparison.csv --open

# Elevator shaft animation from a position log
py -3 visualize.py --position-csv output/elevator_positions_scan.csv --max-floor 51 --open

# Optional PNG charts (requires matplotlib)
py -3 -m pip install -r requirements-viz.txt
py -3 visualize.py --benchmark-csv output/benchmarks/benchmark_comparison.csv --png
```

Output files:

| File | Description |
|------|-------------|
| `output/visualizations/benchmark_dashboard.html` | Scenario picker, efficiency/fairness charts, winner table |
| `output/visualizations/*_animation.html` | Play/pause elevator movement over time |
| `output/visualizations/png/*.png` | Static per-scenario comparison charts |

### Cursor Canvas

Open [elevator-benchmarks](C:\Users\bvchi\.cursor\projects\c-Users-bvchi-Projects-elevator-simulation\canvases\elevator-benchmarks.canvas.tsx) beside the chat for an interactive summary of key benchmark scenarios (bar charts and winner table). A **Canvas** is a live React panel in the IDE — useful for exploring results without leaving the editor.

### Using MCP in Cursor

Visualization has been enhanced with Cursor MCP servers:

| MCP server | How it helps |
|------------|--------------|
| **cursor-app-control** (`open_resource`) | Open `benchmark_dashboard.html` or animation HTML in Glass beside the chat: `open_resource` with a `file://` URI |
| **cursor-ide-browser** | Navigate to the dashboard, take screenshots, or verify charts render correctly after changes |

Example agent workflow:

1. Run `py -3 run_benchmarks.py --visualize`
2. Use MCP `open_resource` to open `output/benchmarks/benchmark_dashboard.html`
3. Use **cursor-ide-browser** to snapshot the page for sharing or regression checks

MCP does not replace the Python visualizer — it **surfaces** the generated HTML in Cursor's UI. For repeatable charts in CI, use `--png` or the CSV output.

# Time taken to finish

3 hours approximately

## Assumptions Made

1. At each time step `t`, new requests with `time == t` are assigned to an elevator immediately.
2. Each elevator moves at most one floor per tick toward its next stop.
3. When an elevator reaches a stop floor, passengers alight and board (instantaneous).
4. A passenger's destination cannot change after assignment.
5. Elevators respect capacity limits; full cars skip additional pickups.
6. Rush-hour windows use **local system time** at program start (end exclusive):

- 08:00–10:00
- 12:00–13:00
- 16:00–18:00

## Planned Improvements

1. **Priority requests**: support emergency or accessibility-priority passengers.
2. **Dynamic rebalancing**: idle elevators reposition to high-traffic floors during quiet periods.
3. **Peak/off-peak profiles**: load request patterns from historical CSV datasets for stress testing.
4. **Multi-objective scoring**: compare algorithms on fairness metrics (e.g. max wait time) in addition to averages.
5. **Configurable cost functions**: let nearest-car use weighted costs for wait time vs. energy use.

## License

MIT
