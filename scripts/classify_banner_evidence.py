#!/usr/bin/env python3
"""第十四輪：官方文章分類與限定躍遷候選擷取。僅輸出待審報告，不發布。"""
import html,json,re,argparse
from html.parser import HTMLParser
from pathlib import Path

class Strip(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)
    def handle_starttag(self,tag,attrs):
        if tag in ("p","div","br","li"):self.parts.append("\n")
def plain(value):
    parser=Strip()
    parser.feed(str(value or ""))
    return html.unescape("".join(parser.parts)).replace("\xa0"," ")
def classify(title):
    if re.search(r"活動躍遷|角色活動祈願|武器活動祈願|調頻.*(角色|音擎)|獨家頻段",title):return "限定卡池公告"
    if re.search(r"前瞻|特別節目|直播預告",title):return "前瞻直播"
    if re.search(r"版本.*(更新說明|更新公告|維護預告)|遊戲更新修復",title):return "版本更新"
    return "其他活動或公告"
# 僅抽取明確描述限定五星與時間的導言，不從任意活動日期推定卡池日期。
LEAD=re.compile(r"限定五星(角色|光錐)「([^」]+)」[^。]{0,350}?(?:躍遷時間為)(\d{4}/\d{1,2}/\d{1,2}[^。]{0,110}?)。")
ITEM=re.compile(r"限定五星(角色|光錐)「([^」]+)」")
DATE=re.compile(r"\d{4}/\d{1,2}/\d{1,2}[^\n。]{0,90}")
def candidates(text):
    out=[]
    for m in LEAD.finditer(text):
        passage=m.group(0)
        items=[{"類型":kind,"原文名稱":name,"名稱":re.sub(r"（[^（）]*）$","",name)} for kind,name in ITEM.findall(passage)]
        times=DATE.findall(passage)
        out.append({"候選":items,"時間原文":times[-1] if times else None,"證據原文":passage,"驗證狀態":"待人工確認","允許發布":False})
    return out
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="official-evidence-diagnostic/官方文章證據.json")
    ap.add_argument("--output",default="banner-diagnostic/第十四輪分類與卡池候選.json")
    args=ap.parse_args()
    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    result={"模式":"只供審核，不發布","遊戲":[]}
    for game in data.get("遊戲",[]):
        record={"遊戲":game["遊戲"],"文章":[]}
        for a in game.get("文章",[]):
            title=a.get("標題","")
            category=classify(title)
            text=plain(a.get("內文",""))
            row={"文章ID":a.get("文章ID"),"文章網址":a.get("網址"),"標題":title,"分類":category,"文字長度":len(text),"官方身分狀態":a.get("審核狀態","待確認"),"卡池候選":candidates(text) if category=="限定卡池公告" else [],"允許發布":False}
            record["文章"].append(row)
        result["遊戲"].append(record)
        print(json.dumps({"遊戲":game["遊戲"],"文章":len(record["文章"]),"限定卡池文章":sum(x["分類"]=="限定卡池公告" for x in record["文章"]),"候選段落":sum(len(x["卡池候選"]) for x in record["文章"])},ensure_ascii=False))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
