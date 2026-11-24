#!/usr/bin/env python3
"""Read-only Traditional Chinese and numeric OCR evaluation on HoYoLAB images."""
import io,json,re,urllib.parse,urllib.request
from PIL import Image,ImageOps,ImageEnhance,ImageFilter
import pytesseract
HOST="upload-os-bbs.hoyolab.com"
BASE="https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList"
def fetch(url,allowed,limit):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.hoyolab.com/"})
    with urllib.request.urlopen(req,timeout=25) as r:
        u=urllib.parse.urlsplit(r.geturl())
        if u.scheme!="https" or u.hostname not in allowed:raise ValueError("Unexpected redirect")
        b=r.read(limit+1)
        if len(b)>limit:raise ValueError("Too large")
        return b
def urls(obj):
    out=set()
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in ("url","image_url","src","cover") and isinstance(v,str) and urllib.parse.urlsplit(v).hostname==HOST and v.startswith("https://"):out.add(v)
            else:out.update(urls(v))
    elif isinstance(obj,list):
        for v in obj:out.update(urls(v))
    return out
for game,gid in {"genshin":2,"hsr":6,"zzz":8}.items():
    try:
        feed=BASE+"?"+urllib.parse.urlencode({"gids":gid,"type":1,"page_size":5})
        doc=json.loads(fetch(feed,{"bbs-api-os.hoyolab.com"},800000))
        candidates=[]
        for entry in ((doc.get("data") or {}).get("list") or [])[:5]:
            post=entry.get("post") or {}
            found=urls(entry)
            if isinstance(post.get("content"),str):
                try:found.update(urls(json.loads(post["content"])))
                except ValueError:pass
            for url in sorted(found)[:12]:
                try:
                    raw=fetch(url,{HOST},5000000)
                    img=Image.open(io.BytesIO(raw))
                    if img.width*img.height>12000000:continue
                    if img.width<500 or img.height<250:continue
                    candidates.append((img.width*img.height,post.get("post_id"),img.copy()))
                except Exception:continue
        if not candidates:
            print(json.dumps({"game":game,"status":"no_large_image","published":False}));continue
        _,postid,img=max(candidates,key=lambda x:x[0])
        img=ImageOps.exif_transpose(img).convert("RGB")
        if img.width<1600:
            scale=min(2,1600/img.width)
            img=img.resize((round(img.width*scale),round(img.height*scale)))
        enhanced=ImageEnhance.Contrast(ImageOps.grayscale(img)).enhance(1.6).filter(ImageFilter.SHARPEN)
        results={}
        for name,im,lang in [("traditional",img,"chi_tra+eng"),("high_contrast",enhanced,"chi_tra+eng")]:
            s=pytesseract.image_to_string(im,lang=lang,config="--psm 11",timeout=30)
            results[name]={"characters":len(s.strip()),"sample":re.sub(r"\\s+"," ",s).strip()[:260]}
        print(json.dumps({"game":game,"post_id":str(postid),"size":[img.width,img.height],"results":results,"status":"ocr_unverified","published":False},ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"game":game,"error":str(exc),"published":False},ensure_ascii=False))
