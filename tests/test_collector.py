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
    calculate_quota_pacing,
    calculate_status_level,
    format_duration_friendly,
    format_tokens,
    format_waybar_payload,
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

    def test_auto_active_model_selection(self):
        # In auto mode, when active model is Gemini 4 Hydrogen, it must bind to gemini group
        primary, groups = self.collector.transform_quota_groups(
            self.mock_quota_raw,
            pinned_group_pref="auto",
            active_model_group="gemini",
            active_model_label="Gemini 4 Hydrogen (XHigh)",
        )
        self.assertEqual(primary["group"], "4\u00a0Hydrogen")
        self.assertAlmostEqual(primary["remaining_pct"], 65.0, places=1)

    def test_pinned_gemini_selection(self):
        primary, groups = self.collector.transform_quota_groups(self.mock_quota_raw, pinned_group_pref="gemini")
        self.assertEqual(primary["group"], "Gemini\u00a03.8")
        self.assertAlmostEqual(primary["remaining_pct"], 65.0, places=1)

    def test_pinned_group_most_restrictive_bucket(self):
        # When 5h bucket is more restrictive than weekly within a pinned group
        mock_raw = {
            "groups": [
                {
                    "displayName": "Claude and GPT models",
                    "buckets": [
                        {
                            "bucketId": "3p-weekly",
                            "window": "weekly",
                            "remainingFraction": 0.40,
                            "resetTime": "2026-11-19T13:00:00Z",
                        },
                        {
                            "bucketId": "3p-5h",
                            "window": "5h",
                            "remainingFraction": 0.05,
                            "resetTime": "2026-11-12T18:00:00Z",
                        },
                    ],
                }
            ]
        }
        primary, _ = self.collector.transform_quota_groups(mock_raw, pinned_group_pref="3p")
        self.assertEqual(primary["group"], "Claude / GPT")
        self.assertEqual(primary["window"], "5h")
        self.assertAlmostEqual(primary["remaining_pct"], 5.0, places=1)
        self.assertEqual(primary["status_level"], "critical")

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

    def test_detect_active_model_from_db(self):
        cid = "conv-active-test"
        db_path = self.gemini_dir / "conversations" / f"{cid}.db"
        (self.gemini_dir / "conversations").mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("CREATE TABLE gen_metadata (idx INTEGER PRIMARY KEY, data BLOB)")
        sample_blob = b"prefix\xaa\x01\x19Gemini 4 Hydrogen (XHigh)suffix"
        cur.execute("INSERT INTO gen_metadata VALUES (1, ?)", (sample_blob,))
        con.commit()
        con.close()

        slug, label, group_id = self.collector.detect_active_model(cid)
        self.assertEqual(label, "Gemini 4 Hydrogen (XHigh)")
        self.assertEqual(group_id, "gemini")
        self.assertIn("hydrogen", slug)


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

        monthly, projects, daily = self.collector.index_transcripts(mock_convs)

        self.assertEqual(monthly["input_tokens"], 3000)
        self.assertEqual(monthly["cache_read_tokens"], 13000)
        self.assertEqual(monthly["output_tokens"], 500)
        self.assertEqual(monthly["total_tokens"], 16500)
        self.assertEqual(monthly["total_formatted"], "16.5k")

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "myproject")
        self.assertEqual(projects[0]["total_tokens"], 16500)

        # 7-day daily history validation
        self.assertEqual(len(daily), 7)
        expected_labels = {"Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"}
        for d in daily:
            self.assertIn("date", d)
            self.assertIn("label", d)
            self.assertIn(d["label"], expected_labels)
            self.assertIn("input_tokens", d)
            self.assertIn("cache_read_tokens", d)
            self.assertIn("output_tokens", d)
            self.assertIn("total_tokens", d)
            self.assertIn("total_formatted", d)

    def test_legacy_cache_invalidation_without_daily(self):
        # Create a legacy cache entry that has mtime_ns and size but NO "daily" key
        st = self.transcript_file.stat()
        legacy_cache = {
            "files": {
                str(self.transcript_file): {
                    "mtime_ns": st.st_mtime_ns,
                    "size": st.st_size,
                    "conv_id": "conv-100",
                    "input_tokens": 100,
                    "cache_read_tokens": 200,
                    "output_tokens": 300,
                    "months": {},
                    # "daily" missing intentionally!
                }
            }
        }
        with open(self.collector.transcript_index_file, "w") as f:
            json.dump(legacy_cache, f)

        mock_convs = [{"conversation_id": "conv-100", "workspace_uris": ""}]
        monthly, projects, daily = self.collector.index_transcripts(mock_convs)

        # Must re-read file from scratch because legacy cache lacked "daily"
        self.assertEqual(monthly["total_tokens"], 16500)
        self.assertEqual(len(daily), 7)


