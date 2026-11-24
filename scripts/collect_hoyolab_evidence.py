#!/usr/bin/env python3
"""第十二輪：蒐集 HoYoLAB 公開文章證據（不推定官方身分、不發布）。"""
import argparse,datetime,json,re,time,urllib.parse,urllib.request
from pathlib import Path

API="https://bbs-api-os.hoyolab.com/community/post/wapi/"
GAMES={"原神":2,"崩壞：星穹鐵道":6,"絕區零":8}
def fetch(endpoint,params):
    url=API+endpoint+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.hoyolab.com/","Accept-Language":"zh-TW,zh;q=0.9","x-rpc-language":"zh-tw"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(2500001)
    if len(raw)>2500000:raise ValueError("資料量超過限制")
    data=json.loads(raw)
    if data.get("retcode")!=0:raise ValueError("API 回傳錯誤："+str(data.get("message")))
    return data.get("data") or {}
def details(post_id,gid):
    root=fetch("getPostFull",{"post_id":post_id,"gids":gid,"read":1}).get("post") or {}
    post=root.get("post") or {}
    user=root.get("user") or {}
    status=post.get("post_status") or {}
    # 無法從欄位單獨確定官方認證；保留原始證據供後續查核
    content=post.get("content","")
    # 部分絕區零公告 content 只回傳語言代碼 zh-tw；不可當成文章內文。
    is_placeholder=isinstance(content,str) and content.strip().lower() in ("zh-tw","zh-cn","en-us","")
    alternative={}
    for key in ("structured_content","structured_content_rows","desc","introduce"):
        value=post.get(key)
        if value and not (isinstance(value,str) and value.strip().lower() in ("zh-tw","zh-cn","en-us")):
            alternative[key]=value
    return {"內文完整性":"待補抓" if is_placeholder else "已取得原始內文","替代內容欄位":alternative,"文章ID":str(post_id),"網址":"https://www.hoyolab.com/article/"+str(post_id),"標題":post.get("subject",""),"內文":("" if is_placeholder else str(content)[:100000]),"發文者":user.get("nickname"),"發文者UID":str(user.get("uid","")),"官方欄位":{"post_status_is_official":status.get("is_official"),"is_official_master":root.get("is_official_master"),"user_certification":user.get("certification")},"發表時間":post.get("created_at"),"圖片數量":len(root.get("image_list") or []),"圖片來源":[x.get("url") for x in (root.get("image_list") or []) if isinstance(x,dict)],"審核狀態":"官方身分待確認","可發布":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--limit",type=int,default=10)
    p.add_argument("--output",default="official-evidence-diagnostic/官方文章證據.json")
    a=p.parse_args()
    if not 1<=a.limit<=20:raise ValueError("limit 須為 1~20")
    out={"擷取時間UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"模式":"只蒐集證據，不修改網站","遊戲":[]}
    for game,gid in GAMES.items():
        record={"遊戲":game,"文章":[],"錯誤":[]}
        try:
            news=fetch("getNewsList",{"gids":gid,"type":1,"page_size":a.limit})
            # 不假定回傳形狀；保留明確結構，拒絕未知格式
            posts=news.get("list") or news.get("posts") or []
            if isinstance(posts,dict):posts=posts.get("list") or []
            for item in posts[:a.limit]:
                post=item.get("post") or item
                pid=post.get("post_id")
                if not pid:continue
                try:record["文章"].append(details(pid,gid))
                except Exception as e:record["錯誤"].append({"文章ID":str(pid),"原因":str(e)})
                time.sleep(.3)
            if not posts:record["錯誤"].append({"原因":"公告清單為空或格式未識別","資料欄位":list(news.keys())})
        except Exception as e:record["錯誤"].append({"原因":str(e)})
        out["遊戲"].append(record)
        print(json.dumps({"遊戲":game,"取得文章":len(record["文章"]),"錯誤":record["錯誤"][:2]},ensure_ascii=False))
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    if not any(g["文章"] for g in out["遊戲"]):raise RuntimeError("所有遊戲均未取得文章，請檢查報告")
if __name__=="__main__":main()
