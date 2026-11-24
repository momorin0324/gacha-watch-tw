#!/usr/bin/env python3
"""第九輪：絕區零繁體中文長圖 PaddleOCR 診斷（不發布）。"""
import io,json,urllib.parse,urllib.request
from pathlib import Path
from PIL import Image,ImageOps
from paddleocr import PaddleOCR

POST_ID="47507255"
OUT=Path("paddleocr-diagnostic")
OUT.mkdir(exist_ok=True)
def download(url,host,limit):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.hoyolab.com/","x-rpc-language":"zh-tw","Accept-Language":"zh-TW,zh;q=0.9"})
    with urllib.request.urlopen(req,timeout=35) as r:
        u=urllib.parse.urlsplit(r.geturl())
        if u.scheme!="https" or u.hostname!=host:raise ValueError("來源網域不符")
        raw=r.read(limit+1)
        if len(raw)>limit:raise ValueError("檔案超過限制")
        return raw

def main():
    api="https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull?"+urllib.parse.urlencode({"gids":8,"post_id":POST_ID,"read":1})
    data=json.loads(download(api,"bbs-api-os.hoyolab.com",2000000))
    if data.get("retcode")!=0:raise ValueError("文章讀取失敗")
    root=(data.get("data") or {}).get("post") or {}
    imgs=root.get("image_list") or []
    if not imgs:raise ValueError("文章圖片清單為空")
    # 完整長圖依序分段掃描；仍僅為待驗證診斷，不自動發布。
    ocr=PaddleOCR(use_angle_cls=False,lang="chinese_cht",use_gpu=False,show_log=False)
    report={"文章":POST_ID,"圖片數量":len(imgs),"狀態":"僅測試，未驗證","發布":False,"圖片":[]}
    for i,item in enumerate(imgs[:3],1):
        record={"圖片順序":i,"區段":[]}
        try:
            raw=download(item["url"],"upload-os-bbs.hoyolab.com",9000000)
            im=Image.open(io.BytesIO(raw))
            if im.width*im.height>22000000:raise ValueError("圖片像素過大")
            im=ImageOps.exif_transpose(im).convert("RGB")
            record["尺寸"]=[im.width,im.height]
            # 全圖連續掃描，區段間重疊 100px，避免文字在邊界被截斷。
            starts=list(range(0,im.height,1100))
            for start in starts:
                tile=im.crop((0,start,im.width,min(im.height,start+1200)))
                path=OUT/("image_%d_y_%d.png"%(i,start))
                tile.save(path)
                lines=ocr.ocr(str(path),cls=False)
                rows=[]
                for block in lines or []:
                    for line in block or []:
                        if isinstance(line,(list,tuple)) and len(line)>1:
                            txt,score=line[1]
                            rows.append({"文字":str(txt),"信心分數":round(float(score),3)})
                record["區段"].append({"起始高度":start,"辨識結果":rows})
                print(json.dumps({"圖片":i,"起始高度":start,"辨識行數":len(rows),"文字預覽":" ".join(x["文字"] for x in rows)[:300]},ensure_ascii=False))
                path.unlink(missing_ok=True)
            record["狀態"]="辨識完成，待驗證"
        except Exception as exc:
            record["狀態"]="辨識失敗"
            record["錯誤"]=str(exc)
            print(json.dumps({"圖片":i,"錯誤":str(exc)},ensure_ascii=False))
        report["圖片"].append(record)
    import re
    # 候選資訊不等於驗證通過；原始辨識文字與圖片座標必須保留。
    candidates=[]
    patterns={
        "日期時間":r"(?:20\\d{2}[/.-])?\\d{1,2}[/月.-]\\d{1,2}(?:日)?(?:\\s*\\d{1,2}[:：]\\d{2})?",
        "版本號":r"(?:版本|Ver\\.?|V)\\s*\\d+\\.\\d+",
        "卡池關鍵字":r"(?:調頻|獨家頻段|UP|限定|代理人|音擎|復刻)"
    }
    for rec in report["圖片"]:
        for seg in rec.get("區段",[]):
            for line in seg.get("辨識結果",[]):
                for kind,pattern in patterns.items():
                    if re.search(pattern,line["文字"],re.I):
                        candidates.append({"類別":kind,"圖片順序":rec["圖片順序"],"起始高度":seg["起始高度"],"文字":line["文字"],"信心分數":line["信心分數"],"驗證狀態":"待人工確認"})
    report["候選資訊"]=candidates
    report["正式發布條件"]="必須另行比對官方證據，OCR 結果不可直接發布"
    (OUT/"絕區零_47507255_繁體中文辨識.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if not any(r.get("狀態")=="辨識完成，待驗證" for r in report["圖片"]):
        raise RuntimeError("沒有任何圖片辨識成功")
    print("已產生繁體中文診斷報告；沒有更新網站。")
if __name__=="__main__":main()
