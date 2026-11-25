"""Import every pickup in three BannerHistory feeds, including client-side pages."""
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE = "https://bannerhistory.app"
SOURCES = {"bd2": "bd2", "gfl2": "gf2", "nikke": "nikke"}
SERVER = {"bd2": "國際服", "gfl2": "國際服（Sunborn）", "nikke": "國際服"}
KIND = {"original":"新品","new":"新品","rerun":"復刻","standard":"常駐","limited":"限定",
        "collab":"合作限定","collaboration":"合作限定","free":"免費贈送","welfare":"免費贈送"}
TZ = ZoneInfo("Asia/Taipei")


def rows_from_page(url, key):
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    soup = BeautifulSoup(r.content.decode("utf-8"), "html.parser")
    pieces = []
    for script in soup.find_all("script"):
        text = script.get_text()
        if text.startswith("self.__next_f.push("):
            part = json.loads(text[len("self.__next_f.push("):-1])
            if part[0] == 1:
                pieces.append(part[1])
    flight = "".join(pieces)
    match = re.search(r'"' + key + r'":\s*(?=\[\{"id":)', flight)
    if not match:
        raise ValueError(f"No full {key} array in {url}")
    rows = json.JSONDecoder().raw_decode(flight[match.end():])[0]
    count = re.search(r'(\d+)\s*(?:个|個)\s*(?:卡池|招募)', soup.get_text(" ",strip=True))
    if not count or int(count[1]) != len(rows):
        raise ValueError(f"Expected source count {count} but extracted {len(rows)} periods")
    data = {key:rows}

    def resolve(value):
        if value == "$undefined":
            return None
        if isinstance(value,str) and re.match(r'^\$[\da-f]+:.*:data:', value):
            path = value.split(":data:",1)[1].split(":")
            target = data
            for k in path:
                target = target[int(k)] if isinstance(target,list) else target[k]
            return resolve(target)
        if isinstance(value,dict):
            return {k:resolve(v) for k,v in value.items()}
        if isinstance(value,list):
            return [resolve(v) for v in value]
        return value
    return resolve(rows)


def local(value):
    if isinstance(value,dict):
        return next((value.get(k) for k in ("tw","zh","en","ko","ja") if value.get(k)), "")
    return value or ""


def timestamp(group, side):
    ms = group.get(side + "At")
    return datetime.fromtimestamp(ms / 1000, TZ).isoformat(timespec="seconds") if ms else group.get(side)


def image_url(obj):
    if isinstance(obj, str):
        if obj.startswith(("/", "https://")):
            return urljoin(BASE, obj)
    elif isinstance(obj,list):
        return next((url for item in obj if (url:=image_url(item))), "")
    elif isinstance(obj,dict):
        keys = ("tw","zh","en","ko","ja","url","src")
        return next((url for k in keys if (url:=image_url(obj.get(k)))), "")
    return ""


def convert(game, slug):
    url = f"{BASE}/tw/{slug}-pickup-history"
    nikke = game == "nikke"
    periods = rows_from_page(url, "pickups" if nikke else "rows")
    rows = []
    for period in periods:
        for group in period["groups"]:
            members = group["characters" if nikke else "members"]
            if not members:
                raise ValueError(f"Empty group {group['id']}")
            if nikke:
                tags = [group.get("runKind")] + (group.get("bannerTypes") or [])
                kind = "、".join(KIND.get(t,t) for t in tags if t)
                links = sorted(group.get("links") or [],key=lambda a:(a.get("locale") not in ("tw","zh-tw"),a.get("role") != "update"))
                official = next((a["url"] for a in links if a.get("url")),None)
                art = image_url(group.get("art") or group.get("bannerArt") or group.get("images"))
            else:
                kind = "、".join(local(b["labels"]) for b in group["badges"])
                official = next(iter(group.get("sources") or []),None)
                art = image_url(group.get("art"))
            for m in members:
                name = (m.get("twName") or m.get("enName")) if nikke else local(m["name"])+local(m.get("sub"))
                if nikke and m["id"] == "Sky": name = "思凱"
                portrait = image_url(m.get("icon"))
                title = local(period.get("labels") if nikke else period.get("title")) or name
                row = {"game":game,"periodId":period["id"],"groupId":group["id"],"title":title,"name":name,
                       "start":timestamp(group,"start"),"end":timestamp(group,"end"),"image":art or portrait,
                       "imageType":"banner" if art else "portrait" if portrait else None,"portrait":portrait,
                       "kind":kind,"source":url,"officialSource":official,"server":SERVER[game]}
                if not all(row[k] for k in ("start","end","name")):
                    raise ValueError(f"Missing core fields in {row}")
                rows.append(row)
    return rows


if __name__ == "__main__":
    directory=Path("data/history")
    directory.mkdir(parents=True,exist_ok=True)
    for game,slug in SOURCES.items():
        rows=convert(game,slug)
        (directory/f"{game}.json").write_text(json.dumps(rows,ensure_ascii=False,indent=1)+"\n")
        print(game,len(rows),"rows")
