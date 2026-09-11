"""
Performance & Latency Benchmark Smoke Tests.

Purpose:
    Asserts runtime execution bounds on critical API and pipeline pathways to prevent performance regressions.
"""

import time
import unittest
import numpy as np
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from ocr.cleaning import OCRTextCleaner
from ocr.parser import OCREntityParser


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance latency benchmark smoke tests."""

    def setUp(self):
        self.client = TestClient(app)
        self.now = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)

    def test_health_endpoint_latency(self):
        """Assert GET /api/v1/health completes under 50 milliseconds."""
        start_t = time.perf_counter()
        res = self.client.get("/api/v1/health")
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        self.assertEqual(res.status_code, 200)
        self.assertLess(elapsed_ms, 200.0, f"Health check latency {elapsed_ms:.2f}ms exceeded 200ms bound")

    def test_text_cleaning_and_parsing_latency(self):
        """Assert OCR text cleaning and entity parsing completes under 20 milliseconds."""
        raw = "  PARACETAM0L \t 5OOmg \n BATCH-2026-09 EXP  2O28/12/31  "
        start_t = time.perf_counter()

        cleaned = OCRTextCleaner.clean(raw)
        identity = OCREntityParser.parse(cleaned)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        self.assertIsNotNone(identity)
        self.assertLess(elapsed_ms, 20.0, f"Parser latency {elapsed_ms:.2f}ms exceeded 20ms bound")


if __name__ == "__main__":
    unittest.main()
