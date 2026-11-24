#!/usr/bin/env python3
"""絕區零繁體中文公告多圖 OCR 測試；只輸出診斷檔，不發布。"""
import io, json, re, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

POST_ID="47507255"
API="https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull"
IMAGE_HOST="upload-os-bbs.hoyolab.com"
OUT=Path("ocr-diagnostic")
OUT.mkdir(exist_ok=True)

def get(url, hosts, max_bytes):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0",
        "Referer":"https://www.hoyolab.com/",
        "Accept-Language":"zh-TW,zh;q=0.9",
        "x-rpc-language":"zh-tw"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        target=urllib.parse.urlsplit(resp.geturl())
        if target.scheme!="https" or target.hostname not in hosts:
            raise ValueError("不允許的來源或重新導向")
        data=resp.read(max_bytes+1)
        if len(data)>max_bytes:raise ValueError("檔案超過大小上限")
        return data

def extract_text(image):
    # 長圖分段，保留 100px 重疊區域以減少截斷
    width,height=image.size
    target_width=min(1800,max(width,1200))
    if width<target_width:
        ratio=target_width/width
        image=image.resize((target_width,round(height*ratio)))
    step=1500
    overlap=120
    parts=[]
    for top in range(0,image.height,step):
        tile=image.crop((0,max(0,top-overlap),image.width,min(image.height,top+step+overlap)))
        grey=ImageEnhance.Contrast(ImageOps.grayscale(tile)).enhance(1.35)
        txt=pytesseract.image_to_string(grey,lang="chi_tra+eng",config="--psm 11",timeout=45)
        parts.append({"區段":len(parts)+1,"起點":top,"辨識文字":txt[:12000]})
        if top+step>=image.height:break
    return parts

def main():
    query=urllib.parse.urlencode({"gids":8,"post_id":POST_ID,"read":1})
    doc=json.loads(get(API+"?"+query,{"bbs-api-os.hoyolab.com"},2000000))
    if doc.get("retcode")!=0:raise ValueError("文章 API 回應異常")
    payload=(doc.get("data") or {}).get("post") or {}
    post=payload.get("post",payload)
    imgs=payload.get("image_list") or post.get("image_list") or []
    print(json.dumps({"文章圖片數量":len(imgs),"文章欄位":list(payload.keys()),"內層欄位":list(post.keys())[:15]},ensure_ascii=False))
    if not imgs: raise ValueError("未找到文章圖片：停止測試，不視為成功")
    if not isinstance(imgs,list):raise ValueError("圖片欄位格式不符")
    result={"文章編號":POST_ID,"標題":post.get("subject"),"語言要求":"zh-tw",
            "實際語言":"尚須人工核實","圖片數量":len(imgs),
            "圖片結果":[],"資料狀態":"待驗證","發布":False}
    for i,item in enumerate(imgs[:20],1):
        row={"順序":i,"狀態":"待處理"}
        try:
            url=item.get("url","")
            parsed=urllib.parse.urlsplit(url)
            if parsed.scheme!="https" or parsed.hostname!=IMAGE_HOST:
                raise ValueError("非允許圖片網域")
            raw=get(url,{IMAGE_HOST},8000000)
            im=Image.open(io.BytesIO(raw))
            if im.width*im.height>20000000:raise ValueError("圖片像素過大")
            im=ImageOps.exif_transpose(im).convert("RGB")
            row.update({"尺寸":[im.width,im.height],"來源網址":url,
                        "區段":extract_text(im),"狀態":"已辨識，尚未驗證"})
        except Exception as exc:
            row.update({"狀態":"失敗","錯誤":str(exc)})
        result["圖片結果"].append(row)
        print(json.dumps({"圖片順序":i,"狀態":row["狀態"],"尺寸":row.get("尺寸"),
                          "辨識字數":sum(len(x["辨識文字"]) for x in row.get("區段",[])),
                          "文字預覽":" ".join(x["辨識文字"] for x in row.get("區段",[]))[:240]},ensure_ascii=False))
    (OUT/"zzz-47507255-ocr.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("診斷資料已產生，未修改正式卡池資料。")
if __name__=="__main__":main()
