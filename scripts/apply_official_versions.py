#!/usr/bin/env python3
"""Publish explicitly dated version records from accepted official notices."""
import datetime as dt
import json
import re

from advance_versions import DATA, ROOT, advance, timestamp, valid_version
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


PREVIEW_TITLE = re.compile(r"前瞻|特別節目|直播")
PREVIEW_TIME = re.compile(r"(?:直播|播出|前瞻)(?:開始)?時間\s*[：:]\s*([^\n]+)")
STREAM_URL = re.compile(r"https://(?:www\.)?(?:youtube\.com/(?:live/|watch\?v=)|youtu\.be/)[A-Za-z0-9_-]{11}(?![A-Za-z0-9_-])")


def preview_from_notice(notice):
    if not valid_notice(notice) or not PREVIEW_TITLE.search(notice["title"]):
        return None
    body = notice.get("traditional_chinese_excerpt") or ""
    lines = PREVIEW_TIME.findall(body)
    times = verified_times(lines[0]) if len(lines) == 1 else []
    if len(times) != 1:
        return None
    links = set(STREAM_URL.findall(body))
    return {"start": times[0]["iso"], "url": next(iter(links)) if len(links) == 1 else None,
            "source": notice["url"], "version": notice.get("version")}


def publish(doc, now):
    result, _ = advance(doc, now)
    games = []
    for original in result.get("games", []):
        game = dict(original)
        if game.get("official_source_verified") is True:
            archived = {h["version"] for h in result.get("history", [])
                        if h.get("game") == game["id"]}
            records = {}
            previews = {}
            for notice in game.get("official_announcements", []):
                preview = preview_from_notice(notice)
                if preview and preview["version"] and timestamp(preview["start"]) >= now:
                    previews.setdefault(preview["version"], preview)
                record = version_from_notice(notice)
                if record and record["version"] not in archived:
                    records.setdefault(record["version"], record)
            for field in ("current_version", "next_version"):
                existing = game.get(field)
                if valid_version(existing):
                    records.setdefault(existing["version"], existing)
            active = [r for r in records.values() if timestamp(r["start"]) <= now and (not r.get("end") or now < timestamp(r["end"]))]
            current = game.get("current_version")
            if len(active) == 1 and not valid_version(current):
                game["current_version"] = current = active[0]
            floor = (timestamp(current.get("end")) or now) if valid_version(current) else now
            future = sorted((r for r in records.values() if timestamp(r["start"]) >= floor
                             and timestamp(r["start"]) > now), key=lambda r: timestamp(r["start"]))
            if future and (len(future) == 1 or future[0]["start"] != future[1]["start"]):
                existing = game.get("next_version")
                if not valid_version(existing):
                    game["next_version"] = future[0]
            next_version = game.get("next_version")
            if valid_version(next_version) and next_version["version"] in previews:
                game["next_version"] = {**next_version, "preview": previews[next_version["version"]]}
            current_number = game.get("current_version") or {}
            pending = [preview for version, preview in previews.items()
                       if version not in archived and version != current_number.get("version")]
            if not valid_version(next_version) and len(pending) == 1:
                game["upcoming_preview"] = pending[0]
            else:
                game.pop("upcoming_preview", None)
        games.append(game)
    return {**result, "games": games}


def merge_verified_releases(doc, feed, now):
    """Merge independently sourced announcements without replacing other games."""
    if feed.get("schema") != 1:
        raise ValueError("Unsupported verified-release schema")
    config = json.loads((ROOT / "config/official_sources.json").read_text())
    allowed = {source["id"] for source in config["sources"]}
    games = {game["id"]: dict(game) for game in doc["games"]}
    for game_id, entries in feed["games"].items():
        if game_id not in allowed:
            continue
        game = games.setdefault(game_id, {"id": game_id})
        current = game.get("current_version") or {}
        upcoming = game.get("next_version") or {}
        record = entries.get("next_version")
        if valid_version(record):
            start = timestamp(record["start"])
            current_start = timestamp(current.get("start"))
            upcoming_start = timestamp(upcoming.get("start"))
            if current_start == start and current["version"] == record["version"]:
                game["current_version"] = merge_release(current, record)
            elif (not current_start or start > current_start) and (
                    not upcoming_start or upcoming["version"] == record["version"] or start <= upcoming_start):
                if not upcoming_start or upcoming["version"] != record["version"]:
                    upcoming = {}
                game["next_version"] = merge_release(upcoming, record)
        preview = entries.get("upcoming_preview") or {}
        preview_start = timestamp(preview.get("start"))
        if (preview_start and preview_start >= now and preview.get("version") != current.get("version")
                and str(preview.get("source")).startswith("https://")):
            game["upcoming_preview"] = preview
    return {**doc, "games": list(games.values())}


def merge_release(previous, incoming):
    phases = {(p.get("characters"), p.get("start")): p for p in previous.get("phases", [])}
    for phase in incoming.get("phases", []):
        if not isinstance(phase, dict) or not phase.get("characters") or not timestamp(phase.get("start")):
            continue
        if not str(phase.get("source")).startswith("https://"):
            continue
        key = (phase["characters"], phase["start"])
        prior = phases.get(key, {})
        phases[key] = {**prior, **phase, "banner_image": phase.get("banner_image") or prior.get("banner_image")}
    return {**previous, **incoming, "end": incoming.get("end") or previous.get("end"), "phases": list(phases.values())}


if __name__ == "__main__":
    old = json.loads(DATA.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    releases = json.loads((DATA.parent / "verified-releases.json").read_text(encoding="utf-8"))
    result = advance(merge_verified_releases(publish(old, now), releases, now), now)[0]
    if result != old:
        save(DATA, {**result, "updated_at": now.isoformat()})
