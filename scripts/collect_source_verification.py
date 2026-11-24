#!/usr/bin/env python3
"""第十八輪：從原始 HoYoLAB 證據中產生帳號與時區查核清單；不自動認證或發布。"""
import argparse,collections,datetime,json,re,html
from html.parser import HTMLParser
class TextOnly(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,t):self.parts.append(t)
 def handle_starttag(self,t,a):
  if t in ('p','div','br','h3','h4','li'):self.parts.append('\n')
def plain(s):
 parser=TextOnly();parser.feed(str(s or ''));return html.unescape(''.join(parser.parts))
from pathlib import Path
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--articles",default="official-evidence-diagnostic/官方文章證據.json")
 p.add_argument("--history",default="history-diagnostic/第十六輪歷史卡池待審資料.json")
 p.add_argument("--output",default="verification-diagnostic/第十八輪官方身分與時區證據.json")
 a=p.parse_args()
 articles=json.loads(Path(a.articles).read_text(encoding="utf-8"))
 history=json.loads(Path(a.history).read_text(encoding="utf-8"))
 accounts={}
 byid={}
 for game in articles.get("遊戲",[]):
  for article in game.get("文章",[]):
   uid=str(article.get("發文者UID") or "")
   name=article.get("發文者")
   k=(game["遊戲"],uid)
   row=accounts.setdefault(k,{"遊戲":game["遊戲"],"發文者UID":uid,"發文者名稱":name,"文章數":0,"來源文章":[],"原始認證欄位":article.get("官方欄位"),"驗證結果":"待人工核實","允許列入白名單":False})
   row["文章數"]+=1
   row["來源文章"].append(article.get("網址"))
   byid[(game["遊戲"],str(article.get("文章ID")))]=article
 rows=[]
 for x in history.get("卡池紀錄",[]):
  article=byid.get((x.get("遊戲"),str(x.get("文章ID"))))
  original=(article or {}).get("內文") or ""
  lines=re.split(r"[\n。]+",plain(original))
  # 時區僅擷取有明確 UTC/GMT 或伺服器時間的文字，不推論遊戲時區
  timezone_quotes=[line.strip()[:350] for line in lines if re.search(r"(?:UTC|GMT)\s*[+-]\s*\d{1,2}|伺服器時間|服务器时间",line,re.I) and not re.search(r"試用活動|試用角色|體驗關卡",line)][:12]
  start_quotes=[line.strip()[:350] for line in lines if re.search(r"維護.*(?:開始|結束)|版本更新後|維護完成|維護結束",line) and not re.search(r"試用活動|試用角色|體驗關卡",line)][:12]
  rows.append({"卡池識別碼":x.get("識別碼"),"遊戲":x.get("遊戲"),"文章來源":x.get("公告來源"),"官方文章原始資料是否在本次蒐集批次":bool(article),"帳號UID":(article or {}).get("發文者UID"),"認證原始欄位":(article or {}).get("官方欄位"),"時區證據片段":timezone_quotes,"更新時間證據片段":start_quotes,"已核實來源時區":None,"已核實開始時刻":None,"審核狀態":"待人工核實","允許發布":False})
 out={"資料格式版本":1,"模式":"證據收集，不發布","建立時間UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"帳號候選":list(accounts.values()),"卡池查核":rows,"統計":{"帳號候選":len(accounts),"卡池查核":len(rows),"文章批次中有原始來源":sum(r["官方文章原始資料是否在本次蒐集批次"] for r in rows),"核准發布":0}}
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(out["統計"],ensure_ascii=False))
 if not rows:raise RuntimeError("缺少歷史卡池候選")
if __name__=="__main__":main()
