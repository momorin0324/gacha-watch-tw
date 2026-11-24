#!/usr/bin/env python3
"""第十九輪：跨公告搜尋維護、時區及官方帳號證據；僅產出待審報告。"""
import argparse,datetime,html,json,re
from html.parser import HTMLParser
from pathlib import Path
class Reader(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,t):self.parts.append(t)
 def handle_starttag(self,t,a):
  if t in ("p","div","br","li"):self.parts.append("\n")
def plain(s):
 p=Reader();p.feed(str(s or ""));return html.unescape("".join(p.parts))
def version(title):
 m=re.search(r"(\d+\.\d+)\s*版本",title or "")
 return m.group(1) if m else None
def evidence(text):
 lines=[x.strip() for x in re.split(r"[\n。]+",plain(text)) if x.strip()]
 tz=[x[:450] for x in lines if re.search(r"(?:UTC|GMT)\s*[+-]\s*\d{1,2}|伺服器時間|服务器时间",x,re.I) and not re.search(r"試用活動|試用角色|體驗關卡",x)][:15]
 maint=[x[:450] for x in lines if re.search(r"維護(?:開始|結束|時間|預計)|維護完成|版本更新後|更新維護|維護期間",x) and not re.search(r"試用活動|試用角色|體驗關卡",x)][:15]
 return tz,maint
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--articles",default="official-evidence-diagnostic/官方文章證據.json")
 p.add_argument("--history",default="history-diagnostic/第十六輪歷史卡池待審資料.json")
 p.add_argument("--output",default="verification-diagnostic/第十九輪跨公告證據.json")
 a=p.parse_args()
 articles=json.loads(Path(a.articles).read_text(encoding="utf-8"))
 history=json.loads(Path(a.history).read_text(encoding="utf-8"))
 bygame={g["遊戲"]:g.get("文章",[]) for g in articles.get("遊戲",[])}
 output={"資料格式版本":1,"建立時間UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"模式":"只讀查核，不核准發布","卡池":[], "帳號認證候選":[]}
 for game,posts in bygame.items():
  users={}
  for post in posts:
   uid=str(post.get("發文者UID") or "")
   if not uid:continue
   entry=users.setdefault(uid,{"遊戲":game,"UID":uid,"名稱":post.get("發文者"),"原始認證":post.get("官方欄位"),"證據網址":[],"驗證狀態":"待人工確認","可列白名單":False})
   entry["證據網址"].append(post.get("網址"))
  output["帳號認證候選"].extend(users.values())
 for record in history.get("卡池紀錄",[]):
  game=record.get("遊戲");target_version=version(record.get("文章標題",""))
  posts=bygame.get(game,[])
  matches=[]
  for post in posts:
   title=post.get("標題","")
   if target_version and version(title)!=target_version:continue
   tz,maint=evidence(post.get("內文",""))
   if not tz and not maint:continue
   matches.append({"文章ID":post.get("文章ID"),"文章網址":post.get("網址"),"標題":title,"官方帳號UID":post.get("發文者UID"),"時區原文":tz,"維護原文":maint,"是否同版本":bool(target_version and version(title)==target_version)})
  output["卡池"].append({"卡池識別碼":record.get("識別碼"),"遊戲":game,"目標版本":target_version,"卡池公告":record.get("公告來源"),"交叉比對文章":matches,"來源時區":"待官方核實","維護完成精確時刻":None,"結束倒數可用":False,"開始倒數可用":False,"允許發布":False})
 output["統計"]={"卡池數":len(output["卡池"]),"有跨公告證據":sum(bool(x["交叉比對文章"]) for x in output["卡池"]),"帳號候選":len(output["帳號認證候選"]),"已核准":0}
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(output["統計"],ensure_ascii=False))
 if not output["卡池"]:raise RuntimeError("沒有卡池候選")
if __name__=="__main__":main()
