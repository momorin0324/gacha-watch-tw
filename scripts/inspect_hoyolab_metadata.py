#!/usr/bin/env python3
"""Inspect HoYoLAB feed metadata to design an official-only verifier.

Read-only diagnostic. Never writes website data or claims posts are verified.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/"config/official_sources.json").read_text(encoding="utf-8"))
games={"genshin":2,"hsr":6,"zzz":8}
endpoint="https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList"
for game,gid in games.items():
    for category in (1,3):
        url=endpoint+"?"+urllib.parse.urlencode({"gids":gid,"type":category,"page_size":10})
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.hoyolab.com/","Accept":"application/json"})
            with urllib.request.urlopen(request,timeout=20) as response:
                if urllib.parse.urlsplit(response.geturl()).hostname!="bbs-api-os.hoyolab.com":
                    raise ValueError("Unexpected redirect")
                raw=response.read(500001)
                if len(raw)>500000: raise ValueError("Oversized response")
                doc=json.loads(raw)
            items=(doc.get("data") or {}).get("list") or []
            samples=[]
            for item in items[:3]:
                post=item.get("post") or {}
                user=item.get("user") or {}
                samples.append({"id":str(post.get("post_id","")),"title":str(post.get("subject",""))[:160],
                                "post_keys":sorted(post.keys())[:50],
                                "user_keys":sorted(user.keys())[:35],
                                "user_id":str(user.get("uid","")),
                                "nickname":str(user.get("nickname",""))[:80],
                                "created_at":post.get("created_at"),
                                "is_official_value":post.get("is_official"),
                                "user_is_official":user.get("is_official"),
                                "is_top":post.get("is_top")})
            print(json.dumps({"game":game,"category":category,"retcode":doc.get("retcode"),
                              "count":len(items),"samples":samples,
                              "verified":False,"publication":"disabled"},ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"game":game,"category":category,"error":str(exc)},ensure_ascii=False))
