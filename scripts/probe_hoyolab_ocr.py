#!/usr/bin/env python3
"""Read-only HoYoLAB image OCR probe. Never updates published game data."""
import io,json,re,urllib.parse,urllib.request
from PIL import Image,ImageOps
import pytesseract
BASE="https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList"
HOSTS={"upload-os-bbs.hoyolab.com"}
def image_urls(obj):
    found=set()
    if isinstance(obj,dict):
        for k,v in obj.items():
            if isinstance(v,str) and k in ("url","image_url","src","cover"):
                u=urllib.parse.urlsplit(v)
                if u.scheme=="https" and u.hostname in HOSTS:found.add(v)
            else:found.update(image_urls(v))
    elif isinstance(obj,list):
        for x in obj:found.update(image_urls(x))
    return found
def fetch(url,limit):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.hoyolab.com/"})
    with urllib.request.urlopen(req,timeout=25) as r:
        u=urllib.parse.urlsplit(r.geturl())
        allowed={"bbs-api-os.hoyolab.com"}|HOSTS
        if u.scheme!="https" or u.hostname not in allowed:raise ValueError("Unexpected redirect")
        raw=r.read(limit+1)
        if len(raw)>limit:raise ValueError("Response exceeds size limit")
        return raw
for game,gid in {"genshin":2,"hsr":6,"zzz":8}.items():
    try:
        feed=BASE+"?"+urllib.parse.urlencode({"gids":gid,"type":1,"page_size":5})
        doc=json.loads(fetch(feed,800000))
        items=(doc.get("data") or {}).get("list") or []
        chosen=None
        for item in items:
            post=item.get("post") or {}
            urls=image_urls(item)
            content=post.get("content")
            if isinstance(content,str):
                try:urls.update(image_urls(json.loads(content)))
                except ValueError:pass
            if urls:
                chosen=(post,sorted(urls));break
        if not chosen:
            print(json.dumps({"game":game,"status":"no_images_found","published":False}));continue
        post,urls=chosen
        # Probe only one image per game; skip tiny graphics and huge files.
        url=urls[0]
        raw=fetch(url,5000000)
        img=Image.open(io.BytesIO(raw))
        img.verify()
        img=Image.open(io.BytesIO(raw))
        if img.width*img.height>12000000:raise ValueError("Image dimensions exceed limit")
        img=ImageOps.exif_transpose(img).convert("RGB")
        txt=pytesseract.image_to_string(img,lang="eng+chi_tra",config="--psm 11",timeout=25)
        txt=re.sub(r"\\s+"," ",txt).strip()
        print(json.dumps({"game":game,"post_id":str(post.get("post_id","")),
          "image_size":[img.width,img.height],"ocr_excerpt":txt[:350],
          "ocr_chars":len(txt),"status":"ocr_unverified","published":False},ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"game":game,"status":"probe_error","error":str(e),"published":False},ensure_ascii=False))
