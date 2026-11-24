#!/usr/bin/env python3
"""第十七輪：歷史卡池證據審核與時區阻擋報告，不改動網站。"""
import argparse,json,re,datetime
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("--input",default="history-diagnostic/第十六輪歷史卡池待審資料.json");p.add_argument("--output",default="history-diagnostic/第十七輪時區與證據審核.json");a=p.parse_args()
 data=json.loads(Path(a.input).read_text(encoding="utf-8"));out={"資料格式版本":1,"審核模式":"只讀、不發布","建立時間UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"紀錄":[]}
 for x in data.get("卡池紀錄",[]):
  t=x.get("卡池時間") or {};start=t.get("開始時間") or {};end=t.get("結束時間") or {}
  reasons=[]
  if not re.fullmatch(r"https://www\.hoyolab\.com/article/\d+",str(x.get("公告來源",""))):reasons.append("來源網址格式未驗證")
  if x.get("官方身分")!="已驗證":reasons.append("官方發文者身分尚未核准")
  if t.get("來源時區")=="待確認" or not t.get("來源時區"):reasons.append("伺服器時區尚未核實，禁止 UTC+8 換算")
  if not start.get("精確時間已確認"):reasons.append("開始時間僅有版本更新條件，無精確時刻")
  if not end.get("精確時間已確認"):reasons.append("結束時間不完整")
  if x.get("未分類候選"):reasons.append("有未分類候選")
  if not x.get("原始證據"):reasons.append("缺少原始證據")
  out["紀錄"].append({"識別碼":x.get("識別碼"),"遊戲":x.get("遊戲"),"文章來源":x.get("公告來源"),"開始日期提示":start.get("日期提示"),"開始條件":start.get("事件條件"),"結束時間原始":end.get("當地時刻"),"時區":t.get("來源時區"),"阻擋原因":reasons,"審核狀態":"待確認","可發布":False,"可用於倒數":False})
 out["統計"]={"總紀錄":len(out["紀錄"]),"阻擋發布":len(out["紀錄"]),"已核准":0}
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(out["統計"],ensure_ascii=False))
 if not out["紀錄"]:raise RuntimeError("沒有卡池紀錄")
if __name__=="__main__":main()
