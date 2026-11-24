#!/usr/bin/env python3
"""Probe user-supplied HoYoLAB official category URLs; no publication or credentials."""
import json
from pathlib import Path
import urllib.request
import urllib.parse
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
sources = json.loads((ROOT / "config/official_sources.json").read_text(encoding="utf-8"))["hoyolab"]["sources"]
for item in sources:
    url = item["url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            final = resp.geturl()
            if urllib.parse.urlsplit(final).hostname != "www.hoyolab.com":
                raise ValueError("Redirected away from HoYoLAB")
            raw = resp.read(500001)
            if len(raw) > 500000:
                raise ValueError("Response too large")
            body = raw.decode("utf-8", errors="replace")
            print(json.dumps({"game":item["id"],"http_status":resp.status,"bytes":len(raw),"has_html":("<html" in body.lower()),"article_links_detected":body.count("/article/"),"note":"HTML presence does not prove announcement extraction works"},ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"game":item["id"],"error":str(e)},ensure_ascii=False))
