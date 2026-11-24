#!/usr/bin/env python3
"""Publish explicitly dated version records from accepted official notices."""
import datetime as dt
import json
import re

from advance_versions import DATA, advance, timestamp, valid_version
from parse_official_announcements import verified_times
from sync_hoyolab_official import save, valid_notice

# The labels must identify version boundaries, not maintenance or event times.
WINDOW = re.compile(
    r"^(?:遊戲)?版本(?:期間|時間|開放期間)\s*[：:]\s*(.+)$", re.M
)
RANGE = re.compile(r"\s*(?:～|~|至|—|–)\s*")
VERSION_TITLE = re.compile(r"版本(?:更新說明|更新公告|前瞻|特別節目)|版本「.+」更新公告")


def explicit_range(line):
    parts = RANGE.split(line)
    if len(parts) != 2:
        return None
    times = [verified_times(part.strip()) for part in parts]
    if any(len(items) != 1 or items[0]["source"] != part.strip()
           for items, part in zip(times, parts)):
        return None
    start, end = [items[0]["iso"] for items in times]
    return (start, end) if timestamp(start) < timestamp(end) else None


def version_from_notice(notice):
    if not valid_notice(notice) or not VERSION_TITLE.search(notice["title"]):
        return None
    number = notice.get("version")
    if not isinstance(number, str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", number):
        return None
    matches = WINDOW.findall(notice.get("traditional_chinese_excerpt") or "")
    dates = explicit_range(matches[0]) if len(matches) == 1 else None
    if not dates:
        return None
    return {"version": number, "start": dates[0], "end": dates[1],
            "verified": True, "source": notice["url"]}


def publish(doc, now):
    result, _ = advance(doc, now)
    games = []
    for original in result.get("games", []):
        game = dict(original)
        if game.get("official_source_verified") is True:
            archived = {h["version"] for h in result.get("history", [])
                        if h.get("game") == game["id"]}
            records = {}
            for notice in game.get("official_announcements", []):
                record = version_from_notice(notice)
                if record and record["version"] not in archived:
                    records.setdefault(record["version"], record)
            for field in ("current_version", "next_version"):
                existing = game.get(field)
                if valid_version(existing):
                    records.setdefault(existing["version"], existing)
            active = [r for r in records.values() if timestamp(r["start"]) <= now < timestamp(r["end"])]
            current = game.get("current_version")
            if len(active) == 1 and not valid_version(current):
                game["current_version"] = current = active[0]
            floor = timestamp(current["end"]) if valid_version(current) else now
            future = sorted((r for r in records.values() if timestamp(r["start"]) >= floor
                             and timestamp(r["start"]) > now), key=lambda r: timestamp(r["start"]))
            if future and (len(future) == 1 or future[0]["start"] != future[1]["start"]):
                existing = game.get("next_version")
                if not valid_version(existing):
                    game["next_version"] = future[0]
        games.append(game)
    return {**result, "games": games}


if __name__ == "__main__":
    old = json.loads(DATA.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    result = publish(old, now)
    if result != old:
        save(DATA, {**result, "updated_at": now.isoformat()})
