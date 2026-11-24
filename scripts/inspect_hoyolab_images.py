#!/usr/bin/env python3
"""Read-only probe: inspect text and image metadata of HoYoLAB official-feed posts.

No image downloads, OCR, credential use, or publishing. Output is diagnostic.
"""
import json, re, urllib.parse, urllib.request
from html import unescape

GAMES={"genshin":2,"hsr":6,"zzz":8}
BASE="https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList"
def images_in(obj, out):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in ("url","image_url","src","cover") and isinstance(v,str) and v.startswith("https://"):
                if re.search(r"image|img|upload|mihoyo|hoyolab",v,re.I):out.add(v)
            images_in(v,out)
    elif isinstance(obj,list):
        for v in obj:images_in(v,out)
for game,gid in GAMES.items():
    for category in (1,3):
        try:
            url=BASE+"?"+urllib.parse.urlencode({"gids":gid,"type":category,"page_size":5})
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.hoyolab.com/","Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=20) as resp:
                if urllib.parse.urlsplit(resp.geturl()).hostname!="bbs-api-os.hoyolab.com":raise ValueError("Unexpected redirect")
                raw=resp.read(800001)
                if len(raw)>800000:raise ValueError("Response too large")
                doc=json.loads(raw)
            posts=(doc.get("data") or {}).get("list") or []
            for entry in posts[:2]:
                post=entry.get("post") or {}
                pics=set()
                images_in(entry,pics)
                body=post.get("content") or ""
                if isinstance(body,str):
                    try:images_in(json.loads(body),pics)
                    except (ValueError,TypeError):pass
                print(json.dumps({"game":game,"category":category,"post_id":str(post.get("post_id","")),
                    "title":str(post.get("subject",""))[:120],
                    "body_chars":len(body) if isinstance(body,str) else 0,
                    "image_count":len(pics),"sample_image_hosts":sorted({urllib.parse.urlsplit(x).hostname for x in pics})[:6],
                    "has_images_field":bool(post.get("images")),
                    "status":"pending_verification","published":False},ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"game":game,"category":category,"error":str(exc)},ensure_ascii=False))