class TestPacingAndExhaustion(unittest.TestCase):
    """Test burn rate pacing marker and exhaustion forecasting."""

    def test_format_duration_friendly(self):
        self.assertEqual(format_duration_friendly(45), "~1m")
        self.assertEqual(format_duration_friendly(300), "~5m")
        self.assertEqual(format_duration_friendly(3600), "~1h")
        self.assertEqual(format_duration_friendly(3720), "~1h 2m")
        self.assertEqual(format_duration_friendly(90000), "~1d 1h")

    def test_pacing_5h_fast_with_exhaustion(self):
        now = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        # 5h window (18000s). Reset in 3h (10800s). Elapsed: 2h (7200s = 40.0%).
        # Expected remaining: 60.0%. Actual remaining: 20.0% (consumed: 80.0%).
        # pace_delta: 20.0 - 60.0 = -40.0 <= -5.0 -> fast!
        # Burn rate: 80% / 7200s = 0.01111 %/s.
        # secs_to_exhaust: 20 / 0.01111 = 1800s (30m).
        # 1800s < 10800s (30m < 3h) -> exhausts in ~30m!
        res = calculate_quota_pacing("5h", 20.0, "2026-11-13T15:00:00Z", now_dt=now)
        self.assertEqual(res["window_duration_sec"], 18000.0)
        self.assertEqual(res["elapsed_sec"], 7200.0)
        self.assertEqual(res["secs_to_reset"], 10800.0)
        self.assertEqual(res["elapsed_pct"], 40.0)
        self.assertEqual(res["expected_remaining_pct"], 60.0)
        self.assertEqual(res["consumed_pct"], 80.0)
        self.assertEqual(res["pace_delta_pct"], -40.0)
        self.assertEqual(res["pace_status"], "fast")
        self.assertEqual(res["estimated_exhaust_in"], "~30m")

    def test_pacing_weekly_fast_with_exhaustion(self):
        now = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        # Weekly window (604800s). Reset in 5d (432000s). Elapsed: 2d (172800s = 28.6%).
        # Expected remaining: 71.4%. Actual remaining: 20.0% (consumed: 80.0%).
        # pace_delta: 20.0 - 71.4 = -51.4 <= -5.0 -> fast!
        # Burn rate: 80% / 172800s = 0.000463 %/s.
        # secs_to_exhaust: 20 / 0.000463 = 43200s (12h).
        # 43200s < 432000s (12h < 5d) -> exhausts in ~12h!
        res = calculate_quota_pacing("weekly", 20.0, "2026-11-18T12:00:00Z", now_dt=now)
        self.assertEqual(res["pace_status"], "fast")
        self.assertEqual(res["estimated_exhaust_in"], "~12h")

    def test_pacing_fast_already_exhausted_gives_none_estimate(self):
        now = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        # Quota already at 0% (exhausted): pace_status is fast, but estimated_exhaust_in is None
        res = calculate_quota_pacing("5h", 0.0, "2026-11-13T15:00:00Z", now_dt=now)
        self.assertEqual(res["pace_status"], "fast")
        self.assertEqual(res["remaining_pct"] if "remaining_pct" in res else res["consumed_pct"], 100.0)
        self.assertIsNone(res["estimated_exhaust_in"])

    def test_pacing_slow(self):
        now = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        # 5h window. Reset in 2h (7200s). Elapsed: 3h (10800s = 60.0%).
        # Expected remaining: 40.0%. Actual remaining: 80.0% (consumed 20.0%).
        # pace_delta: 80.0 - 40.0 = +40.0 >= 5.0 -> slow!
        res = calculate_quota_pacing("5h", 80.0, "2026-11-13T14:00:00Z", now_dt=now)
        self.assertEqual(res["pace_status"], "slow")
        self.assertIsNone(res["estimated_exhaust_in"])

    def test_pacing_normal(self):
        now = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        # 5h window. Reset in 2.5h (9000s). Elapsed: 2.5h (9000s = 50.0%).
        # Expected remaining: 50.0%. Actual remaining: 49.0%.
        # pace_delta: 49.0 - 50.0 = -1.0 (between -5 and +5) -> normal.
        res = calculate_quota_pacing("5h", 49.0, "2026-11-13T14:30:00Z", now_dt=now)
        self.assertEqual(res["pace_status"], "normal")
        self.assertIsNone(res["estimated_exhaust_in"])

    def test_pacing_invalid_and_unknown(self):
        res1 = calculate_quota_pacing("invalid_window", 50.0, "2026-11-13T14:00:00Z")
        self.assertEqual(res1["pace_status"], "unknown")
        self.assertIsNone(res1["elapsed_pct"])

        res2 = calculate_quota_pacing("weekly", 50.0, "")
        self.assertEqual(res2["pace_status"], "unknown")

        res3 = calculate_quota_pacing("weekly", 50.0, "invalid-date-string")
        self.assertEqual(res3["pace_status"], "unknown")

    def test_pacing_early_cycle_not_fast(self):
        now = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        # Reset in 4h 58m (elapsed = 2m = 120s < 300s, elapsed_pct < 2.0%)
        # Even if delta is large, must not trigger fast status or exhaust estimate
        res = calculate_quota_pacing("5h", 90.0, "2026-11-13T16:58:00Z", now_dt=now)
        self.assertEqual(res["pace_status"], "normal")
        self.assertIsNone(res["estimated_exhaust_in"])


