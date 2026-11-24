#!/usr/bin/env python3
"""第十一輪：官方歷史證據交叉驗證。僅產生待確認報告，不發布。"""
import argparse,json,re,unicodedata
from pathlib import Path

def normalize(value):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",str(value))).casefold()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ocr",default="paddleocr-diagnostic/絕區零_47507255_繁體中文辨識.json")
    parser.add_argument("--dictionary",default="data/official-name-evidence.json")
    parser.add_argument("--output",default="verification-diagnostic/待確認候選資料.json")
    args=parser.parse_args()
    report=json.loads(Path(args.ocr).read_text(encoding="utf-8"))
    dictionary=json.loads(Path(args.dictionary).read_text(encoding="utf-8"))
    candidates=report.get("候選資訊",[])
    results=[]
    for item in candidates:
        raw=item.get("文字","")
        matches=[]
        for entry in dictionary.get("entries",[]):
            aliases=[entry["canonical_name"]]+entry.get("aliases",[])
            if any(normalize(alias) in normalize(raw) for alias in aliases if alias):
                matches.append({"標準名稱":entry["canonical_name"],"原始作品":entry.get("origin_game"),"登場遊戲":entry.get("appearance_games",[]),"證據":entry.get("sources",[]),"分類":entry.get("type")})
        results.append({"OCR原文":raw,"來源圖片":item.get("圖片順序"),"圖片起始高度":item.get("起始高度"),"候選類型":item.get("類別"),"名稱候選":matches,"驗證狀態":"待確認","允許發布":False})
    out={"文章":report.get("文章"),"模式":"僅診斷，不發布","規則":"名稱比對不是卡池證明；卡池起訖時間須有明確官方證據與時區","候選數":len(results),"結果":results}
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"候選數":len(results),"有名稱對照":sum(bool(x["名稱候選"]) for x in results),"發布數":0,"報告":str(target)},ensure_ascii=False))
if __name__=="__main__":main()
