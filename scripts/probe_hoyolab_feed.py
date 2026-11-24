#!/usr/bin/env python3
"""Second-round read-only HoYoLAB discovery probe. No credentials, no publication."""
import json
import urllib.parse
import urllib.request
import urllib.error

GAMES = {"genshin": 2, "hsr": 6, "zzz": 8}
BASE = "https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList"
for game, gid in GAMES.items():
    for category in (1, 3):
        url = BASE + "?" + urllib.parse.urlencode({"gids":gid,"type":category,"page_size":10})
        try:
            request = urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json","Referer":"https://www.hoyolab.com/"})
            with urllib.request.urlopen(request,timeout=20) as response:
                raw=response.read(500001)
                if len(raw)>500000: raise ValueError("oversized response")
                doc=json.loads(raw)
                data=doc.get("data") or {}
                posts=data.get("list") or []
                samples=[]
                for entry in posts[:3]:
                    post=entry.get("post") or {}
                    samples.append({"post_id":str(post.get("post_id","")),"title":str(post.get("subject",""))[:140],"official_flag":(post.get("post_status") or {}).get("is_official")})
                print(json.dumps({"game":game,"category":category,"http":response.status,"retcode":doc.get("retcode"),"count":len(posts),"samples":samples,"status":"probe_only_unverified"},ensure_ascii=False))
        except (urllib.error.URLError,ValueError,KeyError,TypeError) as exc:
            print(json.dumps({"game":game,"category":category,"error":str(exc),"status":"probe_failed"},ensure_ascii=False))
