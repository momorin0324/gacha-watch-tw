#!/usr/bin/env python3
"""第十六輪：將第十五輪候選轉為可追溯的歷史卡池待審資料；絕不發布。"""
import argparse,datetime,json,re,hashlib
from pathlib import Path
DATE=re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})")
def time_fields(raw):
    parts=re.split(r"\s+[-–—~～]\s+",raw,maxsplit=1)
    start,end=(parts+[None])[:2]
    def parse(value):
        if not value:return None
        m=DATE.search(value)
        if not m:return None
        try:return datetime.datetime(*map(int,m.groups())).strftime("%Y-%m-%dT%H:%M:00")
        except ValueError:return None
    start_iso=parse(start);end_iso=parse(end)
    start_date_match=re.search(r"(\\d{4})[/-](\\d{1,2})[/-](\\d{1,2})",start or "")
    start_date_hint=None
    if start_date_match:
        try:
            start_date_hint=datetime.date(*map(int,start_date_match.groups())).isoformat()
        except ValueError:
            pass
    start_event=bool(start and re.search(r"版本更新後|維護後",start))
    return {"公告時間原文":raw,"開始時間":{"當地時刻":start_iso if not start_event else None,"日期提示":start_iso[:10] if start_iso else start_date_hint,"事件條件":"版本更新後" if start_event else None,"精確時間已確認":bool(start_iso and not start_event)},"結束時間":{"當地時刻":end_iso,"精確時間已確認":bool(end_iso)},"來源時區":"待確認","台灣時間UTC+8":None,"可用於倒數":False}
def normalize(doc):
    result={"資料格式版本":1,"來源":"第十五輪官方文章候選","模式":"待人工審核，不發布","產生時間UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"卡池紀錄":[],"統計":{}}
    for game in doc.get("遊戲",[]):
        for article in game.get("文章",[]):
            for index,block in enumerate(article.get("卡池段落",[]),1):
                url=article.get("網址")
                if not url or not re.fullmatch(r"https://www\.hoyolab\.com/article/\d+",url):continue
                items=block.get("候選UP名單",[])
                chars=[{"名稱":x.get("名稱"),"原文名稱":x.get("原文名稱"),"星級":x.get("星級"),"復刻狀態":x.get("是否復刻","待確認")} for x in items if x.get("類型")=="角色"]
                equipment=[{"名稱":x.get("名稱"),"原文名稱":x.get("原文名稱"),"星級":x.get("星級"),"類型":x.get("類型"),"復刻狀態":x.get("是否復刻","待確認")} for x in items if x.get("類型") in ("光錐","武器","音擎")]
                unknown=[x for x in items if x.get("類型") not in ("角色","光錐","武器","音擎")]
                key=hashlib.sha256((game["遊戲"]+"|"+str(article.get("文章ID"))+"|"+str(index)+"|"+block.get("證據原文","")).encode()).hexdigest()[:16]
                result["卡池紀錄"].append({"識別碼":key,"遊戲":game["遊戲"],"文章ID":article.get("文章ID"),"文章標題":article.get("標題"),"公告來源":url,"公告內分組序號":index,"卡池時間":time_fields(block.get("原文時間","")),"UP角色":chars,"UP裝備":equipment,"未分類候選":unknown,"復刻證據":{"段落出現復刻字樣":bool(block.get("復刻字樣")),"逐項復刻狀態需再核實":True},"原始證據":block.get("證據原文"),"官方身分":article.get("官方身分","待確認"),"審核狀態":"待人工確認","允許發布":False})
    result["統計"]={"卡池分組":len(result["卡池紀錄"]),"角色候選":sum(len(x["UP角色"]) for x in result["卡池紀錄"]),"裝備候選":sum(len(x["UP裝備"]) for x in result["卡池紀錄"]),"可發布":0}
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--input",default="banner-diagnostic/第十五輪多卡池與UP名單.json");p.add_argument("--output",default="history-diagnostic/第十六輪歷史卡池待審資料.json");a=p.parse_args()
    data=normalize(json.loads(Path(a.input).read_text(encoding="utf-8")))
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(data["統計"],ensure_ascii=False))
    if not data["卡池紀錄"]:raise RuntimeError("未取得任何卡池分組，請檢查第十五輪輸入")
if __name__=="__main__":main()
