from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .controller import build_demo_system


class AutoSortDashboard:
    def __init__(self, seed: int = 7) -> None:
        self.seed = seed
        self.system = build_demo_system(seed=self.seed)
        self.auto_running = False

        self.root = tk.Tk()
        self.root.title("AutoSort Control System")
        self.root.geometry("980x720")
        self.root.configure(padx=12, pady=12)

        self.summary_var = tk.StringVar()
        self.stats_var = tk.StringVar()
        self.error_var = tk.StringVar()
        self.event_var = tk.StringVar()
        self.operator_note_var = tk.StringVar(
            value="Operator panel ready. Try a destination inject or a barcode scan."
        )
        self.destination_var = tk.StringVar(value="X")
        self.barcode_var = tk.StringVar(value="BC-X-MANUAL-101")
        self.lane_vars: dict[str, tk.StringVar] = {}

        self._build_layout()
        self._refresh_view()

    def _build_layout(self) -> None:
        header = ttk.Label(
            self.root,
            text="PLC-Based Package Routing Simulator",
            font=("Segoe UI", 16, "bold"),
        )
        header.pack(anchor="w", pady=(0, 10))

        summary = ttk.Label(
            self.root,
            textvariable=self.summary_var,
            font=("Consolas", 11),
        )
        summary.pack(anchor="w", pady=(0, 10))

        operator_frame = ttk.LabelFrame(self.root, text="Operator Panel")
        operator_frame.pack(fill="x", pady=(0, 12))
        operator_frame.columnconfigure(1, weight=1)

        ttk.Label(operator_frame, text="Destination").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Combobox(
            operator_frame,
            textvariable=self.destination_var,
            values=("X", "Y", "Z", "Q"),
            state="readonly",
            width=10,
        ).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(
            operator_frame,
            text="Inject Package",
            command=self.add_manual_destination,
        ).grid(row=0, column=2, padx=6, pady=6, sticky="w")

        ttk.Label(operator_frame, text="Barcode Input").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(
            operator_frame,
            textvariable=self.barcode_var,
            width=28,
        ).grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        ttk.Button(
            operator_frame,
            text="Scan Barcode",
            command=self.add_barcode_package,
        ).grid(row=1, column=2, padx=6, pady=6, sticky="w")
        ttk.Label(
            operator_frame,
            text="Examples: BC-Y-501 routes to Lane B, BAD-UNKNOWN-01 forces a misread.",
            font=("Segoe UI", 9),
        ).grid(row=2, column=0, columnspan=3, padx=6, pady=(0, 6), sticky="w")

        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", pady=(0, 12))

        ttk.Button(control_frame, text="Next Cycle", command=self.step).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Auto Run", command=self.start_auto_run).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Stop", command=self.stop_auto_run).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Reset", command=self.reset).pack(side="left", padx=4)

        ttk.Label(control_frame, text="   Simulate jam:").pack(side="left", padx=(12, 2))
        for lane_id in ("A", "B", "C"):
            ttk.Button(
                control_frame,
                text=f"Toggle Lane {lane_id}",
                command=lambda lid=lane_id: self.toggle_lane(lid),
            ).pack(side="left", padx=4)

        ttk.Label(
            self.root,
            textvariable=self.operator_note_var,
            justify="left",
            font=("Segoe UI", 9, "italic"),
            foreground="#1f4e79",
        ).pack(anchor="w", pady=(0, 10))

        lane_frame = ttk.Frame(self.root)
        lane_frame.pack(fill="x", pady=(0, 12))

        for lane_id in ("A", "B", "C"):
            card = ttk.LabelFrame(lane_frame, text=f"Lane {lane_id}")
            card.pack(side="left", expand=True, fill="both", padx=4)
            lane_var = tk.StringVar()
            self.lane_vars[lane_id] = lane_var
            ttk.Label(
                card,
                textvariable=lane_var,
                justify="left",
                font=("Consolas", 10),
            ).pack(anchor="w", padx=10, pady=10)

        ttk.Label(
            self.root,
            textvariable=self.stats_var,
            justify="left",
            font=("Consolas", 10),
        ).pack(anchor="w", pady=(0, 10))

        ttk.Label(
            self.root,
            textvariable=self.error_var,
            justify="left",
            font=("Consolas", 10),
            foreground="#8b0000",
        ).pack(anchor="w", pady=(0, 10))

        events = ttk.LabelFrame(self.root, text="Recent PLC Events")
        events.pack(fill="both", expand=True)
        ttk.Label(
            events,
            textvariable=self.event_var,
            justify="left",
            font=("Consolas", 10),
        ).pack(anchor="w", padx=10, pady=10)

    def _refresh_view(self) -> None:
        snapshot = self.system.snapshot()
        self.summary_var.set(
            (
                f"Cycle: {snapshot['cycle']}    Inbound Queue: {snapshot['inbound_count']}    "
                f"Completed: {snapshot['completed_count']}    Errors: {snapshot['error_count']}"
            )
        )

        for lane_id, lane in snapshot["lanes"].items():
            if lane_id not in self.lane_vars:
                continue
            fill_bar = "█" * lane["load"] + "░" * max(0, lane["capacity"] - lane["load"])
            packages = ", ".join(lane["packages"]) if lane["packages"] else "-"
            destinations = ", ".join(lane["destinations"])
            state = "BLOCKED" if lane["blocked"] else "READY"
            control_mode = "MANUAL" if lane["manual_override"] is not None else "SCHEDULED"
            self.lane_vars[lane_id].set(
                (
                    f"Destinations : {destinations}\n"
                    f"State        : {state}\n"
                    f"Control      : {control_mode}\n"
                    f"Load         : {lane['load']}/{lane['capacity']}  {fill_bar}\n"
                    f"Packages     : {packages}"
                )
            )

        stats = snapshot["stats"]
        self.stats_var.set(
            (
                f"KPIs -> routed={stats['routed']} | released={stats['released']} | "
                f"requeued={stats['requeued']} | buildup={stats['queue_buildup']} | "
                f"misread={stats['misread']} | blocked={stats['blocked_lane']} | "
                f"lane_overflow={stats['lane_overflow']} | inbound_overflow={stats['inbound_overflow']}"
            )
        )

        errors = ", ".join(snapshot["error_packages"]) if snapshot["error_packages"] else "-"
        self.error_var.set(f"Exception Handling Bin: {errors}")
        events = snapshot["history"][-8:] or ["System ready."]
        self.event_var.set("\n".join(f"• {event}" for event in events))

    def add_manual_destination(self) -> None:
        destination = self.destination_var.get().strip().upper() or "Q"
        accepted = self.system.add_package(destination)
        if accepted:
            self.operator_note_var.set(
                f"Injected package for destination {destination}. Advance the PLC cycle to route it."
            )
        else:
            self.operator_note_var.set("Inbound queue full; manual inject diverted to exception handling.")
        self._refresh_view()

    def add_barcode_package(self) -> None:
        barcode = self.barcode_var.get().strip()
        accepted = self.system.add_package_from_barcode(barcode)
        if accepted:
            self.operator_note_var.set(f"Scanned barcode '{barcode}'. Package added to the inbound queue.")
        else:
            self.operator_note_var.set("Inbound queue full; barcode scan could not be admitted.")
        self._refresh_view()

    def toggle_lane(self, lane_id: str) -> None:
        is_blocked = self.system.toggle_lane_block(lane_id)
        state = "BLOCKED" if is_blocked else "READY"
        self.operator_note_var.set(f"Lane {lane_id} manually toggled to {state}.")
        self._refresh_view()

    def step(self) -> None:
        self.system.process_cycle()
        self._refresh_view()
        if not self.system.has_pending_work():
            self.auto_running = False
            self.operator_note_var.set("Simulation idle: all packages have cleared the system.")

    def start_auto_run(self) -> None:
        if self.auto_running:
            return
        self.auto_running = True
        self.operator_note_var.set("Automatic PLC scan cycle started.")
        self._auto_step()

    def _auto_step(self) -> None:
        if not self.auto_running:
            return
        self.step()
        if self.auto_running and self.system.has_pending_work():
            self.root.after(650, self._auto_step)

    def stop_auto_run(self) -> None:
        self.auto_running = False
        self.operator_note_var.set("Automatic run stopped by operator.")

    def reset(self) -> None:
        self.auto_running = False
        self.system = build_demo_system(seed=self.seed)
        self.operator_note_var.set("System reset complete. Demo manifest reloaded.")
        self._refresh_view()


def run_dashboard(seed: int = 7) -> None:
    dashboard = AutoSortDashboard(seed=seed)
    dashboard.root.mainloop()
