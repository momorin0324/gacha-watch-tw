#!/usr/bin/env python3
"""繁體中文指定文章診斷：僅擷取欄位與圖片順序，不發布資料。"""
import json, urllib.parse, urllib.request, re
ARTICLE_ID="47507255"
ENDPOINT="https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull"
query=urllib.parse.urlencode({"gids":"8","post_id":ARTICLE_ID,"read":1})
url=ENDPOINT+"?"+query
req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json","Referer":"https://www.hoyolab.com/","x-rpc-language":"zh-tw","Accept-Language":"zh-TW,zh;q=0.9"})
try:
    with urllib.request.urlopen(req,timeout=25) as r:
        if urllib.parse.urlsplit(r.geturl()).hostname!="bbs-api-os.hoyolab.com":raise ValueError("非預期重新導向")
        raw=r.read(2000001)
        if len(raw)>2000000:raise ValueError("資料過大")
        data=json.loads(raw)
    payload=data.get("data") or {}
    post=payload.get("post") or {}
    if "post" in post and isinstance(post["post"],dict):post=post["post"]
    body=post.get("content") or ""
    parsed=None
    if isinstance(body,str):
        try:parsed=json.loads(body)
        except ValueError:pass
    images=[]
    def scan(obj,path=""):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if isinstance(v,str) and (k in ("url","image_url","src","cover")) and urllib.parse.urlsplit(v).hostname=="upload-os-bbs.hoyolab.com":
                    images.append({"position":len(images)+1,"path":(path+"."+k)[:120],"host":"upload-os-bbs.hoyolab.com"})
                else:scan(v,path+"."+k)
        elif isinstance(obj,list):
            for i,v in enumerate(obj):scan(v,path+"["+str(i)+"]")
    scan(parsed if parsed is not None else payload)
    print(json.dumps({"文章編號":ARTICLE_ID,"介面回應碼":data.get("retcode"),"回應訊息":data.get("message"),"文章標題":post.get("subject"),"發文者欄位":list((payload.get("user") or {}).keys())[:20],"內容長度":len(body) if isinstance(body,str) else 0,"圖片數量":len(images),"圖片欄位順序":images[:40],"原始欄位":list(payload.keys()),"狀態":"僅供測試，未驗證，不發布"},ensure_ascii=False))
except Exception as e:
    print(json.dumps({"文章編號":ARTICLE_ID,"錯誤":str(e),"狀態":"測試失敗，不發布"},ensure_ascii=False))
