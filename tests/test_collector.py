#!/usr/bin/env python3
"""
Unit and Integration Test Suite for Antigravity View Usage (ag-vu) Collector.
"""

import datetime
import json
import os
import pathlib
import shutil
import sqlite3
import tempfile
import unittest

from backend.ag_vu_collector import (
    AntigravityCollector,
    calculate_status_level,
    format_tokens,
    parse_reset_in,
)


class TestHelpers(unittest.TestCase):
    """Test utility and formatting helper functions."""

    def test_format_tokens(self):
        self.assertEqual(format_tokens(0), "0")
        self.assertEqual(format_tokens(500), "500")
        self.assertEqual(format_tokens(999), "999")
        self.assertEqual(format_tokens(1000), "1.0k")
        self.assertEqual(format_tokens(48200), "48.2k")
        self.assertEqual(format_tokens(1250000), "1.25M")
        self.assertEqual(format_tokens(371460000), "371.46M")

    def test_calculate_status_level(self):
        self.assertEqual(calculate_status_level(100.0), "healthy")
        self.assertEqual(calculate_status_level(50.1), "healthy")
        self.assertEqual(calculate_status_level(50.0), "warning")
        self.assertEqual(calculate_status_level(30.0), "warning")
        self.assertEqual(calculate_status_level(20.0), "warning")
        self.assertEqual(calculate_status_level(19.9), "critical")
        self.assertEqual(calculate_status_level(5.0), "critical")
        self.assertEqual(calculate_status_level(0.0), "critical")

    def test_parse_reset_in(self):
        self.assertEqual(parse_reset_in(""), "--")
        self.assertEqual(parse_reset_in(None), "--")

        now = datetime.datetime.now(datetime.timezone.utc)

        # Past time
        past = (now - datetime.timedelta(minutes=10)).isoformat()
        self.assertEqual(parse_reset_in(past), "Ready")

        # 3 days, 5 hours ahead
        future_days = (now + datetime.timedelta(days=3, hours=5, minutes=10)).isoformat()
        self.assertEqual(parse_reset_in(future_days), "3d 5h")

        # 4 hours, 50 minutes ahead
        future_hours = (now + datetime.timedelta(hours=4, minutes=50, seconds=5)).isoformat()
        self.assertEqual(parse_reset_in(future_hours), "4h 50m")

        # 25 minutes ahead
        future_mins = (now + datetime.timedelta(minutes=25, seconds=5)).isoformat()
        self.assertEqual(parse_reset_in(future_mins), "25m")


