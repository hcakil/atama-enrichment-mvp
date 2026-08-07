"""Lightweight tests for match + feed export (stdlib)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from atama_mvp.feed_export import feed_metrics, to_feed_record, write_feed
from atama_mvp.match import AlertProfile, match_listing


class MatchTests(unittest.TestCase):
    def test_province_and_age(self) -> None:
        profile = AlertProfile.from_dict(
            {
                "provinces": ["Ankara"],
                "age": 28,
                "min_confidence": 0.4,
                "education_levels": ["lisans"],
            }
        )
        ok = {
            "confidence": 0.7,
            "provinces": '["Ankara","İzmir"]',
            "education_levels": '["lisans"]',
            "min_age": 18,
            "max_age": 35,
            "kpss_requirement": "kpss",
            "title": "Memur",
            "institution_name": "X",
            "enrich_status": "detail",
            "source": "ilan_gov",
        }
        self.assertTrue(match_listing(ok, profile))
        too_old = {**ok, "max_age": 25}
        self.assertFalse(match_listing(too_old, profile))
        other_city = {**ok, "provinces": '["Bursa"]'}
        self.assertFalse(match_listing(other_city, profile))


class FeedExportTests(unittest.TestCase):
    def test_demo_strips_evidence(self) -> None:
        row = {
            "fingerprint": "t:1",
            "source": "kk",
            "external_id": "1",
            "external_url": "https://example.com",
            "title": "T",
            "institution_name": "I",
            "category": None,
            "published_at": None,
            "application_window": None,
            "application_start": None,
            "application_end": None,
            "quota": 3,
            "kpss_requirement": "kpss",
            "education_levels": '["lisans"]',
            "provinces": '["Ankara"]',
            "fields_of_study": None,
            "min_age": 18,
            "max_age": 35,
            "gender": None,
            "profession_hint": None,
            "military_hints": None,
            "license_hints": None,
            "confidence": 0.8,
            "enrich_status": "detail",
            "evidence_json": '{"x":1}',
            "criteria_json": '{"quota":3,"confidence":0.8}',
            "review_status": "pending",
            "first_seen_at": 1.0,
            "last_seen_at": 1.0,
        }
        demo = to_feed_record(row, demo=True)
        self.assertNotIn("evidence", demo)
        self.assertNotIn("criteria_summary", demo)
        full = to_feed_record(row, demo=False)
        self.assertIn("evidence", full)
        self.assertEqual(full["quota"], 3)

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_feed([demo], feed_metrics([demo], source_rows=1), Path(tmp) / "feed")
            self.assertTrue(paths["json"].is_file())
            self.assertTrue(paths["csv"].is_file())
            self.assertTrue(paths["metrics"].is_file())


if __name__ == "__main__":
    unittest.main()
