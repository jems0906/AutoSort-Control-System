from __future__ import annotations

import os
from threading import Lock

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from .controller import build_demo_system

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoSort Control System</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --card: #ffffff;
      --accent: #2457c5;
      --ok: #1f7a1f;
      --warn: #9a5b00;
      --bad: #a32020;
      --muted: #5c6470;
      --border: #d7deea;
    }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: #1e2732;
    }
    .container {
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }
    h1, h2, h3, p { margin-top: 0; }
    .hero, .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 4px 14px rgba(20, 35, 60, 0.06);
    }
    .hero {
      padding: 20px;
      margin-bottom: 16px;
    }
    .grid {
      display: grid;
      gap: 16px;
    }
    .grid-2 {
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    }
    .grid-3 {
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .card {
      padding: 16px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .stat {
      background: #f8faff;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
    }
    .stat strong {
      display: block;
      font-size: 1.2rem;
    }
    .lane-ready { color: var(--ok); font-weight: bold; }
    .lane-blocked { color: var(--bad); font-weight: bold; }
    .muted { color: var(--muted); }
    .pill {
      display: inline-block;
      margin: 4px 6px 0 0;
      padding: 4px 8px;
      border-radius: 999px;
      background: #e9eefb;
      font-size: 0.9rem;
    }
    form.inline, .button-row form {
      display: inline-block;
      margin-right: 8px;
      margin-bottom: 8px;
    }
    input, select, button {
      font: inherit;
      border-radius: 8px;
      border: 1px solid #bcc8db;
      padding: 8px 10px;
    }
    button {
      background: var(--accent);
      color: white;
      border-color: var(--accent);
      cursor: pointer;
    }
    button.secondary {
      background: white;
      color: var(--accent);
    }
    ul.events {
      padding-left: 18px;
      margin-bottom: 0;
    }
    code {
      background: #eef3ff;
      padding: 2px 6px;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <h1>AutoSort Control System</h1>
      <p class="muted">PLC-style package routing simulator deployed as a Render-friendly web app.</p>
      <div class="stats">
        <div class="stat"><span>Cycle</span><strong>{{ snapshot.cycle }}</strong></div>
        <div class="stat"><span>Inbound</span><strong>{{ snapshot.inbound_count }}</strong></div>
        <div class="stat"><span>Completed</span><strong>{{ snapshot.completed_count }}</strong></div>
        <div class="stat"><span>Errors</span><strong>{{ snapshot.error_count }}</strong></div>
      </div>
    </section>

    <section class="grid grid-2">
      <div class="card">
        <h2>Operator Controls</h2>
        <div class="button-row">
          <form action="{{ url_for('step') }}" method="post" class="inline"><button type="submit">Next Cycle</button></form>
          <form action="{{ url_for('auto_run') }}" method="post" class="inline">
            <input type="hidden" name="cycles" value="3">
            <button type="submit">Auto Run x3</button>
          </form>
          <form action="{{ url_for('reset') }}" method="post" class="inline"><button type="submit" class="secondary">Reset</button></form>
        </div>

        <h3>Inject by destination</h3>
        <form action="{{ url_for('inject') }}" method="post">
          <select name="destination">
            <option value="X">X</option>
            <option value="Y">Y</option>
            <option value="Z">Z</option>
            <option value="Q">Q (invalid)</option>
          </select>
          <button type="submit">Inject Package</button>
        </form>

        <h3>Scan barcode</h3>
        <form action="{{ url_for('scan') }}" method="post">
          <input name="barcode" value="BC-Y-501" aria-label="barcode input">
          <button type="submit">Scan Barcode</button>
        </form>

        <p class="muted">Examples: <code>BC-X-111</code>, <code>BC-Z-222</code>, <code>BAD-UNKNOWN-01</code>.</p>
      </div>

      <div class="card">
        <h2>Throughput KPIs</h2>
        <div class="stats">
          {% for key, value in snapshot.stats.items() %}
          <div class="stat"><span>{{ key.replace('_', ' ') }}</span><strong>{{ value }}</strong></div>
          {% endfor %}
        </div>
      </div>
    </section>

    <section class="grid grid-3" style="margin-top: 16px;">
      {% for lane_id, lane in snapshot.lanes.items() %}
      <div class="card">
        <h2>Lane {{ lane_id }}</h2>
        <p>Status:
          {% if lane.blocked %}
          <span class="lane-blocked">BLOCKED</span>
          {% else %}
          <span class="lane-ready">READY</span>
          {% endif %}
        </p>
        <p>Load: <strong>{{ lane.load }}/{{ lane.capacity }}</strong></p>
        <p>Destinations:
          {% for dest in lane.destinations %}
          <span class="pill">{{ dest }}</span>
          {% endfor %}
        </p>
        <p>Packages:
          {% if lane.packages %}
            {% for pkg in lane.packages %}<span class="pill">{{ pkg }}</span>{% endfor %}
          {% else %}
            <span class="muted">No packages in lane</span>
          {% endif %}
        </p>
        <form action="{{ url_for('toggle_lane', lane_id=lane_id) }}" method="post">
          <button type="submit" class="secondary">Toggle Lane {{ lane_id }}</button>
        </form>
      </div>
      {% endfor %}
    </section>

    <section class="grid grid-2" style="margin-top: 16px;">
      <div class="card">
        <h2>Inbound Queue</h2>
        {% if snapshot.inbound_packages %}
          {% for pkg in snapshot.inbound_packages %}<span class="pill">{{ pkg }}</span>{% endfor %}
        {% else %}
          <p class="muted">Inbound queue is empty.</p>
        {% endif %}
      </div>

      <div class="card">
        <h2>Exception Bin</h2>
        {% if snapshot.error_packages %}
          {% for pkg in snapshot.error_packages %}<span class="pill">{{ pkg }}</span>{% endfor %}
        {% else %}
          <p class="muted">No current exceptions.</p>
        {% endif %}
      </div>
    </section>

    <section class="card" style="margin-top: 16px;">
      <h2>Recent PLC Events</h2>
      <ul class="events">
        {% for item in snapshot.history[-8:] %}
        <li>{{ item }}</li>
        {% endfor %}
      </ul>
    </section>
  </div>
</body>
</html>
"""


def create_app(seed: int = 7) -> Flask:
    app = Flask(__name__)
    app.config["SORT_SYSTEM"] = build_demo_system(seed=seed)
    app.config["SORT_SEED"] = seed
    lock = Lock()

    def get_system():
        return app.config["SORT_SYSTEM"]

    @app.get("/")
    def index():
        with lock:
            snapshot = get_system().snapshot()
        return render_template_string(PAGE_TEMPLATE, snapshot=snapshot)

    @app.post("/step")
    def step():
        with lock:
            get_system().process_cycle()
        return redirect(url_for("index"))

    @app.post("/auto-run")
    def auto_run():
        cycles = max(1, min(int(request.form.get("cycles", 3)), 10))
        with lock:
            system = get_system()
            for _ in range(cycles):
                system.process_cycle()
                if not system.has_pending_work():
                    break
        return redirect(url_for("index"))

    @app.post("/reset")
    def reset():
        with lock:
            app.config["SORT_SYSTEM"] = build_demo_system(seed=app.config["SORT_SEED"])
        return redirect(url_for("index"))

    @app.post("/inject")
    def inject():
        destination = request.form.get("destination", "X").strip().upper() or "X"
        with lock:
            get_system().add_package(destination)
        return redirect(url_for("index"))

    @app.post("/scan")
    def scan():
        barcode = request.form.get("barcode", "")
        with lock:
            get_system().add_package_from_barcode(barcode)
        return redirect(url_for("index"))

    @app.post("/toggle/<lane_id>")
    def toggle_lane(lane_id: str):
        with lock:
            get_system().toggle_lane_block(lane_id.upper())
        return redirect(url_for("index"))

    @app.get("/healthz")
    def healthz():
        with lock:
            snapshot = get_system().snapshot()
        return jsonify(
            status="ok",
            cycle=snapshot["cycle"],
            inbound=snapshot["inbound_count"],
            completed=snapshot["completed_count"],
            errors=snapshot["error_count"],
        )

    return app


app = create_app(seed=int(os.environ.get("AUTOSORT_SEED", "7")))


def run_web_app(seed: int = 7, host: str = "0.0.0.0", port: int | None = None) -> None:
    web_app = create_app(seed=seed)
    port = port or int(os.environ.get("PORT", "10000"))
    web_app.run(host=host, port=port, debug=False)
