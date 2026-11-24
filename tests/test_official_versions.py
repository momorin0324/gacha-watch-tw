import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_official_versions import publish


class OfficialVersionPublicationTests(unittest.TestCase):
    def setUp(self):
        self.notice = {
            "title": "9.9版本更新說明",
            "version": "9.9",
            "url": "https://www.hoyolab.com/article/123",
            "traditional_chinese_excerpt":
                "版本期間：2026/12/01 UTC+8 12:00～2026/12/21 UTC+8 12:00",
        }
        self.doc = {"games": [{
            "id": "genshin", "official_source_verified": True,
            "official_announcements": [self.notice],
        }], "history": []}
        self.before = dt.datetime(2026, 11, 30, tzinfo=dt.timezone.utc)

    def test_publish_promote_archive(self):
        future = publish(self.doc, self.before)
        self.assertEqual(future["games"][0]["next_version"]["version"], "9.9")
        active = publish(future, self.before + dt.timedelta(days=2))
        self.assertEqual(active["games"][0]["current_version"]["version"], "9.9")
        self.assertIsNone(active["games"][0]["next_version"])
        now = self.before + dt.timedelta(days=25)
        ended = publish(active, now)
        self.assertIsNone(ended["games"][0]["current_version"])
        self.assertEqual([record["version"] for record in ended["history"]], ["9.9"])
        self.assertEqual(publish(ended, now), ended)

    def test_ignore_maintenance_and_unknown_timezone(self):
        for text in (
            self.notice["traditional_chinese_excerpt"].replace("版本期間", "維護時間"),
            self.notice["traditional_chinese_excerpt"].replace("UTC+8 ", ""),
        ):
            with self.subTest(text=text):
                self.notice["traditional_chinese_excerpt"] = text
                self.assertEqual(publish(self.doc, self.before), self.doc)
