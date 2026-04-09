from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from autosort.controller import FaultCode, SortationConfig, SortationSystem


class SortationSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        config = SortationConfig(
            inbound_capacity=2,
            retry_limit=1,
            scanner_accuracy=1.0,
            lane_release_rate=0,
        )
        self.system = SortationSystem(
            route_table={"X": "A", "Y": "B"},
            lane_capacities={"A": 1, "B": 1},
            config=config,
            seed=1,
        )

    def test_destination_x_routes_to_lane_a(self) -> None:
        package = self.system.make_package("X")
        self.system.enqueue(package)

        self.system.process_cycle()

        self.assertEqual(len(self.system.lanes["A"].queue), 1)
        self.assertEqual(self.system.lanes["A"].queue[0].package_id, package.package_id)
        self.assertEqual(self.system.stats["routed"], 1)

    def test_unknown_destination_goes_to_exception_handling(self) -> None:
        package = self.system.make_package("Q")
        self.system.enqueue(package)

        self.system.process_cycle()

        self.assertEqual(len(self.system.error_bin), 1)
        self.assertEqual(self.system.error_bin[0].fault, FaultCode.MISREAD.value)

    def test_barcode_input_routes_to_matching_lane(self) -> None:
        self.assertTrue(self.system.add_package_from_barcode("BC-Y-501"))

        self.system.process_cycle()

        self.assertEqual(len(self.system.lanes["B"].queue), 1)
        self.assertEqual(self.system.stats["routed"], 1)

    def test_bad_barcode_is_treated_as_misread(self) -> None:
        self.assertTrue(self.system.add_package_from_barcode("BAD-UNKNOWN-01"))

        self.system.process_cycle()

        self.assertEqual(len(self.system.error_bin), 1)
        self.assertEqual(self.system.error_bin[0].fault, FaultCode.MISREAD.value)

    def test_blocked_lane_requeues_then_rejects_after_retry_limit(self) -> None:
        self.system.set_lane_blocked("A", True)
        package = self.system.make_package("X")
        self.system.enqueue(package)

        self.system.process_cycle()
        self.assertEqual(len(self.system.inbound_queue), 1)
        self.assertEqual(self.system.stats["requeued"], 1)

        self.system.process_cycle()
        self.assertEqual(len(self.system.error_bin), 1)
        self.assertEqual(self.system.error_bin[0].fault, FaultCode.BLOCKED_LANE.value)

    def test_inbound_capacity_rejects_extra_package(self) -> None:
        first = self.system.make_package("X")
        second = self.system.make_package("Y")
        third = self.system.make_package("X")

        self.assertTrue(self.system.enqueue(first))
        self.assertTrue(self.system.enqueue(second))
        self.assertFalse(self.system.enqueue(third))
        self.assertEqual(self.system.error_bin[-1].fault, FaultCode.INBOUND_OVERFLOW.value)


if __name__ == "__main__":
    unittest.main()
