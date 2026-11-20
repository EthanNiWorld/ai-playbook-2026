"""daily_audit 离线回归：不访问 ECS/OSS、不调评审模型。"""

import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import daily_audit as audit


class DailyAuditTest(unittest.TestCase):
    def test_internal_sessions_are_excluded(self):
        self.assertTrue(audit.INTERNAL_SESSION_RE.match("judge-123"))
        self.assertTrue(audit.INTERNAL_SESSION_RE.match("diagnose-123"))
        self.assertFalse(audit.INTERNAL_SESSION_RE.match("browser-session-123"))

    def test_hard_failure_and_slow_signals(self):
        row = audit.inspect_row({
            "id": 1, "question": "价格", "answer": "见 knowledge/qwen.md",
            "sources_json": "[]", "price_status": "official",
            "price_audit": "mismatch:$1", "latency_ms": 120001,
            "interrupted": 0, "feedback": "down",
        })
        self.assertIn("price_mismatch", row["flags"])
        self.assertIn("internal_path_leak", row["flags"])
        self.assertIn("feedback_down", row["flags"])
        self.assertIn("slow_over_120s", row["flags"])
        self.assertEqual(audit._final_verdict(row), "fail")

    def test_unreviewed_is_not_pass(self):
        row = audit.inspect_row({
            "id": 2, "question": "你好", "answer": "你好，有什么可以帮你？",
            "sources_json": "[]", "price_status": "", "price_audit": "",
            "latency_ms": 100, "interrupted": 0, "feedback": None,
        })
        self.assertEqual(row["flags"], [])
        self.assertEqual(audit._final_verdict(row), "unreviewed")

    def test_recommendation_contains_impact_and_regression(self):
        row = {
            "id": 3, "verdict": "warn",
            "judge": {"category": "followup", "suggestion": "补充多轮上下文", "needs_replay": True},
        }
        rec = audit._recommendations([row])[0]
        self.assertEqual(rec["category"], "followup")
        self.assertIn("影响", rec["impact"])
        self.assertIn("test_followup.py", rec["regression"])
        self.assertTrue(rec["needs_replay"])

    def test_malformed_sources_do_not_break_audit(self):
        row = audit.inspect_row({
            "id": 4, "question": "价格", "answer": "回答",
            "sources_json": "not-json", "price_status": "official", "price_audit": "ok",
            "latency_ms": 1000, "interrupted": 0, "feedback": None,
        })
        self.assertEqual(row["source_count"], 0)
        self.assertIn("official_without_sources", row["flags"])

    def test_screenshot_totals_are_not_hard_fail_without_semantic_review(self):
        row = audit.inspect_row({
            "id": 5, "question": "多少钱（附 1 张截图）", "answer": "| 小计 |\n| $10 |",
            "sources_json": "[]", "price_status": "official", "price_audit": "mismatch:10",
            "latency_ms": 1000, "interrupted": 0, "feedback": None,
        })
        self.assertIn("derived_price_audit", row["flags"])
        self.assertNotIn("price_mismatch", row["flags"])
        self.assertEqual(audit._final_verdict(row), "warn")

    def test_later_explicit_correction_confirms_previous_failure(self):
        previous = {"id": 10, "session_id": "s", "answer": "错误合计", "flags": []}
        later = {"id": 11, "session_id": "s", "answer": "确实算错，上一轮误写为 10 倍", "flags": []}
        audit._mark_later_corrections([previous, later])
        self.assertIn("later_corrected_error", previous["flags"])
        self.assertEqual(previous["corrected_by"], 11)
        self.assertEqual(audit._final_verdict(previous), "fail")

    def test_failed_judge_ids_can_be_read_beyond_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "qa.db"
            conn = sqlite3.connect(db)
            conn.execute("""CREATE TABLE answers (
                id INTEGER, session_id TEXT, question TEXT, answer TEXT, sources_json TEXT,
                price_status TEXT, price_audit TEXT, llm_model TEXT, latency_ms INTEGER,
                interrupted INTEGER, created_at TEXT, feedback TEXT, feedback_reason TEXT)""")
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            conn.execute("INSERT INTO answers VALUES (1,'s','q','a','[]','','','',1,0,?,'','')", (now,))
            conn.commit()
            conn.close()
            rows, _ = audit._read_rows(db, after_id=2, since_hours=24, include_ids=[1])
            self.assertEqual([x["id"] for x in rows], [1])


if __name__ == "__main__":
    unittest.main()
