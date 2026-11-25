#!/usr/bin/env python3
"""Read the Traditional Chinese Endfield news index and official version notices."""
import datetime as dt
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from advance_versions import DATA, advance, timestamp
from parse_official_announcements import clean
from sync_hoyolab_official import LOG, save

NEWS = "https://endfield.gryphline.com/zh-tw/news"
DATE = r"20\d{2}/\d{1,2}/\d{1,2} \d{1,2}:\d{2}"
UPDATE = re.compile(r"^「([^」]+)」版本更新說明$")
MAINTENANCE = re.compile(rf"^Asia\s*伺服器[：:]\s*({DATE})\s*~\s*({DATE})\s*\(UTC\+8\)", re.M)
BANNER = re.compile(r"^\d+\. 「([^」]+)」(特許尋訪|重構尋訪#\d+)\s*\n"
                    r"\s*· 開放時間[：:]([^\n]+)\n\s*· 尋訪說明[：:][^\n]*?"
                    r"6星幹員[【〖]([^】〗]+)[】〗]獲得機率提升", re.M)
FLIGHT = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
ZONE = dt.timezone(dt.timedelta(hours=8))


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as response:
        if urlsplit(response.geturl()).hostname != "endfield.gryphline.com":
            raise ValueError("Redirect away from official news domain")
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError("Official news page exceeds size limit")
    return body.decode("utf-8")


def news_items(html):
    state = "".join(json.loads(raw) for raw in FLIGHT.findall(html))
    decoder = json.JSONDecoder()
    items = {}
    for match in re.finditer(r'\{"cid":"[0-9]+"', state):
        try:
            item, _ = decoder.raw_decode(state, match.start())
        except ValueError:
            continue
        if item.get("title"):
            items[item["title"]] = item
    if not items:
        raise ValueError("Official Endfield news list was empty or changed format")
    return items


def taiwan(value):
    return dt.datetime.strptime(value, "%Y/%m/%d %H:%M").replace(tzinfo=ZONE).isoformat()


def notice(item, items, html):
    name = UPDATE.fullmatch(item["title"])[1]
    body = clean(html.split("</head>", 1)[-1])
    maintenance = MAINTENANCE.search(body)
    if not maintenance:
        raise ValueError("Missing explicit Asia maintenance window")
    boundary, start = map(taiwan, maintenance.groups())
    source = f"{NEWS}/{item['cid']}"
    phases = []
    for title, kind, window, character in BANNER.findall(body):
        first, separator, last = window.partition("~")
        if not separator:
            continue
        first, last = [s.replace("（伺服器時間）", "").strip() for s in (first, last)]
        if first == f"「{name}」版本更新後":
            phase_start = start
        elif re.fullmatch(DATE, first):
            phase_start = taiwan(first)
        else:
            continue
        if re.fullmatch(DATE, last):
            phase_end = taiwan(last)
        elif last == "版本更新維護前":
            phase_end = None
        else:
            continue
        if phase_end and timestamp(phase_end) <= timestamp(phase_start):
            continue
        banner = items.get(f"「{title}」{kind}", {})
        cover = banner.get("cover") or ""
        phases.append({"label": title, "characters": character, "start": phase_start,
                       "end": phase_end, "end_note": last if not phase_end else None,
                       "source": f"{NEWS}/{banner['cid']}" if banner else source,
                       "banner_image": cover if cover.startswith("https://web-static.hg-cdn.com/") else None,
                       "rerun_characters": [character] if kind.startswith("重構") else []})
    return {"version": {"穿越甚大蘑境與你相逢": "1.7"}.get(name, name), "title": name,
            "start": start, "end": None, "previous_end": boundary,
            "source": source, "verified": True, "phases": phases}


def sync(doc, now):
    items = news_items(fetch(NEWS))
    updates = sorted((item for title, item in items.items() if UPDATE.fullmatch(title)),
                     key=lambda item: item["displayTime"], reverse=True)
    if not updates:
        raise ValueError("No official version update notice found")
    latest = updates[0]
    record = notice(latest, items, fetch(f"{NEWS}/{latest['cid']}"))
    games = {g["id"]: g for g in doc["games"]}
    game = dict(games.get("endfield", {"id": "endfield"}))
    current, upcoming = game.get("current_version"), game.get("next_version")
    if current and timestamp(current["start"]) == timestamp(record["start"]):
        game["current_version"] = {**current, **record, "end": current.get("end")}
    elif not upcoming or timestamp(upcoming["start"]) <= timestamp(record["start"]):
        if not current or timestamp(current["start"]) < timestamp(record["start"]):
            game["next_version"] = record
    games["endfield"] = game
    return advance({**doc, "games": list(games.values())}, now)[0]


def run():
    old = json.loads(DATA.read_text(encoding="utf-8"))
    status = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    try:
        now = dt.datetime.now(dt.timezone.utc)
        new = sync(old, now)
        if new != old:
            save(DATA, {**new, "updated_at": now.isoformat()})
        status["endfield"] = {"status": "ok", "checked_at": now.isoformat()}
    except Exception as error:
        status["endfield"] = {"status": "error", "error": str(error)}
        raise
    finally:
        save(LOG, status)


if __name__ == "__main__":
    run()
