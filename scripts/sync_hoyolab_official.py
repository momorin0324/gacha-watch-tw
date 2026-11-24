#!/usr/bin/env python3
"""HoYoLAB 官方白名單快訊同步。欄位級合併，不臆測卡池日期/時區。"""
import datetime,json,os,re,tempfile
from pathlib import Path
from urllib.parse import urlsplit
from collect_hoyolab_evidence import GAMES,fetch,details
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/official_accounts.json"
OUTPUT=ROOT/"data/updates.json"
LOG=ROOT/"data/sync_status.json"
TZ=datetime.timezone(datetime.timedelta(hours=8))
GAME_IDS={"原神":"genshin","崩壞：星穹鐵道":"hsr","絕區零":"zzz"}
VERSION=re.compile(r"(?<!\d)(\d+\.\d+)\s*版本")
CATEGORIES={"版本":"version","維護":"maintenance","躍遷":"banner","祈願":"banner","調頻":"banner","前瞻":"preview","直播":"preview"}
def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("w",dir=path.parent,encoding="utf-8",delete=False) as f:
  json.dump(data,f,ensure_ascii=False,indent=2);f.write("\n");tmp=f.name
 os.replace(tmp,path)
def eligible(post,rule):
 uid=str(post.get("發文者UID",""))
 cert=(post.get("官方欄位") or {}).get("user_certification") or {}
 if not isinstance(cert,dict):return False
 # 僅接受指定 UID + 預先核對的認證描述；認證不符時絕不發佈。
 desc=str(cert.get("desc") or "")
 return uid==str(rule["uid"]) and desc==rule["certification_desc"]
def category(title):
 return next((v for k,v in CATEGORIES.items() if k in title),"news")
def extract(post):
 title=post.get("標題") or ""
 match=VERSION.search(title)
 # 從標題提取的版本資訊屬於官方公告標題證據，不視為「已上線當前版本」
 return {"id":str(post["文章ID"]),"title":title[:240],"url":post["網址"],"published_at":post.get("發表時間"),"category":category(title),"version":match.group(1) if match else None}
def valid_notice(n):
 u=urlsplit(n.get("url",""))
 return u.scheme=="https" and u.hostname=="www.hoyolab.com" and re.fullmatch(r"/article/\d+",u.path or "") and bool(n.get("title"))
def merge(old,notices,gameid,now):
 game=next((g for g in old.get("games",[]) if g.get("id")==gameid),{"id":gameid})
 previous={n["id"]:n for n in game.get("official_announcements",[]) if isinstance(n,dict) and n.get("id")}
 for n in notices:
  if valid_notice(n):previous[n["id"]]=n
 # 保存最近 80 篇，避免每次抓取只剩最新十篇
 def sortkey(n):
  try:return int(n["id"])
  except (ValueError,TypeError):return 0
 merged=sorted(previous.values(),key=sortkey,reverse=True)[:80]
 if merged:
  game["official_announcements"]=merged
  game["official_source_verified"]=True
  game["announcements_checked_at"]=now
  # 版本公告候選可顯示；不覆蓋現有 current 或尚未驗證的卡池
  versions=[n for n in merged if n["category"]=="version" and n.get("version")]
  if versions:game["latest_official_version_announcement"]={"version":versions[0]["version"],"source":versions[0]["url"],"title":versions[0]["title"]}
 return game
def run():
 rules=json.loads(CONFIG.read_text(encoding="utf-8"))["games"]
 old=json.loads(OUTPUT.read_text(encoding="utf-8"))
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 games={g["id"]:g for g in old.get("games",[]) if isinstance(g,dict) and g.get("id")}
 status={"checked_at":now,"games":{}}
 errors=[]
 for name,gid in GAMES.items():
  gameid=GAME_IDS[name];rule=rules[gameid]
  found=[];rejected=0;failures=[]
  try:
   data=fetch("getNewsList",{"gids":gid,"type":1,"page_size":20})
   posts=data.get("list") or data.get("posts") or []
   if isinstance(posts,dict):posts=posts.get("list") or []
   if not isinstance(posts,list) or not posts:raise ValueError("公告清單空白或格式變更")
   for item in posts[:20]:
    p=item.get("post") or item
    pid=p.get("post_id")
    if not pid:continue
    try:
     article=details(pid,gid)
     if eligible(article,rule):found.append(extract(article))
     else:rejected+=1
    except Exception as e:failures.append({"article_id":str(pid),"error":str(e)[:180]})
   if found:
    games[gameid]=merge(old,found,gameid,now)
   else:
    errors.append(gameid+": no whitelisted official articles")
  except Exception as e:errors.append(gameid+": "+str(e))
  status["games"][gameid]={"accepted":len(found),"rejected":rejected,"article_errors":failures[:20],"latest_url":found[0]["url"] if found else None}
  if failures:errors.append(gameid+": "+str(len(failures))+" article errors")
 result=dict(old)
 result["games"]=list(games.values())
 # 不更動 history、phases 或 current；缺乏可靠時區與角色欄位時不得編造
 if result!=old:
  result["updated_at"]=now
  save(OUTPUT,result)
 status["errors"]=errors
 save(LOG,status)
 print(json.dumps(status,ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=="__main__":run()
