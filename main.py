from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from autosort.console_view import render_snapshot
from autosort.controller import build_demo_system
from autosort.ui import run_dashboard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AutoSort Control System - PLC-based package routing simulator"
    )
    parser.add_argument(
        "--mode",
        choices=("console", "ui"),
        default="console",
        help="Choose console output or the Tkinter dashboard.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=18,
        help="Maximum number of PLC scan cycles to run in console mode.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Optional delay between console cycles in seconds.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for deterministic demo behavior.",
    )
    return parser.parse_args()


def run_console(cycles: int, delay: float, seed: int) -> None:
    system = build_demo_system(seed=seed)

    print("\nAutoSort Control System")
    print("=" * 72)
    print("PLC simulation started.\n")

    for _ in range(cycles):
        snapshot = system.process_cycle()
        print(render_snapshot(snapshot))

        if delay > 0:
            time.sleep(delay)

        if not system.has_pending_work():
            print("\nSimulation finished early: all packages cleared from the system.")
            break


def main() -> None:
    args = parse_args()

    if args.mode == "ui":
        run_dashboard(seed=args.seed)
        return

    run_console(cycles=args.cycles, delay=args.delay, seed=args.seed)


if __name__ == "__main__":
    main()
