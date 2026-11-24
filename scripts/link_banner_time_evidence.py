#!/usr/bin/env python3
"""第二十輪：依卡池來源、版本及公告類型建立保守的時區證據關聯，不發布。"""
import argparse,datetime,json,re
from pathlib import Path
def version(s):
 m=re.search(r"(?<!\d)(\d+\.\d+)\s*版本",s or "")
 return m.group(1) if m else None
def classify(title):
 if "更新維護預告" in title:return "維護預告"
 if "版本更新說明" in title:return "版本更新說明"
 if "活動躍遷" in title:return "卡池公告"
 return "其他公告"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--crosscheck",default="verification-diagnostic/第十九輪跨公告證據.json")
 p.add_argument("--history",default="history-diagnostic/第十六輪歷史卡池待審資料.json")
 p.add_argument("--output",default="verification-diagnostic/第二十輪時區關聯審核.json")
 a=p.parse_args()
 cross=json.loads(Path(a.crosscheck).read_text(encoding="utf-8"))
 history=json.loads(Path(a.history).read_text(encoding="utf-8"))
 cross_by_id={r["卡池識別碼"]:r for r in cross.get("卡池",[])}
 result={"資料格式版本":1,"模式":"只讀證據關聯，不發布","建立時間UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"紀錄":[]}
 for record in history.get("卡池紀錄",[]):
  match=cross_by_id.get(record["識別碼"],{})
  v=version(record.get("文章標題"))
  sources=[]; explicit=[];context=[]
  for post in match.get("交叉比對文章",[]):
   if not v or version(post.get("標題"))!=v:continue
   typ=classify(post.get("標題",""))
   lines=post.get("時區原文",[])
   utc=[line for line in lines if re.search(r"\(\s*UTC\s*\+\s*8\s*\)",line,re.I)]
   sources.append({"類型":typ,"標題":post.get("標題"),"網址":post.get("文章網址"),"同版本":True,"UTC+8明示句":utc[:6],"維護相關句":post.get("維護原文",[])[:6]})
   if utc and typ=="卡池公告":explicit.append(post.get("文章網址"))
   elif utc and typ in ("版本更新說明","維護預告"):context.append(post.get("文章網址"))
  raw=record.get("卡池時間",{})
  end=raw.get("結束時間",{}).get("當地時刻")
  event=raw.get("開始時間",{}).get("事件條件")
  # 同版本 UTC+8 只算間接證據；不能直接宣稱卡池「伺服器時間」等同 UTC+8
  level="卡池公告直接明示UTC+8" if explicit else ("同版本其他公告明示UTC+8，卡池時區仍待核實" if context else "缺乏UTC+8證據")
  result["紀錄"].append({"識別碼":record["識別碼"],"遊戲":record.get("遊戲"),"版本":v,"卡池公告":record.get("公告來源"),"卡池結束當地時刻":end,"卡池開始條件":event,"時區證據等級":level,"同版本來源":sources,"卡池公告直接UTC+8來源":explicit,"其他公告UTC+8來源":context,"卡池伺服器時間已證明等同UTC+8":bool(explicit),"維護完成實際時間":None,"預估維護時間不得當作實際完成":True,"結束倒數可用":bool(end and explicit),"開始倒數可用":False,"允許發布":False,"待確認":["官方帳號白名單人工核准","卡池伺服器時間與UTC+8的明確對應" if not explicit else "核對卡池時間","版本維護實際完成時間"]})
 result["統計"]={"卡池數":len(result["紀錄"]),"同版本有UTC+8參考":sum(bool(x["其他公告UTC+8來源"]) for x in result["紀錄"]),"卡池直接明示UTC+8":sum(bool(x["卡池公告直接UTC+8來源"]) for x in result["紀錄"]),"結束倒數可用":sum(x["結束倒數可用"] for x in result["紀錄"]),"已發布":0}
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(result["統計"],ensure_ascii=False))
 if not result["紀錄"]:raise RuntimeError("沒有卡池可審核")
if __name__=="__main__":main()
