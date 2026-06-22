"""Generate HTML and optional PNG visualizations for simulation output."""

from __future__ import annotations

import csv
import json
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CORE_ALGORITHMS = ("nearest_car", "round_robin", "scan")


@dataclass
class BenchmarkRow:
    scenario: str
    description: str
    algorithm: str
    avg_wait: float
    max_wait: int
    wait_spread: int
    avg_total: float
    final_time: int


def load_benchmark_csv(path: Path) -> list[BenchmarkRow]:
    rows: list[BenchmarkRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                BenchmarkRow(
                    scenario=row["scenario"],
                    description=row["description"],
                    algorithm=row["algorithm"],
                    avg_wait=float(row["avg_wait"]),
                    max_wait=int(row["max_wait"]),
                    wait_spread=int(row["wait_spread"]),
                    avg_total=float(row["avg_total"]),
                    final_time=int(row["final_time"]),
                )
            )
    return rows


def load_position_log(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    elevator_ids = sorted(
        {
            key.split("_")[1]
            for key in fieldnames
            if key.startswith("elevator_") and key.endswith("_floor")
        },
        key=int,
    )
    return rows, elevator_ids


def _benchmark_payload(rows: list[BenchmarkRow]) -> dict[str, Any]:
    scenarios: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.algorithm not in CORE_ALGORITHMS:
            continue
        bucket = scenarios.setdefault(
            row.scenario,
            {"description": row.description, "algorithms": {}},
        )
        bucket["algorithms"][row.algorithm] = {
            "avg_wait": row.avg_wait,
            "max_wait": row.max_wait,
            "wait_spread": row.wait_spread,
            "avg_total": row.avg_total,
            "final_time": row.final_time,
        }
    return {"scenarios": scenarios}


def generate_benchmark_dashboard(csv_path: Path, output_path: Path) -> Path:
    """Build a self-contained HTML dashboard from benchmark_comparison.csv."""
    rows = load_benchmark_csv(csv_path)
    payload = _benchmark_payload(rows)
    data_json = json.dumps(payload)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Elevator Benchmark Dashboard</title>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a2332;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --grid: #30363d;
      --c0: #58a6ff;
      --c1: #3fb950;
      --c2: #d29922;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header {{
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--grid);
    }}
    h1 {{ margin: 0 0 0.25rem; font-size: 1.35rem; }}
    .subtitle {{ color: var(--muted); font-size: 0.9rem; }}
    main {{ padding: 1.5rem; max-width: 1200px; margin: 0 auto; }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      margin-bottom: 1.5rem;
    }}
    label {{ color: var(--muted); font-size: 0.85rem; }}
    select {{
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--grid);
      padding: 0.45rem 0.65rem;
      border-radius: 6px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1rem;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--grid);
      border-radius: 8px;
      padding: 1rem;
    }}
    .card h2 {{ margin: 0 0 0.35rem; font-size: 1rem; }}
    .card p {{ margin: 0 0 0.75rem; color: var(--muted); font-size: 0.85rem; }}
    canvas {{ width: 100%; height: 220px; display: block; }}
    .legend {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; font-size: 0.8rem; }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
      margin-right: 0.35rem;
    }}
    .scatter-wrap canvas {{ height: 360px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.45rem 0.5rem;
      border-bottom: 1px solid var(--grid);
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    .best {{ color: #3fb950; }}
  </style>
</head>
<body>
  <header>
    <h1>Elevator Algorithm Benchmark Dashboard</h1>
    <p class="subtitle">Source: {csv_path.name} · metrics in discrete time units (ticks)</p>
  </header>
  <main>
    <div class="controls">
      <label for="scenario">Scenario
        <select id="scenario"></select>
      </label>
    </div>
    <div class="grid">
      <div class="card">
        <h2>Average total time (efficiency)</h2>
        <p id="scenario-desc"></p>
        <canvas id="chart-total"></canvas>
        <div class="legend">
          <span style="--swatch:var(--c0)">nearest_car</span>
          <span style="--swatch:var(--c1)">round_robin</span>
          <span style="--swatch:var(--c2)">scan</span>
        </div>
      </div>
      <div class="card">
        <h2>Max wait time (fairness)</h2>
        <p>Worst passenger wait per algorithm — lower is fairer.</p>
        <canvas id="chart-wait"></canvas>
      </div>
    </div>
    <div class="card scatter-wrap" style="margin-top:1rem;">
      <h2>Fairness vs efficiency (all scenarios)</h2>
      <p>Each point is one algorithm in one scenario. Bottom-left is best.</p>
      <canvas id="chart-scatter"></canvas>
    </div>
    <div class="card" style="margin-top:1rem;">
      <h2>Winners by scenario</h2>
      <table id="winners">
        <thead>
          <tr><th>Scenario</th><th>Best efficiency</th><th>Best fairness</th></tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </main>
  <script>
    const DATA = {data_json};
    const ALGS = ["nearest_car", "round_robin", "scan"];
    const COLORS = ["#58a6ff", "#3fb950", "#d29922"];
    const scenarioSelect = document.getElementById("scenario");
    const names = Object.keys(DATA.scenarios).sort();

    names.forEach(name => {{
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      scenarioSelect.appendChild(opt);
    }});

    function drawBars(canvasId, metric, title) {{
      const scenario = scenarioSelect.value;
      const canvas = document.getElementById(canvasId);
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      const w = rect.width, h = rect.height;
      ctx.clearRect(0, 0, w, h);
      const values = ALGS.map(a => DATA.scenarios[scenario].algorithms[a][metric]);
      const maxV = Math.max(...values, 1) * 1.15;
      const pad = {{ l: 40, r: 16, t: 16, b: 36 }};
      const chartW = w - pad.l - pad.r;
      const chartH = h - pad.t - pad.b;
      const barW = chartW / ALGS.length * 0.55;
      ALGS.forEach((alg, i) => {{
        const v = values[i];
        const x = pad.l + (i + 0.5) * (chartW / ALGS.length) - barW / 2;
        const barH = (v / maxV) * chartH;
        const y = pad.t + chartH - barH;
        ctx.fillStyle = COLORS[i];
        ctx.fillRect(x, y, barW, barH);
        ctx.fillStyle = "#8b949e";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(v.toFixed(1), x + barW / 2, y - 4);
        ctx.fillText(alg.replace("_", " "), x + barW / 2, h - 12);
      }});
      ctx.strokeStyle = "#30363d";
      ctx.beginPath();
      ctx.moveTo(pad.l, pad.t + chartH);
      ctx.lineTo(w - pad.r, pad.t + chartH);
      ctx.stroke();
    }}

    function drawScatter() {{
      const canvas = document.getElementById("chart-scatter");
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      const w = rect.width, h = rect.height;
      ctx.clearRect(0, 0, w, h);
      const pad = {{ l: 48, r: 16, t: 16, b: 44 }};
      const points = [];
      names.forEach(sname => {{
        ALGS.forEach((alg, i) => {{
          const a = DATA.scenarios[sname].algorithms[alg];
          points.push({{ x: a.avg_total, y: a.max_wait, alg, sname, color: COLORS[i] }});
        }});
      }});
      const maxX = Math.max(...points.map(p => p.x)) * 1.1;
      const maxY = Math.max(...points.map(p => p.y)) * 1.1;
      const chartW = w - pad.l - pad.r;
      const chartH = h - pad.t - pad.b;
      points.forEach(p => {{
        const x = pad.l + (p.x / maxX) * chartW;
        const y = pad.t + chartH - (p.y / maxY) * chartH;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();
      }});
      ctx.fillStyle = "#8b949e";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Avg total time (ticks)", pad.l + chartW / 2, h - 8);
      ctx.save();
      ctx.translate(14, pad.t + chartH / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText("Max wait (ticks)", 0, 0);
      ctx.restore();
      ctx.strokeStyle = "#30363d";
      ctx.beginPath();
      ctx.moveTo(pad.l, pad.t + chartH);
      ctx.lineTo(w - pad.r, pad.t + chartH);
      ctx.moveTo(pad.l, pad.t);
      ctx.lineTo(pad.l, pad.t + chartH);
      ctx.stroke();
    }}

    function fillWinners() {{
      const tbody = document.querySelector("#winners tbody");
      tbody.innerHTML = "";
      names.forEach(name => {{
        const algs = DATA.scenarios[name].algorithms;
        let bestEff = ALGS[0], bestFair = ALGS[0];
        ALGS.forEach(a => {{
          if (algs[a].avg_total < algs[bestEff].avg_total) bestEff = a;
          if (algs[a].max_wait < algs[bestFair].max_wait) bestFair = a;
        }});
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${{name}}</td><td class="best">${{bestEff}}</td><td class="best">${{bestFair}}</td>`;
        tbody.appendChild(tr);
      }});
    }}

    function refresh() {{
      document.getElementById("scenario-desc").textContent =
        DATA.scenarios[scenarioSelect.value].description;
      drawBars("chart-total", "avg_total");
      drawBars("chart-wait", "max_wait");
      drawScatter();
      fillWinners();
    }}

    scenarioSelect.addEventListener("change", refresh);
    window.addEventListener("resize", refresh);
    refresh();
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def generate_elevator_animation(
    position_csv: Path,
    output_path: Path,
    max_floor: int,
    title: str = "Elevator Simulation",
) -> Path:
    """Build an interactive HTML animation from an elevator position log."""
    rows, elevator_ids = load_position_log(position_csv)
    for row in rows:
        for key, value in row.items():
            if key == "time" or key.endswith("_passengers"):
                row[key] = int(value)
            elif key.endswith("_floor"):
                row[key] = int(value)
    data_json = json.dumps({"rows": rows, "elevator_ids": elevator_ids, "max_floor": max_floor})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: #0f1419;
      color: #e6edf3;
    }}
    header {{ padding: 1rem 1.25rem; border-bottom: 1px solid #30363d; }}
    h1 {{ margin: 0; font-size: 1.2rem; }}
    main {{ display: flex; gap: 1.5rem; padding: 1.25rem; flex-wrap: wrap; }}
    .shafts {{
      display: flex;
      gap: 1.25rem;
      align-items: flex-end;
    }}
    .shaft {{
      position: relative;
      width: 72px;
      background: #1a2332;
      border: 1px solid #30363d;
      border-radius: 6px;
    }}
    .shaft-label {{
      text-align: center;
      font-size: 0.8rem;
      color: #8b949e;
      margin-top: 0.35rem;
    }}
    .floor-label {{
      position: absolute;
      left: -28px;
      font-size: 10px;
      color: #8b949e;
      transform: translateY(50%);
    }}
    .car {{
      position: absolute;
      left: 8px;
      right: 8px;
      height: 22px;
      background: #58a6ff;
      border-radius: 4px;
      transition: bottom 0.15s linear;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 600;
    }}
    .panel {{
      min-width: 260px;
      flex: 1;
    }}
    .controls {{ display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }}
    input[type=range] {{ width: 220px; }}
    .meta {{ color: #8b949e; font-size: 0.85rem; margin-top: 0.75rem; }}
    button {{
      background: #21262d;
      color: #e6edf3;
      border: 1px solid #30363d;
      padding: 0.4rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <header><h1>{title}</h1></header>
  <main>
    <div>
      <div class="shafts" id="shafts"></div>
    </div>
    <div class="panel">
      <div class="controls">
        <button id="play">Play</button>
        <label>Time <input id="time" type="range" min="0" max="0" value="0" /></label>
        <span id="time-label">t=0</span>
      </div>
      <div class="meta" id="meta"></div>
    </div>
  </main>
  <script>
    const DATA = {data_json};
    const shaftHeight = 420;
    const shaftsEl = document.getElementById("shafts");
    const timeInput = document.getElementById("time");
    const timeLabel = document.getElementById("time-label");
    const meta = document.getElementById("meta");
    const playBtn = document.getElementById("play");
    let playing = false;
    let timer = null;

    DATA.elevator_ids.forEach(id => {{
      const wrap = document.createElement("div");
      const shaft = document.createElement("div");
      shaft.className = "shaft";
      shaft.style.height = shaftHeight + "px";
      shaft.dataset.elevatorId = id;
      wrap.appendChild(shaft);
      const label = document.createElement("div");
      label.className = "shaft-label";
      label.textContent = "Elevator " + id;
      wrap.appendChild(label);
      shaftsEl.appendChild(wrap);
      const car = document.createElement("div");
      car.className = "car";
      car.id = "car-" + id;
      shaft.appendChild(car);
    }});

    timeInput.max = DATA.rows.length - 1;

    function floorToBottom(floor) {{
      return (floor / DATA.max_floor) * (shaftHeight - 24);
    }}

    function render(idx) {{
      const row = DATA.rows[idx];
      timeInput.value = idx;
      timeLabel.textContent = "t=" + row.time;
      const parts = [];
      DATA.elevator_ids.forEach(id => {{
        const floor = row["elevator_" + id + "_floor"];
        const dir = row["elevator_" + id + "_direction"];
        const pax = row["elevator_" + id + "_passengers"];
        const car = document.getElementById("car-" + id);
        car.style.bottom = floorToBottom(floor) + "px";
        car.textContent = pax;
        car.title = "Floor " + floor + " · " + dir;
        parts.push("Elev " + id + ": floor " + floor + ", " + dir + ", " + pax + " pax");
      }});
      meta.textContent = parts.join(" · ");
    }}

    timeInput.addEventListener("input", () => render(Number(timeInput.value)));
    playBtn.addEventListener("click", () => {{
      playing = !playing;
      playBtn.textContent = playing ? "Pause" : "Play";
      if (playing) {{
        timer = setInterval(() => {{
          let next = Number(timeInput.value) + 1;
          if (next >= DATA.rows.length) next = 0;
          render(next);
        }}, 200);
      }} else if (timer) {{
        clearInterval(timer);
      }}
    }});
    render(0);
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def generate_matplotlib_charts(csv_path: Path, output_dir: Path) -> list[Path]:
    """Optional PNG charts; requires matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for PNG charts. Install with: pip install matplotlib"
        ) from exc

    rows = load_benchmark_csv(csv_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    scenarios = sorted({r.scenario for r in rows if r.algorithm in CORE_ALGORITHMS})
    for scenario in scenarios:
        subset = [r for r in rows if r.scenario == scenario and r.algorithm in CORE_ALGORITHMS]
        algs = [r.algorithm for r in subset]
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        fig.suptitle(scenario.replace("_", " ").title())

        axes[0].bar(algs, [r.avg_total for r in subset], color=["#58a6ff", "#3fb950", "#d29922"])
        axes[0].set_title("Avg total time (efficiency)")
        axes[0].set_ylabel("Ticks")
        axes[0].tick_params(axis="x", rotation=20)

        axes[1].bar(algs, [r.max_wait for r in subset], color=["#58a6ff", "#3fb950", "#d29922"])
        axes[1].set_title("Max wait (fairness)")
        axes[1].set_ylabel("Ticks")
        axes[1].tick_params(axis="x", rotation=20)

        fig.tight_layout()
        path = output_dir / f"{scenario}_comparison.png"
        fig.savefig(path, dpi=120, facecolor="#0f1419")
        plt.close(fig)
        written.append(path)

    return written


def open_in_browser(path: Path) -> None:
    """Open a file URL in the default browser."""
    webbrowser.open(path.resolve().as_uri())
