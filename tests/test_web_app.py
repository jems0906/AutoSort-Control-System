from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from autosort.web_app import create_app


class WebAppTests(unittest.TestCase):
    def test_homepage_loads(self) -> None:
        app = create_app(seed=7)
        client = app.test_client()

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AutoSort Control System", response.data)
        self.assertIn(b"Lane A", response.data)


if __name__ == "__main__":
    unittest.main()