class TestWaybarOutput(unittest.TestCase):
    """Test --waybar JSON generation."""

    def test_format_waybar_payload_online(self):
        mock_data = {
            "user": {"ls_online": True},
            "primary_quota": {
                "group": "Gemini 3.8",
                "remaining_pct": 75.0,
                "reset_in": "2d 4h",
                "status_level": "healthy",
                "pace_status": "normal",
            },
            "active_context": {
                "active_model_label": "Gemini 3.8 Flash",
                "context_formatted": "42k",
            },
            "swarm": {
                "active_count": 2,
                "total_alive": 5,
            },
        }
        out_json = format_waybar_payload(mock_data)
        parsed = json.loads(out_json)
        self.assertEqual(parsed["class"], "normal")
        self.assertEqual(parsed["percentage"], 75.0)
        self.assertIn("Gemini 3.8", parsed["text"])
        self.assertIn("75%", parsed["text"])
        self.assertIn("Context: 42k tokens", parsed["tooltip"])

    def test_format_waybar_payload_offline_and_warning(self):
        mock_data = {
            "user": {"ls_online": False},
            "primary_quota": {
                "group": "Gemini 4 Argon",
                "remaining_pct": 15.0,
                "reset_in": "5h",
                "status_level": "critical",
                "pace_status": "fast",
            },
            "active_context": {},
            "swarm": {},
        }
        out_json = format_waybar_payload(mock_data)
        parsed = json.loads(out_json)
        self.assertEqual(parsed["class"], "offline")
        self.assertEqual(parsed["percentage"], 15.0)
        self.assertIn("⚡", parsed["text"])  # fast pace indicator


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
            "daily_history",
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
        self.assertIn("pace_status", pq)

        # Active context schema
        act = data["active_context"]
        self.assertIn("conversation_id", act)
        self.assertIn("title", act)
        self.assertIn("project_name", act)
        self.assertIn("context_tokens", act)
        self.assertIn("context_formatted", act)
        self.assertIn("active_model", act)
        self.assertIn("active_model_label", act)

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

        # Daily history schema
        dh = data["daily_history"]
        self.assertEqual(len(dh), 7)
        for d in dh:
            self.assertIn("date", d)
            self.assertIn("label", d)
            self.assertIn("input_tokens", d)
            self.assertIn("cache_read_tokens", d)
            self.assertIn("output_tokens", d)
            self.assertIn("total_tokens", d)
            self.assertIn("total_formatted", d)

        # Waybar payload verification
        wb_str = format_waybar_payload(data)
        wb = json.loads(wb_str)
        self.assertIn("text", wb)
        self.assertIn("tooltip", wb)
        self.assertIn("class", wb)
        self.assertIn("percentage", wb)


if __name__ == "__main__":
    unittest.main()
