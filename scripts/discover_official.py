#!/usr/bin/env python3
"""Discover candidate announcements from allowlisted official pages.

Discovery is NOT verification. Never modifies data/updates.json.
Only official HTTPS links and titles are recorded for later review.
"""
from concurrent.futures import ThreadPoolExecutor
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "official_sources.json"
OUTPUT = ROOT / "data" / "announcement_candidates.json"
KEYWORDS = re.compile(r"卡池|祈願|躍遷|調頻|版本|前瞻|直播|更新|活動|限定|復刻|wish|banner|signal search|channel|version|special program|update", re.I)

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []
    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(self.text).strip()))
            self.href = None
            self.text = []

def brown_dust_notes():
    endpoint = "https://webapi.browndust2.com/api/notices?locale=zh-tw&page=0&limit=5&category=update"
    with urllib.request.urlopen(endpoint, timeout=25) as response:
        payload = json.load(response)
    notes = []
    for item in payload["items"]:
        if item.get("category") != "update" or not re.fullmatch(r"[A-Za-z0-9_-]+", str(item.get("id") or "")):
            continue
        notes.append({"game": "bd2", "title": item["subject"],
                      "url": "https://www.browndust2.com/zh-tw/news/view?id=" + str(item["id"]),
                      "status": "pending_review"})
    if not notes:
        raise ValueError("No Traditional Chinese developer notes returned")
    return notes


def discover(src):
    if src["id"] == "bd2":
        return brown_dust_notes()
    url = src["url"]
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != src["domain"]:
        raise ValueError("Official source hostname mismatch")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GachaWatchTW/1.0)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.geturl().split("/")[2].lower() != src["domain"]:
            raise ValueError("Redirected away from official hostname")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("HTML page exceeds size limit")
        page = raw.decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(page)
    found = {}
    for href, title in parser.links:
        target = urllib.parse.urljoin(url, html.unescape(href))
        parts = urllib.parse.urlsplit(target)
        if parts.scheme != "https" or parts.hostname != src["domain"]:
            continue
        title = re.sub(r"\s+", " ", html.unescape(title)).strip()[:240]
        if len(title) < 5 or not KEYWORDS.search(title):
            continue
        clean = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        found[clean] = {"game": src["id"], "title": title, "url": clean, "status": "pending_review"}
    return list(found.values())[:100]

def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"candidates": []}
    saved = {(x["game"], x["url"]): x for x in previous.get("candidates", [])}
    errors = []
    counts = {}
    enabled = [src for src in cfg["sources"] if src.get("enabled")]
    with ThreadPoolExecutor(max_workers=5) as pool:
        pending = [(src, pool.submit(discover, src)) for src in enabled]
        for src, check in pending:
            try:
                candidates = check.result()
                counts[src["id"]] = len(candidates)
                for item in candidates:
                    saved.setdefault((item["game"], item["url"]), item)
            except Exception as exc:
                errors.append({"game": src["id"], "error": str(exc)})
    result = {"schema": 1, "candidates": sorted(saved.values(), key=lambda x: (x["game"], x["url"]))}
    if result != {"schema": 1, "candidates": previous.get("candidates", [])}:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"discovered": counts, "total_pending": len(saved), "errors": errors}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