class TestQuotaTransformation(unittest.TestCase):
    """Test quota parsing and group pinning logic."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.gemini_dir = pathlib.Path(self.temp_dir) / "gemini"
        self.cache_dir = pathlib.Path(self.temp_dir) / "cache"
        self.config_dir = pathlib.Path(self.temp_dir) / "config"
        self.collector = AntigravityCollector(
            gemini_dir=self.gemini_dir,
            cache_dir=self.cache_dir,
            config_dir=self.config_dir,
        )

        self.mock_quota_raw = {
            "groups": [
                {
                    "displayName": "Gemini Models",
                    "buckets": [
                        {
                            "bucketId": "gemini-weekly",
                            "window": "weekly",
                            "remainingFraction": 0.65,
                            "resetTime": "2026-11-15T18:00:00Z",
                        },
                        {
                            "bucketId": "gemini-5h",
                            "window": "5h",
                            "remainingFraction": 0.90,
                            "resetTime": "2026-11-12T18:00:00Z",
                        },
                    ],
                },
                {
                    "displayName": "Claude and GPT models",
                    "buckets": [
                        {
                            "bucketId": "3p-weekly",
                            "window": "weekly",
                            "remainingFraction": 1.0,
                            "resetTime": "2026-11-19T13:00:00Z",
                        }
                    ],
                },
                {
                    "displayName": "Gemini 4 Argon",
                    "buckets": [
                        {
                            "bucketId": "gemini-argon-wtu-weekly",
                            "window": "weekly",
                            "remainingFraction": 0.30,
                            "resetTime": "2026-11-15T18:00:00Z",
                        }
                    ],
                },
            ]
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auto_lowest_selection(self):
        primary, groups = self.collector.transform_quota_groups(self.mock_quota_raw, pinned_group_pref="auto")
        self.assertEqual(len(groups), 3)
        self.assertEqual(primary["group"], "Gemini 4 Argon")
        self.assertAlmostEqual(primary["remaining_pct"], 30.0, places=1)
        self.assertEqual(primary["status_level"], "warning")

    def test_pinned_gemini_selection(self):
        primary, groups = self.collector.transform_quota_groups(self.mock_quota_raw, pinned_group_pref="gemini")
        self.assertEqual(primary["group"], "Gemini Models")
        self.assertAlmostEqual(primary["remaining_pct"], 65.0, places=1)

    def test_empty_quota_fallback(self):
        primary, groups = self.collector.transform_quota_groups(None, pinned_group_pref="auto")
        self.assertEqual(primary["group"], "Gemini 4 Argon")
        self.assertEqual(primary["remaining_pct"], 100.0)
        self.assertEqual(len(groups), 0)


class TestPreferencesAndCache(unittest.TestCase):
    """Test preferences and disk caching mechanics."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = pathlib.Path(self.temp_dir) / "cache"
        self.config_dir = pathlib.Path(self.temp_dir) / "config"
        self.collector = AntigravityCollector(
            gemini_dir=pathlib.Path(self.temp_dir) / "gemini",
            cache_dir=self.cache_dir,
            config_dir=self.config_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preferences_save_and_load(self):
        prefs = self.collector.get_preferences()
        self.assertEqual(prefs.get("pinned_group"), "auto")

        self.collector.save_preferences({"pinned_group": "argon"})
        reloaded = self.collector.get_preferences()
        self.assertEqual(reloaded.get("pinned_group"), "argon")


class TestSQLiteAndSwarmExtraction(unittest.TestCase):
    """Test conversation_summaries SQLite parsing and swarm hierarchy."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.gemini_dir = pathlib.Path(self.temp_dir) / "antigravity"
        self.gemini_dir.mkdir(parents=True)
        self.cache_dir = pathlib.Path(self.temp_dir) / "cache"
        self.config_dir = pathlib.Path(self.temp_dir) / "config"

        # Create mock conversation_summaries.db
        self.db_path = self.gemini_dir / "conversation_summaries.db"
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE conversation_summaries (
                conversation_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT "",
                preview TEXT NOT NULL DEFAULT "",
                step_count INTEGER NOT NULL DEFAULT 0,
                last_modified_time TEXT NOT NULL,
                workspace_uris TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT "",
                project_id TEXT NOT NULL DEFAULT "",
                agent_name TEXT NOT NULL DEFAULT "",
                parent_conversation_id TEXT NOT NULL DEFAULT "",
                not_fully_idle NUMERIC NOT NULL DEFAULT 0,
                killed NUMERIC NOT NULL DEFAULT 0
            )
            """
        )

        # Insert coordinator and 2 workers
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute(
            """
            INSERT INTO conversation_summaries VALUES
            ('coord-1', 'Main Project Task', 'Preview', 15, ?, '["file:///home/user/project1"]', 'CASCADE_RUN_STATUS_RUNNING', 'proj-1', '', '', 1, 0),
            ('worker-1', '', '', 8, ?, '["file:///home/user/project1"]', 'CASCADE_RUN_STATUS_RUNNING', 'proj-1', 'explorer', 'coord-1', 1, 0),
            ('worker-2', '', '', 5, ?, '["file:///home/user/project1"]', 'CASCADE_RUN_STATUS_IDLE', 'proj-1', 'verifier', 'coord-1', 0, 0),
            ('dead-worker', '', '', 2, ?, '["file:///home/user/project1"]', 'CASCADE_RUN_STATUS_IDLE', 'proj-1', 'old', 'coord-1', 0, 1)
            """,
            (now_str, now_str, now_str, now_str),
        )
        con.commit()
        con.close()

        self.collector = AntigravityCollector(
            gemini_dir=self.gemini_dir,
            cache_dir=self.cache_dir,
            config_dir=self.config_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_active_context_and_swarm(self):
        convs = self.collector.read_conversations_db()
        self.assertEqual(len(convs), 4)

        active_ctx, swarm = self.collector.extract_active_context_and_swarm(convs)

        # Context assertions
        self.assertEqual(active_ctx["project_name"], "project1")
        self.assertIn(active_ctx["conversation_id"], ["coord-1", "worker-1"])

        # Swarm assertions
        self.assertEqual(swarm["total_alive"], 3)  # excludes dead-worker
        self.assertEqual(swarm["active_count"], 2)  # coord-1 and worker-1
        self.assertTrue(swarm["is_working"])

        agent_names = [a["name"] for a in swarm["agents"]]
        self.assertIn("coordinator", agent_names)
        self.assertIn("explorer", agent_names)
        self.assertIn("verifier", agent_names)
        self.assertNotIn("old", agent_names)


class TestIncrementalTranscriptIndexer(unittest.TestCase):
    """Test fast incremental transcript parsing and caching."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.gemini_dir = pathlib.Path(self.temp_dir) / "antigravity"
        self.cache_dir = pathlib.Path(self.temp_dir) / "cache"
        self.config_dir = pathlib.Path(self.temp_dir) / "config"

        # Create mock brain directory with transcript
        t_dir = self.gemini_dir / "brain" / "conv-100" / ".system_generated" / "logs"
        t_dir.mkdir(parents=True)
        self.transcript_file = t_dir / "transcript.jsonl"

        with open(self.transcript_file, "w") as f:
            f.write(json.dumps({
                "step_index": 0,
                "input_tokens": 1000,
                "cache_read_tokens": 5000,
                "output_tokens": 200,
                "created_at": "2026-11-12T10:00:00Z"
            }) + "\n")
            f.write(json.dumps({
                "step_index": 1,
                "input_tokens": 2000,
                "cache_read_tokens": 8000,
                "output_tokens": 300,
                "created_at": "2026-11-12T10:05:00Z"
            }) + "\n")

        self.collector = AntigravityCollector(
            gemini_dir=self.gemini_dir,
            cache_dir=self.cache_dir,
            config_dir=self.config_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_indexing_tokens(self):
        mock_convs = [{
            "conversation_id": "conv-100",
            "workspace_uris": json.dumps(["file:///home/user/myproject"])
        }]

        monthly, projects = self.collector.index_transcripts(mock_convs)

        self.assertEqual(monthly["input_tokens"], 3000)
        self.assertEqual(monthly["cache_read_tokens"], 13000)
        self.assertEqual(monthly["output_tokens"], 500)
        self.assertEqual(monthly["total_tokens"], 16500)
        self.assertEqual(monthly["total_formatted"], "16.5k")

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "myproject")
        self.assertEqual(projects[0]["total_tokens"], 16500)


class TestLiveContractValidation(unittest.TestCase):
    """End-to-End contract validation against live local system."""

    def test_live_collect_contract_structure(self):
        collector = AntigravityCollector()
        data = collector.collect()

        # Contract keys verification
        expected_keys = [
            "timestamp",
            "user",
            "primary_quota",
            "quota_groups",
            "active_context",
            "swarm",
            "monthly_tokens",
            "projects",
        ]
        for k in expected_keys:
            self.assertIn(k, data, f"Missing key '{k}' in collect() output")

        # User schema
        user = data["user"]
        self.assertIn("name", user)
        self.assertIn("tier", user)
        self.assertIn("ls_online", user)

        # Primary quota schema
        pq = data["primary_quota"]
        self.assertIn("group", pq)
        self.assertIn("window", pq)
        self.assertIn("remaining_pct", pq)
        self.assertIn("reset_in", pq)
        self.assertIn("status_level", pq)

        # Active context schema
        act = data["active_context"]
        self.assertIn("conversation_id", act)
        self.assertIn("title", act)
        self.assertIn("project_name", act)
        self.assertIn("context_tokens", act)
        self.assertIn("context_formatted", act)

        # Swarm schema
        sw = data["swarm"]
        self.assertIn("active_count", sw)
        self.assertIn("total_alive", sw)
        self.assertIn("is_working", sw)
        self.assertIn("agents", sw)

        # Monthly tokens schema
        mt = data["monthly_tokens"]
        self.assertIn("month", mt)
        self.assertIn("total_tokens", mt)
        self.assertIn("total_formatted", mt)


if __name__ == "__main__":
    unittest.main()
