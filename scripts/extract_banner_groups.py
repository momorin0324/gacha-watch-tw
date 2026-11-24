#!/usr/bin/env python3
"""第十五輪：按公告段落提取完整 UP 名單與各自時間；只供審核。"""
import argparse,html,json,re
from html.parser import HTMLParser
from pathlib import Path
class Cleaner(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,s):self.parts.append(s)
 def handle_starttag(self,t,a):
  if t in ("p","div","br","li"):self.parts.append("\n")
def clean(s):
 p=Cleaner();p.feed(str(s or ""));return html.unescape("".join(p.parts))
def category(title):
 if re.search(r"活動躍遷|祈願|調頻|獨家頻段|音擎頻段",title):return "疑似卡池公告"
 if re.search(r"前瞻|特別節目|直播預告",title):return "前瞻直播"
 if re.search(r"版本.*(更新|維護)|遊戲更新修復",title):return "版本更新"
 return "其他公告"
NAME=re.compile(r"(限定五星|四星)(角色|光錐|武器|音擎)?「([^」\n]{1,90})」")
QUOTED=re.compile(r"「([^」\n]{1,90})」")
TIME=re.compile(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2}[^\n。]{0,95}?(?:\d{1,2}:\d{2}|版本更新後)[^\n。]{0,100})")
def extract(text):
 output=[]
 for passage in re.split(r"[。\n]+",text):
  passage=passage.strip()
  if not passage or not re.search(r"躍遷時間為|祈願時間|調頻時間|活動祈願時間",passage):continue
  if not re.search(r"限定五星|四星|五星角色|五星武器|S級",passage):continue
  times=TIME.findall(passage)
  if not times:continue
  # 對每個星級／類型群組擷取連續引號，直到下一個群組起點。
  matches=list(NAME.finditer(passage))
  items=[]
  for i,m in enumerate(matches):
   boundary=matches[i+1].start() if i+1<len(matches) else len(passage)
   fragment=passage[m.end():boundary]
   names=[m.group(3)]
   # 只接收直接由頓號或逗號連接的連續名稱，避免抓到其他敘述中的引號。
   for extra in re.finditer(r"[、，,]\s*「([^」\\n]{1,90})」",fragment):
    names.append(extra.group(1))
   for name in names:
    items.append({"星級":"五星" if m.group(1)=="限定五星" else "四星","類型":m.group(2) or "待判斷","原文名稱":name,"名稱":re.sub(r"（[^（）]*）$","",name),"是否復刻":"是（公告段落明示）" if re.search("復刻",passage) else "待確認"})
  # 保留無法安全歸類的引號名稱供人工檢查，不自動指定星級。
  unknown=[name for name in QUOTED.findall(passage) if name not in [i["原文名稱"] for i in items]]
  for name in unknown:
   items.append({"星級":"待判斷","類型":"待判斷","原文名稱":name,"名稱":re.sub(r"（[^（）]*）$","",name),"是否復刻":"待確認"})
  output.append({"原文時間":times[-1],"候選UP名單":items,"復刻字樣":bool(re.search("復刻",passage)),"證據原文":passage[:1600],"驗證狀態":"待人工確認","允許發布":False})
 return output
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--input",default="official-evidence-diagnostic/官方文章證據.json");ap.add_argument("--output",default="banner-diagnostic/第十五輪多卡池與UP名單.json");a=ap.parse_args()
 raw=json.loads(Path(a.input).read_text(encoding="utf-8"));result={"模式":"候選資料，不發布","遊戲":[]}
 for g in raw.get("遊戲",[]):
  rows=[]
  for article in g.get("文章",[]):
   title=article.get("標題","");typ=category(title)
   rows.append({"文章ID":article.get("文章ID"),"網址":article.get("網址"),"標題":title,"分類":typ,"卡池段落":extract(clean(article.get("內文"))) if typ=="疑似卡池公告" else [],"官方身分":article.get("審核狀態","待確認"),"允許發布":False})
  result["遊戲"].append({"遊戲":g["遊戲"],"文章":rows})
  print(json.dumps({"遊戲":g["遊戲"],"文章":len(rows),"候選段落":sum(len(r["卡池段落"]) for r in rows)},ensure_ascii=False))
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
