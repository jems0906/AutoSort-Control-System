from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from random import Random
from typing import Deque


class FaultCode(str, Enum):
    MISREAD = "misread"
    BLOCKED_LANE = "blocked_lane"
    LANE_OVERFLOW = "lane_overflow"
    INBOUND_OVERFLOW = "inbound_overflow"


@dataclass(slots=True)
class Package:
    package_id: str
    destination: str
    barcode: str
    forced_scan: str | None = None
    retries: int = 0
    status: str = "queued"
    fault: str | None = None


@dataclass
class Lane:
    lane_id: str
    capacity: int
    accepted_destinations: set[str]
    queue: Deque[Package] = field(default_factory=deque)
    blocked: bool = False
    total_released: int = 0

    def release(self, count: int) -> list[Package]:
        released: list[Package] = []
        for _ in range(min(count, len(self.queue))):
            package = self.queue.popleft()
            package.status = "complete"
            released.append(package)
        self.total_released += len(released)
        return released


@dataclass(slots=True)
class SortationConfig:
    inbound_capacity: int = 10
    retry_limit: int = 2
    scanner_accuracy: float = 0.90
    lane_release_rate: int = 1


class SortationSystem:
    def __init__(
        self,
        route_table: dict[str, str] | None = None,
        lane_capacities: dict[str, int] | None = None,
        config: SortationConfig | None = None,
        seed: int = 7,
        blocked_schedule: dict[str, set[int]] | None = None,
    ) -> None:
        self.random = Random(seed)
        self.config = config or SortationConfig()
        self.route_table = {k.upper(): v for k, v in (route_table or {"X": "A", "Y": "B", "Z": "C"}).items()}
        capacities = lane_capacities or {}

        self.lanes: dict[str, Lane] = {}
        for lane_id in sorted(set(self.route_table.values())):
            accepted = {dest for dest, target in self.route_table.items() if target == lane_id}
            self.lanes[lane_id] = Lane(
                lane_id=lane_id,
                capacity=capacities.get(lane_id, 3),
                accepted_destinations=accepted,
            )

        self.inbound_queue: Deque[Package] = deque()
        self.error_bin: list[Package] = []
        self.completed: list[Package] = []
        self.history: Deque[str] = deque(maxlen=10)
        self.blocked_schedule = {lane_id: set(cycles) for lane_id, cycles in (blocked_schedule or {}).items()}
        self.manual_blocked: dict[str, bool | None] = {lane_id: None for lane_id in self.lanes}
        self.package_counter = 1
        self.cycle = 0

        self.stats = {
            "enqueued": 0,
            "routed": 0,
            "released": 0,
            "requeued": 0,
            "queue_buildup": 0,
            "misread": 0,
            "blocked_lane": 0,
            "lane_overflow": 0,
            "inbound_overflow": 0,
        }

    def make_package(
        self,
        destination: str,
        barcode: str | None = None,
        forced_scan: str | None = None,
    ) -> Package:
        destination = destination.strip().upper()
        package = Package(
            package_id=f"PKG-{self.package_counter:03d}",
            destination=destination,
            barcode=barcode or f"BC-{destination}-{self.package_counter:03d}",
            forced_scan=forced_scan,
        )
        self.package_counter += 1
        return package

    def add_package(
        self,
        destination: str,
        barcode: str | None = None,
        forced_scan: str | None = None,
    ) -> bool:
        return self.enqueue(self.make_package(destination, barcode, forced_scan))

    def enqueue(self, package: Package) -> bool:
        if len(self.inbound_queue) >= self.config.inbound_capacity:
            package.status = "error"
            package.fault = FaultCode.INBOUND_OVERFLOW.value
            self.error_bin.append(package)
            self.stats[FaultCode.INBOUND_OVERFLOW.value] += 1
            self._log(
                f"Inbound queue at limit; {package.package_id} diverted before scan."
            )
            return False

        self.inbound_queue.append(package)
        self.stats["enqueued"] += 1
        self._log(
            f"{package.package_id} entered the system for destination {package.destination}."
        )
        return True

    def set_lane_blocked(self, lane_id: str, blocked: bool | None) -> None:
        if lane_id not in self.lanes:
            raise KeyError(f"Unknown lane: {lane_id}")
        self.manual_blocked[lane_id] = blocked
        if blocked is not None:
            self.lanes[lane_id].blocked = blocked
            self._log(
                f"Operator forced Lane {lane_id} to {'BLOCKED' if blocked else 'READY'} state."
            )

    def toggle_lane_block(self, lane_id: str) -> bool:
        if lane_id not in self.lanes:
            raise KeyError(f"Unknown lane: {lane_id}")

        effective_state = self.lanes[lane_id].blocked
        new_state = not effective_state
        self.set_lane_blocked(lane_id, new_state)
        return new_state

    def add_package_from_barcode(self, barcode_text: str) -> bool:
        normalized = barcode_text.strip().upper()
        if not normalized:
            normalized = "BAD-MANUAL-EMPTY"

        if normalized.startswith("BAD"):
            return self.add_package("UNK", barcode=normalized, forced_scan="MISREAD")

        destination = self._decode_barcode_destination(normalized)
        if destination is None:
            return self.add_package("UNK", barcode=normalized, forced_scan="MISREAD")

        return self.add_package(destination, barcode=normalized, forced_scan=destination)

    def has_pending_work(self) -> bool:
        return bool(self.inbound_queue or any(lane.queue for lane in self.lanes.values()))

    def process_cycle(self) -> dict:
        self.cycle += 1
        self._apply_lane_constraints()
        self._release_lane_capacity()

        if self.inbound_queue:
            package = self.inbound_queue.popleft()
            self._scan_and_route(package)
        else:
            self._log("No package at the infeed sensor; PLC remains idle.")

        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "cycle": self.cycle,
            "inbound_count": len(self.inbound_queue),
            "inbound_packages": [package.package_id for package in self.inbound_queue],
            "completed_count": len(self.completed),
            "error_count": len(self.error_bin),
            "error_packages": [
                f"{package.package_id}:{package.fault}" for package in self.error_bin[-5:]
            ],
            "lanes": {
                lane_id: {
                    "blocked": lane.blocked,
                    "load": len(lane.queue),
                    "capacity": lane.capacity,
                    "packages": [package.package_id for package in lane.queue],
                    "destinations": sorted(lane.accepted_destinations),
                    "manual_override": self.manual_blocked.get(lane_id),
                }
                for lane_id, lane in self.lanes.items()
            },
            "stats": dict(self.stats),
            "history": list(self.history),
        }

    def _apply_lane_constraints(self) -> None:
        for lane_id, lane in self.lanes.items():
            was_blocked = lane.blocked
            override = self.manual_blocked.get(lane_id)
            lane.blocked = override if override is not None else self.cycle in self.blocked_schedule.get(lane_id, set())

            if lane.blocked != was_blocked:
                if lane.blocked:
                    self._log(f"Lane {lane_id} blocked by downstream accumulation sensor.")
                else:
                    self._log(f"Lane {lane_id} cleared and returned to service.")

    def _release_lane_capacity(self) -> None:
        if self.config.lane_release_rate <= 0:
            return

        for lane in self.lanes.values():
            if lane.blocked or not lane.queue:
                continue

            released = lane.release(self.config.lane_release_rate)
            if not released:
                continue

            self.completed.extend(released)
            self.stats["released"] += len(released)
            released_ids = ", ".join(package.package_id for package in released)
            self._log(
                f"Lane {lane.lane_id} discharged {len(released)} package(s): {released_ids}."
            )

    def _scan_and_route(self, package: Package) -> None:
        scanned_destination = self._scan_destination(package)

        if scanned_destination is None or scanned_destination not in self.route_table:
            package.status = "error"
            package.fault = FaultCode.MISREAD.value
            self.error_bin.append(package)
            self.stats[FaultCode.MISREAD.value] += 1
            self._log(
                f"{package.package_id} could not be read correctly and moved to exception handling."
            )
            return

        target_lane = self.lanes[self.route_table[scanned_destination]]

        if target_lane.blocked:
            self._manage_constraint(
                package=package,
                fault=FaultCode.BLOCKED_LANE,
                reason=f"Lane {target_lane.lane_id} is blocked",
            )
            return

        if len(target_lane.queue) >= target_lane.capacity:
            self._manage_constraint(
                package=package,
                fault=FaultCode.LANE_OVERFLOW,
                reason=f"Lane {target_lane.lane_id} is at capacity",
            )
            return

        package.status = f"routed:{target_lane.lane_id.lower()}"
        target_lane.queue.append(package)
        self.stats["routed"] += 1
        self._log(
            f"{package.package_id} scanned as {scanned_destination} and routed to Lane {target_lane.lane_id}."
        )

    def _manage_constraint(self, package: Package, fault: FaultCode, reason: str) -> None:
        self.stats[fault.value] += 1

        if (
            package.retries < self.config.retry_limit
            and len(self.inbound_queue) < self.config.inbound_capacity
        ):
            package.retries += 1
            package.status = "requeued"
            self.inbound_queue.append(package)
            self.stats["requeued"] += 1
            self.stats["queue_buildup"] += 1
            self._log(
                f"{reason}; {package.package_id} requeued (attempt {package.retries}/{self.config.retry_limit})."
            )
            return

        package.status = "error"
        package.fault = fault.value
        self.error_bin.append(package)
        self._log(f"{reason}; {package.package_id} diverted to the exception lane.")

    def _decode_barcode_destination(self, barcode_text: str) -> str | None:
        if barcode_text in self.route_table:
            return barcode_text

        normalized = barcode_text.replace(":", "-").replace("_", "-").replace(" ", "-")
        tokens = [token for token in normalized.split("-") if token]
        for token in reversed(tokens):
            if token in self.route_table:
                return token
        return None

    def _scan_destination(self, package: Package) -> str | None:
        if package.forced_scan is not None:
            forced_scan = package.forced_scan.strip().upper()
            return None if forced_scan in {"", "MISREAD", "NONE"} else forced_scan

        if package.barcode.strip().upper().startswith("BAD"):
            return None

        if self.random.random() > self.config.scanner_accuracy:
            return None

        return package.destination.strip().upper()

    def _log(self, message: str) -> None:
        self.history.append(f"C{self.cycle:02d}: {message}")


def build_demo_system(seed: int = 7) -> SortationSystem:
    config = SortationConfig(
        inbound_capacity=10,
        retry_limit=2,
        scanner_accuracy=0.92,
        lane_release_rate=1,
    )

    system = SortationSystem(
        route_table={"X": "A", "Y": "B", "Z": "C"},
        lane_capacities={"A": 2, "B": 2, "C": 2},
        config=config,
        seed=seed,
        blocked_schedule={"A": {3, 4, 5}, "B": {7, 8}},
    )

    manifest = [
        ("X", None, None),
        ("Y", None, None),
        ("Z", None, None),
        ("X", None, None),
        ("Y", None, None),
        ("Q", None, None),
        ("Z", "BAD-Z-007", None),
        ("X", None, None),
        ("X", None, None),
        ("Y", None, None),
        ("Z", None, None),
        ("X", None, None),
        ("Y", None, None),
        ("Z", None, "MISREAD"),
    ]

    for destination, barcode, forced_scan in manifest:
        system.add_package(destination, barcode=barcode, forced_scan=forced_scan)

    return system
