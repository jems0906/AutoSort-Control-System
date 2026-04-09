from __future__ import annotations


def render_snapshot(snapshot: dict) -> str:
    lines = [
        "-" * 72,
        (
            f"Cycle {snapshot['cycle']:>2} | Inbound: {snapshot['inbound_count']:<2} "
            f"| Completed: {snapshot['completed_count']:<2} | Errors: {snapshot['error_count']:<2}"
        ),
        "-" * 72,
        f"{'Lane':<8}{'State':<10}{'Load':<8}{'Cap':<6}Packages",
    ]

    for lane_id, lane in snapshot["lanes"].items():
        state = "BLOCKED" if lane["blocked"] else "READY"
        packages = ", ".join(lane["packages"]) if lane["packages"] else "-"
        lines.append(
            f"{lane_id:<8}{state:<10}{lane['load']:<8}{lane['capacity']:<6}{packages}"
        )

    inbound = ", ".join(snapshot["inbound_packages"]) if snapshot["inbound_packages"] else "-"
    errors = ", ".join(snapshot["error_packages"]) if snapshot["error_packages"] else "-"

    lines.extend(
        [
            "",
            f"Inbound queue : {inbound}",
            f"Exception bin: {errors}",
            "Recent PLC events:",
        ]
    )

    for event in snapshot["history"][-4:]:
        lines.append(f"  • {event}")

    stats = snapshot["stats"]
    lines.extend(
        [
            "",
            (
                "KPIs -> "
                f"enqueued={stats['enqueued']}, routed={stats['routed']}, released={stats['released']}, "
                f"requeued={stats['requeued']}, buildup={stats['queue_buildup']}, misread={stats['misread']}, "
                f"blocked={stats['blocked_lane']}, lane_overflow={stats['lane_overflow']}, "
                f"inbound_overflow={stats['inbound_overflow']}"
            ),
        ]
    )

    return "\n".join(lines)
