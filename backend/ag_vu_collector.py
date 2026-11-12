#!/usr/bin/env python3
"""
Antigravity View Usage (ag-vu) Collector & CLI
Zero-dependency telemetry & quota monitor for Google Antigravity on Linux GNOME.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import pathlib
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

APP_NAME = "antigravity-vu"
DEFAULT_CACHE_DIR = pathlib.Path.home() / ".cache" / APP_NAME
DEFAULT_CONFIG_DIR = pathlib.Path.home() / ".config" / APP_NAME
DEFAULT_GEMINI_DIR = pathlib.Path.home() / ".gemini" / "antigravity"


def format_tokens(n: int) -> str:
    """Format token count into readable string (e.g. 1.25M, 48.2k, 500)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def parse_reset_in(reset_time_str: str) -> str:
    """Calculate remaining time until reset from ISO-8601 UTC string."""
    if not reset_time_str:
        return "--"
    try:
        clean_str = reset_time_str.replace("Z", "+00:00")
        target = datetime.datetime.fromisoformat(clean_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = target - now
        total_seconds = int(diff.total_seconds() + 0.5)
        if total_seconds <= 0:
            return "Ready"
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{max(1, minutes)}m"
    except Exception:
        return "--"


def calculate_status_level(remaining_pct: float) -> str:
    """Determine status level (healthy, warning, critical) based on quota percentage."""
    if remaining_pct > 50.0:
        return "healthy"
    if remaining_pct >= 20.0:
        return "warning"
    return "critical"


class AntigravityCollector:
    """Main collector engine for Google Antigravity telemetry and metrics."""

    def __init__(
        self,
        gemini_dir: Optional[pathlib.Path] = None,
        cache_dir: Optional[pathlib.Path] = None,
        config_dir: Optional[pathlib.Path] = None,
    ) -> None:
        self.gemini_dir = gemini_dir or DEFAULT_GEMINI_DIR
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.quota_cache_file = self.cache_dir / "last_quota.json"
        self.transcript_index_file = self.cache_dir / "transcript_index.json"
        self.prefs_file = self.config_dir / "prefs.json"

    # ------------------------------------------------------------------
    # Preferences Management
    # ------------------------------------------------------------------
    def get_preferences(self) -> Dict[str, Any]:
        """Load user preferences from JSON config."""
        default_prefs = {"pinned_group": "auto"}
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        default_prefs.update(data)
            except Exception:
                pass
        return default_prefs

    def save_preferences(self, prefs: Dict[str, Any]) -> None:
        """Save preferences to disk."""
        try:
            with open(self.prefs_file, "w", encoding="utf-8") as f:
                json.dump(prefs, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Daemon Discovery & Local RPC Communication
    # ------------------------------------------------------------------
    def discover_daemon(self) -> Optional[Dict[str, Any]]:
        """
        Discover running Language Server daemon from ~/.gemini/antigravity/daemon/hub_*.json
        or environment variables.
        """
        daemon_dir = self.gemini_dir / "daemon"
        if daemon_dir.exists():
            hub_files = sorted(daemon_dir.glob("hub_*.json"), key=os.path.getmtime, reverse=True)
            for hf in hub_files:
                try:
                    with open(hf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    pid = data.get("pid")
                    http_port = data.get("httpPort")
                    csrf = data.get("csrfToken")
                    if pid and http_port and csrf:
                        # Verify process is alive
                        if os.path.exists(f"/proc/{pid}"):
                            return {
                                "pid": pid,
                                "httpPort": http_port,
                                "httpsPort": data.get("httpsPort", 0),
                                "csrfToken": csrf,
                                "lsVersion": data.get("lsVersion", "unknown"),
                            }
                except Exception:
                    continue

        # Fallback to environment variables
        env_addr = os.environ.get("ANTIGRAVITY_LS_ADDRESS")
        env_csrf = os.environ.get("ANTIGRAVITY_CSRF_TOKEN")
        if env_addr and env_csrf:
            port = 38125
            if ":" in env_addr:
                try:
                    port = int(env_addr.split(":")[-1])
                except ValueError:
                    pass
            return {
                "pid": 0,
                "httpPort": port,
                "httpsPort": 0,
                "csrfToken": env_csrf,
                "lsVersion": os.environ.get("ANTIGRAVITY_LS_VERSION", "env"),
            }

        return None

    def call_rpc(
        self,
        method: str,
        daemon_info: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 1.5,
    ) -> Optional[Dict[str, Any]]:
        """Call a ConnectRPC method on the local Language Server HTTP endpoint."""
        port = daemon_info["httpPort"]
        csrf = daemon_info["csrfToken"]
        url = f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/{method}"
        headers = {
            "Content-Type": "application/json",
            "x-codeium-csrf-token": csrf,
        }
        body_bytes = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass
        return None

    def fetch_live_quota_and_user(
        self, daemon_info: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any], Optional[Dict[str, Any]]]:
        """Fetch real-time quota and user status from daemon, with fallback to disk cache."""
        user_info = {"name": "User", "tier": "Pro", "ls_online": False}
        quota_data = None

        if daemon_info:
            # Query user status
            status_resp = self.call_rpc("GetUserStatus", daemon_info)
            if status_resp and "userStatus" in status_resp:
                us = status_resp["userStatus"]
                user_info["name"] = us.get("name", "User")
                plan = us.get("planStatus", {}).get("planInfo", {})
                user_info["tier"] = plan.get("planName", "Pro")

            # Query quota summary
            quota_resp = self.call_rpc("RetrieveUserQuotaSummary", daemon_info)
            if quota_resp and "response" in quota_resp:
                user_info["ls_online"] = True
                quota_data = quota_resp["response"]
                # Save to cache
                try:
                    with open(self.quota_cache_file, "w", encoding="utf-8") as f:
                        json.dump({"user": user_info, "quota": quota_data}, f, indent=2)
                except Exception:
                    pass

        # If offline or RPC failed, read from cache
        if not user_info["ls_online"] and self.quota_cache_file.exists():
            try:
                with open(self.quota_cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if isinstance(cached, dict):
                        cached_user = cached.get("user", {})
                        user_info["name"] = cached_user.get("name", user_info["name"])
                        user_info["tier"] = cached_user.get("tier", user_info["tier"])
                        quota_data = cached.get("quota")
            except Exception:
                pass

        return user_info["ls_online"], user_info, quota_data

    # ------------------------------------------------------------------
    # Quota Transformation
    # ------------------------------------------------------------------
    def detect_active_model(
        self, active_cid: str, parent_cid: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detect currently active AI model from SQLite conversations/<id>.db
        (gen_metadata protobuf blobs) or antigravity_state.pbtxt.
        Returns: (model_id, model_label, group_id)
        """
        candidates = [active_cid]
        if parent_cid and parent_cid != active_cid:
            candidates.append(parent_cid)

        for cid in candidates:
            if not cid:
                continue
            db_path = self.gemini_dir / "conversations" / f"{cid}.db"
            if not db_path.exists():
                continue
            try:
                uri = f"file:{db_path.resolve()}?mode=ro"
                con = sqlite3.connect(uri, uri=True, timeout=1.0)
                cur = con.cursor()
                cur.execute("SELECT idx, data FROM gen_metadata ORDER BY idx DESC LIMIT 30")
                for _, data in cur.fetchall():
                    if not data:
                        continue
                    matches = re.findall(
                        rb"\xaa\x01([\x01-\x7f])((?:Gemini|Claude|GPT-)[A-Za-z0-9 ._()-]{3,40})",
                        data,
                    )
                    for length_b, text_b in matches:
                        length = length_b[0]
                        clean_label = text_b[:length].decode("utf-8", errors="ignore").strip()
                        if clean_label:
                            con.close()
                            slug = re.sub(r"[^a-z0-9.]+", "-", clean_label.lower()).strip("-")
                            lower_label = clean_label.lower()
                            if "argon" in lower_label:
                                group_id = "argon"
                            elif "claude" in lower_label or "gpt" in lower_label:
                                group_id = "3p"
                            else:
                                group_id = "gemini"
                            return slug, clean_label, group_id
                con.close()
            except Exception:
                pass

        # Fallback to antigravity_state.pbtxt if available
        state_file = self.gemini_dir / "antigravity_state.pbtxt"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if "last_selected_agent_model" in line:
                            val = line.split(":")[-1].strip().strip('"')
                            if val:
                                return val, val, "gemini"
            except Exception:
                pass

        return None, None, None

    def transform_quota_groups(
        self,
        quota_raw: Optional[Dict[str, Any]],
        pinned_group_pref: str = "auto",
        active_model_group: Optional[str] = None,
        active_model_label: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Transform raw RPC quota payload into structured groups and primary quota."""
        groups_out: List[Dict[str, Any]] = []

        if not quota_raw or "groups" not in quota_raw:
            # Provide sensible fallback structure if completely unpopulated
            fallback_primary = {
                "group": "Gemini 4 Argon",
                "window": "weekly",
                "remaining_pct": 100.0,
                "reset_in": "--",
                "status_level": "healthy",
            }
            return fallback_primary, []

        group_id_map = {
            "gemini models": "gemini",
            "claude and gpt models": "3p",
            "gemini 4 argon": "argon",
        }

        # Rich group metadata defining official display names, subtitles, and models:
        # Note: "pill_name" uses Non-Breaking Space (\u00a0) where appropriate so legacy
        # in-memory JS instances doing .replace('Gemini ', '') will not strip "Gemini".
        group_meta = {
            "gemini": {
                "name": "Gemini 3.8 & 4 Hydrogen",
                "pill_name": "Gemini\u00a03.8",
                "description": "Gemini 3.8 Flash, Gemini 4 Hydrogen, Gemini 3.5 Lite",
                "models": [
                    "Gemini 3.8 Flash",
                    "Gemini 4 Hydrogen",
                    "Gemini 3.5 Flash Lite",
                    "Gemini 2.5 Pro",
                ],
            },
            "argon": {
                "name": "Gemini 4 Argon",
                "pill_name": "Gemini 4 Argon",
                "description": "Gemini 4 Argon (Weekly WTU Quota)",
                "models": [
                    "Gemini 4 Argon",
                ],
            },
            "3p": {
                "name": "Claude & GPT (Opus / Sonnet / GPT)",
                "pill_name": "Claude / GPT",
                "description": "Claude Opus 5.5, Claude Sonnet 5.5, GPT-OSS 120B",
                "models": [
                    "Claude Opus 5.5",
                    "Claude Sonnet 5.5",
                    "GPT-OSS 120B",
                ],
            },
        }

        lowest_bucket = None
        pinned_candidate = None
        active_candidate = None

        for grp in quota_raw.get("groups", []):
            raw_name = grp.get("displayName", "Unknown")
            g_id = group_id_map.get(raw_name.lower().strip(), re.sub(r"[^a-z0-9]+", "-", raw_name.lower()))
            meta = group_meta.get(g_id, {
                "name": raw_name,
                "pill_name": raw_name,
                "description": raw_name,
                "models": [],
            })
            g_name = meta["name"]
            g_pill = meta["pill_name"]
            buckets_out = []

            for b in grp.get("buckets", []):
                b_id = b.get("bucketId", "")
                b_window = b.get("window", "")
                rem_frac = float(b.get("remainingFraction", 1.0))
                rem_pct = round(rem_frac * 100.0, 1)
                reset_time = b.get("resetTime", "")
                reset_in = parse_reset_in(reset_time)

                label = "Weekly" if b_window == "weekly" else ("5-Hour" if b_window == "5h" else b_window.capitalize())
                bucket_dict = {
                    "id": b_id,
                    "label": label,
                    "window": b_window,
                    "remaining_pct": rem_pct,
                    "reset_time": reset_time,
                    "reset_in": reset_in,
                }
                buckets_out.append(bucket_dict)

                candidate = {
                    "group": g_pill,
                    "group_name": g_name,
                    "group_id": g_id,
                    "window": b_window,
                    "remaining_pct": rem_pct,
                    "reset_in": reset_in,
                    "status_level": calculate_status_level(rem_pct),
                }

                if lowest_bucket is None or rem_pct < lowest_bucket["remaining_pct"]:
                    lowest_bucket = candidate

                # Active model candidate tracking
                if active_model_group and g_id == active_model_group:
                    if active_candidate is None:
                        active_candidate = candidate
                    elif rem_pct < active_candidate["remaining_pct"]:
                        active_candidate = candidate
                    elif rem_pct == active_candidate["remaining_pct"] and b_window == "5h":
                        active_candidate = candidate

                # Exact ID match takes top priority, fallback to substring if not yet matched
                is_exact_match = (pinned_group_pref.lower() == g_id.lower())
                is_sub_match = (pinned_group_pref.lower() in g_name.lower()) or (pinned_group_pref.lower() in g_pill.lower())
                if pinned_group_pref != "auto" and (is_exact_match or is_sub_match):
                    # Prefer exact match over substring match
                    if pinned_candidate is None:
                        pinned_candidate = candidate
                    elif is_exact_match and (pinned_candidate.get("group_id") != g_id):
                        pinned_candidate = candidate
                    elif pinned_candidate.get("group_id") == g_id:
                        # Within the pinned group, select the most restrictive bucket (lowest remaining_pct)
                        if rem_pct < pinned_candidate["remaining_pct"]:
                            pinned_candidate = candidate
                        elif rem_pct == pinned_candidate["remaining_pct"] and b_window == "5h":
                            pinned_candidate = candidate

            groups_out.append({
                "name": g_name,
                "id": g_id,
                "description": meta["description"],
                "models": meta["models"],
                "buckets": buckets_out,
            })

        # Selection priority:
        # 1. If pinned_group is explicitly chosen (not "auto"), use pinned_candidate.
        # 2. If "auto" and active_candidate is found, use active_candidate!
        # 3. Fallback to lowest_bucket.
        if pinned_group_pref != "auto" and pinned_candidate is not None:
            selected = pinned_candidate
        elif pinned_group_pref == "auto" and active_candidate is not None:
            selected = dict(active_candidate)
            # Refine pill label according to active model
            if active_model_label and "hydrogen" in active_model_label.lower():
                selected["group"] = "4\u00a0Hydrogen"
            elif active_model_label and "flash" in active_model_label.lower():
                selected["group"] = "Gemini\u00a03.8"
            elif active_model_label and "argon" in active_model_label.lower():
                selected["group"] = "Gemini 4 Argon"
        else:
            selected = lowest_bucket

        if not selected:
            selected = {
                "group": "Gemini 4 Argon",
                "window": "weekly",
                "remaining_pct": 100.0,
                "reset_in": "--",
                "status_level": "healthy",
            }
        else:
            selected = {
                "group": selected["group"],
                "window": selected["window"],
                "remaining_pct": selected["remaining_pct"],
                "reset_in": selected["reset_in"],
                "status_level": selected["status_level"],
            }

        return selected, groups_out

    # ------------------------------------------------------------------
    # SQLite Conversation Summaries & Swarm Data
    # ------------------------------------------------------------------
    def read_conversations_db(self) -> List[Dict[str, Any]]:
        """Read conversation summaries from SQLite in read-only mode."""
        db_path = self.gemini_dir / "conversation_summaries.db"
        if not db_path.exists():
            return []

        results = []
        try:
            uri = f"file:{db_path.resolve()}?mode=ro"
            con = sqlite3.connect(uri, uri=True, timeout=1.0)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                """
                SELECT conversation_id, title, preview, step_count, last_modified_time,
                       workspace_uris, status, project_id, agent_name, parent_conversation_id,
                       not_fully_idle, killed
                FROM conversation_summaries
                ORDER BY last_modified_time DESC
                """
            )
            for row in cur.fetchall():
                results.append(dict(row))
            con.close()
        except Exception:
            pass
        return results

    def extract_active_context_and_swarm(
        self, convs: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract active conversation context and swarm agents hierarchy."""
        if not convs:
            default_ctx = {
                "conversation_id": "",
                "title": "Antigravity Idle",
                "project_name": "none",
                "context_tokens": 0,
                "context_formatted": "0",
                "input_tokens": 0,
                "cache_read_tokens": 0,
                "output_tokens": 0,
            }
            default_swarm = {
                "active_count": 0,
                "total_alive": 0,
                "is_working": false if "false" in locals() else False,
                "agents": [],
            }
            return default_ctx, default_swarm

        # Find active or most recent conversation
        active_row = None
        for c in convs:
            if c.get("not_fully_idle") == 1 or c.get("status") == "CASCADE_RUN_STATUS_RUNNING":
                active_row = c
                break
        if not active_row:
            active_row = convs[0]

        # Determine root conversation ID for swarm grouping
        active_cid = active_row["conversation_id"]
        parent_cid = active_row.get("parent_conversation_id") or ""
        root_cid = parent_cid if parent_cid else active_cid

        # Swarm members sharing root or parent
        swarm_agents = []
        active_count = 0
        total_alive = 0

        for c in convs:
            cid = c["conversation_id"]
            pcid = c.get("parent_conversation_id") or ""
            is_member = (cid == root_cid) or (pcid == root_cid) or (cid == active_cid) or (pcid == active_cid)
            if not is_member:
                continue

            killed = bool(c.get("killed", 0))
            if killed:
                continue

            total_alive += 1
            name = c.get("agent_name") or ""
            if not name or name == "self":
                name = "coordinator" if cid == root_cid else "worker"

            role = "coordinator" if (cid == root_cid or name == "coordinator") else "worker"
            is_working = bool(c.get("not_fully_idle", 0) == 1 or c.get("status") == "CASCADE_RUN_STATUS_RUNNING")
            if is_working:
                active_count += 1

            status_str = "WORKING" if is_working else "IDLE"

            swarm_agents.append({
                "name": name,
                "role": role,
                "status": status_str,
                "is_working": is_working,
                "steps": c.get("step_count", 0),
            })

        # Sort agents so coordinator is first, then workers alphabetically
        swarm_agents.sort(key=lambda a: (0 if a["role"] == "coordinator" else 1, a["name"]))

        swarm_dict = {
            "active_count": active_count,
            "total_alive": total_alive,
            "is_working": active_count > 0,
            "agents": swarm_agents,
        }

        # Project name extraction from workspace_uris
        proj_name = "workspace"
        ws_uris = active_row.get("workspace_uris") or ""
        if ws_uris:
            try:
                uris = json.loads(ws_uris)
                if isinstance(uris, list) and uris:
                    path = uris[0].replace("file://", "")
                    proj_name = os.path.basename(path.rstrip("/")) or "workspace"
            except Exception:
                pass

        # Read last step metrics from active conversation's transcript.jsonl
        last_step_tokens = self.read_last_step_tokens(active_cid)

        input_tok = last_step_tokens.get("input_tokens", 0)
        cache_tok = last_step_tokens.get("cache_read_tokens", 0)
        output_tok = last_step_tokens.get("output_tokens", 0)
        context_tok = input_tok + cache_tok

        title = active_row.get("title") or active_row.get("preview") or "Antigravity Session"

        # Detect active model from conversation databases or state
        active_model, active_model_label, active_group_id = self.detect_active_model(active_cid, parent_cid)

        active_ctx = {
            "conversation_id": active_cid,
            "title": title,
            "project_name": proj_name,
            "context_tokens": context_tok,
            "context_formatted": format_tokens(context_tok),
            "input_tokens": input_tok,
            "cache_read_tokens": cache_tok,
            "output_tokens": output_tok,
            "active_model": active_model or "gemini-4-hydrogen-xhigh",
            "active_model_label": active_model_label or "Gemini 4 Hydrogen (XHigh)",
            "active_model_group": active_group_id or "gemini",
        }

        return active_ctx, swarm_dict

    def read_last_step_tokens(self, conv_id: str) -> Dict[str, int]:
        """Read tokens from the last non-empty step in transcript.jsonl."""
        transcript_path = self.gemini_dir / "brain" / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
        if not transcript_path.exists():
            return {"input_tokens": 0, "cache_read_tokens": 0, "output_tokens": 0}

        try:
            # Read last 32KB of file to find last line quickly
            with open(transcript_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                read_size = min(32768, size)
                f.seek(size - read_size)
                lines = f.read().decode("utf-8", errors="ignore").splitlines()

            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "input_tokens" in data:
                        return {
                            "input_tokens": data.get("input_tokens", 0),
                            "cache_read_tokens": data.get("cache_read_tokens", 0),
                            "output_tokens": data.get("output_tokens", 0),
                        }
                except Exception:
                    continue
        except Exception:
            pass

        return {"input_tokens": 0, "cache_read_tokens": 0, "output_tokens": 0}

    # ------------------------------------------------------------------
    # Incremental Transcript Indexing (Monthly Tokens & Projects)
    # ------------------------------------------------------------------
    def index_transcripts(
        self, convs: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Fast incremental indexer for transcript.jsonl across all brain/ sessions.
        Stores file mtime_ns and size in ~/.cache/antigravity-vu/transcript_index.json.
        """
        conv_ws_map = {}
        for c in convs:
            cid = c.get("conversation_id")
            ws_uris = c.get("workspace_uris") or ""
            path = ""
            if ws_uris:
                try:
                    uris = json.loads(ws_uris)
                    if isinstance(uris, list) and uris:
                        path = uris[0].replace("file://", "").rstrip("/")
                except Exception:
                    pass
            conv_ws_map[cid] = path

        # Load existing index cache
        cached_index = {}
        if self.transcript_index_file.exists():
            try:
                with open(self.transcript_index_file, "r", encoding="utf-8") as f:
                    cached_index = json.load(f).get("files", {})
            except Exception:
                pass

        new_index = {}
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        current_month = now_dt.strftime("%Y-%m")

        brain_dir = self.gemini_dir / "brain"
        transcript_files = list(brain_dir.glob("*/.system_generated/logs/transcript.jsonl"))

        for tf in transcript_files:
            tf_str = str(tf)
            conv_id = tf.parent.parent.parent.name
            try:
                st = tf.stat()
                mtime_ns = st.st_mtime_ns
                size = st.st_size
            except Exception:
                continue

            entry = cached_index.get(tf_str)
            if entry and entry.get("mtime_ns") == mtime_ns and entry.get("size") == size:
                # Cache is fresh
                new_index[tf_str] = entry
                continue

            # Parse transcript incrementally
            entry = {
                "mtime_ns": mtime_ns,
                "size": size,
                "conv_id": conv_id,
                "input_tokens": 0,
                "cache_read_tokens": 0,
                "output_tokens": 0,
                "months": {},
            }

            try:
                with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                        except Exception:
                            continue

                        in_tok = item.get("input_tokens", 0)
                        ca_tok = item.get("cache_read_tokens", 0)
                        out_tok = item.get("output_tokens", 0)
                        if not (in_tok or ca_tok or out_tok):
                            continue

                        entry["input_tokens"] += in_tok
                        entry["cache_read_tokens"] += ca_tok
                        entry["output_tokens"] += out_tok

                        c_at = item.get("created_at") or ""
                        month = c_at[:7] if len(c_at) >= 7 else current_month

                        if month not in entry["months"]:
                            entry["months"][month] = {"input": 0, "cache": 0, "output": 0}
                        entry["months"][month]["input"] += in_tok
                        entry["months"][month]["cache"] += ca_tok
                        entry["months"][month]["output"] += out_tok
            except Exception:
                pass

            new_index[tf_str] = entry

        # Save updated index
        try:
            with open(self.transcript_index_file, "w", encoding="utf-8") as f:
                json.dump({"files": new_index}, f)
        except Exception:
            pass

        # Aggregate monthly tokens
        monthly_in = 0
        monthly_ca = 0
        monthly_out = 0

        # Aggregate projects
        projects_dict: Dict[str, Dict[str, Any]] = {}

        for tf_str, entry in new_index.items():
            conv_id = entry.get("conv_id")
            ws_path = conv_ws_map.get(conv_id) or "/unknown"
            proj_name = os.path.basename(ws_path) if ws_path != "/unknown" else "Global/Other"

            # Month aggregation
            m_data = entry.get("months", {}).get(current_month)
            if m_data:
                monthly_in += m_data.get("input", 0)
                monthly_ca += m_data.get("cache", 0)
                monthly_out += m_data.get("output", 0)

            # Project aggregation
            if ws_path not in projects_dict:
                projects_dict[ws_path] = {
                    "name": proj_name,
                    "path": ws_path,
                    "input_tokens": 0,
                    "cache_read_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "conversations_count": 0,
                }
            p = projects_dict[ws_path]
            p["input_tokens"] += entry.get("input_tokens", 0)
            p["cache_read_tokens"] += entry.get("cache_read_tokens", 0)
            p["output_tokens"] += entry.get("output_tokens", 0)
            p["total_tokens"] = p["input_tokens"] + p["cache_read_tokens"] + p["output_tokens"]
            p["conversations_count"] += 1

        monthly_total = monthly_in + monthly_ca + monthly_out
        monthly_tokens = {
            "month": current_month,
            "input_tokens": monthly_in,
            "cache_read_tokens": monthly_ca,
            "output_tokens": monthly_out,
            "total_tokens": monthly_total,
            "input_formatted": format_tokens(monthly_in),
            "cache_formatted": format_tokens(monthly_ca),
            "output_formatted": format_tokens(monthly_out),
            "total_formatted": format_tokens(monthly_total),
        }

        # Format projects list sorted by total tokens descending
        projects_list = []
        for p in sorted(projects_dict.values(), key=lambda x: x["total_tokens"], reverse=True):
            p["input_formatted"] = format_tokens(p["input_tokens"])
            p["cache_formatted"] = format_tokens(p["cache_read_tokens"])
            p["output_formatted"] = format_tokens(p["output_tokens"])
            p["total_formatted"] = format_tokens(p["total_tokens"])
            projects_list.append(p)

        return monthly_tokens, projects_list

    # ------------------------------------------------------------------
    # Main Collect Entrypoint
    # ------------------------------------------------------------------
    def collect(self, pin_group_override: Optional[str] = None) -> Dict[str, Any]:
        """Execute full collection and return unified contract JSON."""
        prefs = self.get_preferences()
        if pin_group_override:
            prefs["pinned_group"] = pin_group_override
            self.save_preferences(prefs)

        pinned_pref = prefs.get("pinned_group", "auto")

        # 1. Discover Language Server daemon
        daemon_info = self.discover_daemon()

        # 2. Fetch live or cached quota
        ls_online, user_info, quota_raw = self.fetch_live_quota_and_user(daemon_info)

        # 3. Read conversation summaries & swarm info (and detect active model)
        convs = self.read_conversations_db()
        active_ctx, swarm_info = self.extract_active_context_and_swarm(convs)

        # 4. Transform quota with active model intelligence
        primary_quota, quota_groups = self.transform_quota_groups(
            quota_raw,
            pinned_group_pref=pinned_pref,
            active_model_group=active_ctx.get("active_model_group"),
            active_model_label=active_ctx.get("active_model_label"),
        )

        # 5. Index transcripts for monthly & project token telemetry
        monthly_tok, projects_list = self.index_transcripts(convs)

        now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

        return {
            "timestamp": now_iso,
            "user": user_info,
            "primary_quota": primary_quota,
            "quota_groups": quota_groups,
            "active_context": active_ctx,
            "swarm": swarm_info,
            "monthly_tokens": monthly_tok,
            "projects": projects_list,
        }


# ----------------------------------------------------------------------
# Terminal Pretty Printer (ANSI UI)
# ----------------------------------------------------------------------
def render_progress_bar(pct: float, width: int = 24) -> str:
    """Render ANSI colored progress bar."""
    filled_len = int(round(width * (pct / 100.0)))
    bar = "█" * filled_len + "░" * (width - filled_len)
    if pct > 50.0:
        color = "\033[92m"  # Green
    elif pct >= 20.0:
        color = "\033[93m"  # Amber
    else:
        color = "\033[91m"  # Red
    reset = "\033[0m"
    return f"{color}{bar}{reset} {pct:5.1f}%"


def print_pretty_dashboard(data: Dict[str, Any]) -> None:
    """Display modern terminal dashboard for Antigravity View Usage."""
    user = data.get("user", {})
    primary = data.get("primary_quota", {})
    active = data.get("active_context", {})
    swarm = data.get("swarm", {})
    monthly = data.get("monthly_tokens", {})
    groups = data.get("quota_groups", [])

    online_badge = "\033[92m● ONLINE\033[0m" if user.get("ls_online") else "\033[91m○ CACHED\033[0m"
    status_color = "\033[92m" if primary.get("status_level") == "healthy" else ("\033[93m" if primary.get("status_level") == "warning" else "\033[91m")

    print("\033[2J\033[H" if os.environ.get("AG_WATCH") else "", end="")
    print("\033[1;36m╭────────────────────────────────────────────────────────────────────────────╮\033[0m")
    print(f"\033[1;36m│\033[0m  \033[1;37mANTIGRAVITY DYNAMIC ISLAND (ag-vu)\033[0m     {online_badge}  Tier: \033[1;33m{user.get('tier', 'Pro')}\033[0m  User: \033[1;37m{user.get('name', 'User')}\033[0m \033[1;36m│\033[0m")
    print("\033[1;36m├────────────────────────────────────────────────────────────────────────────┤\033[0m")

    # Dynamic Island Pill Preview
    dot = "🟢" if primary.get("status_level") == "healthy" else ("🟡" if primary.get("status_level") == "warning" else "🔴")
    pill_text = f" {dot} {primary.get('group', 'Quota')} {primary.get('remaining_pct', 0.0):.0f}% ({primary.get('reset_in', '--')}) │ 🧠 {active.get('context_formatted', '0')} │ 🐝 {swarm.get('active_count', 0)}/{swarm.get('total_alive', 0)} "
    print(f"\033[1;36m│\033[0m  Top Bar Pill: \033[48;5;235m\033[1;37m{pill_text}\033[0m")
    print("\033[1;36m├────────────────────────────────────────────────────────────────────────────┤\033[0m")

    # Quota Section
    print("\033[1;36m│\033[0m  \033[1;34mAPI QUOTA & LIMITS\033[0m")
    for g in groups:
        print(f"\033[1;36m│\033[0m   \033[1;37m{g['name']}:\033[0m")
        for b in g.get("buckets", []):
            bar = render_progress_bar(b["remaining_pct"], 20)
            print(f"\033[1;36m│\033[0m     • {b['label']:<8} {bar}  (Resets in: {b['reset_in']})")

    # Active Session & Swarm Section
    print("\033[1;36m├────────────────────────────────────────────────────────────────────────────┤\033[0m")
    print("\033[1;36m│\033[0m  \033[1;34mACTIVE CONTEXT & SWARM WORKERS\033[0m")
    print(f"\033[1;36m│\033[0m   Project: \033[1;32m{active.get('project_name')}\033[0m  Title: {active.get('title')[:45]}")
    print(f"\033[1;36m│\033[0m   Model: \033[1;36m{active.get('active_model_label', 'Unknown')}\033[0m  Context: \033[1;33m{active.get('context_formatted')}\033[0m tokens (Input: {active.get('input_tokens')}, Cache: {active.get('cache_read_tokens')}, Output: {active.get('output_tokens')})")

    if swarm.get("agents"):
        agent_strs = []
        for ag in swarm["agents"]:
            st_color = "\033[92m" if ag["is_working"] else "\033[90m"
            agent_strs.append(f"{st_color}{ag['name']}({ag['steps']})\033[0m")
        print(f"\033[1;36m│\033[0m   Swarm: {', '.join(agent_strs)}")

    # Monthly Tokens & Projects Section
    print("\033[1;36m├────────────────────────────────────────────────────────────────────────────┤\033[0m")
    print(f"\033[1;36m│\033[0m  \033[1;34mTELEMETRY ({monthly.get('month', '')})\033[0m")
    print(f"\033[1;36m│\033[0m   Total: \033[1;35m{monthly.get('total_formatted')}\033[0m (Input: {monthly.get('input_formatted')}, Cache: {monthly.get('cache_formatted')}, Output: {monthly.get('output_formatted')})")

    projects = data.get("projects", [])[:3]
    if projects:
        print("\033[1;36m│\033[0m   Top Projects:")
        for p in projects:
            print(f"\033[1;36m│\033[0m     - {p['name']:<20} {p['total_formatted']:>8} tokens ({p['conversations_count']} sessions)")

    print("\033[1;36m╰────────────────────────────────────────────────────────────────────────────╯\033[0m")


# ----------------------------------------------------------------------
# CLI Argument Parsing & Execution
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Antigravity View Usage (ag-vu) Collector & CLI telemetry tool"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON according to contract (default when called non-interactively)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Render rich colored terminal dashboard",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously update terminal dashboard every 2 seconds",
    )
    parser.add_argument(
        "--pin-group",
        type=str,
        help="Pin primary quota group (auto, argon, gemini, 3p)",
    )

    args = parser.parse_args()
    collector = AntigravityCollector()

    if args.pin_group:
        collector.get_preferences()
        collector.save_preferences({"pinned_group": args.pin_group})

    if args.watch:
        os.environ["AG_WATCH"] = "1"
        try:
            while True:
                data = collector.collect(pin_group_override=args.pin_group)
                print_pretty_dashboard(data)
                time.sleep(2.0)
        except KeyboardInterrupt:
            print("\nExiting ag-vu watch mode.")
            sys.exit(0)

    # Collect data
    data = collector.collect(pin_group_override=args.pin_group)

    # If --pretty explicitly given, print dashboard.
    # Otherwise, if --json or stdout is redirected / pipe, output JSON.
    if args.pretty:
        print_pretty_dashboard(data)
    elif args.json or not sys.stdout.isatty():
        print(json.dumps(data, indent=2))
    else:
        # If in TTY and no flag given, pretty is convenient for developer
        print_pretty_dashboard(data)


if __name__ == "__main__":
    main()
