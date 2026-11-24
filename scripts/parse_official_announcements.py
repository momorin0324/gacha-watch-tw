#!/usr/bin/env python3
"""官方公告保守解析：保留原文證據，未證實的時間不轉成倒數。"""
import re,html
from html.parser import HTMLParser
class Text(HTMLParser):
 def __init__(self):super().__init__();self.out=[]
 def handle_data(self,s):self.out.append(s)
 def handle_starttag(self,tag,attrs):
  if tag in ("p","br","div","li","h2","h3"):self.out.append("\n")
def clean(raw):
 parser=Text()
 try:parser.feed(str(raw or ""))
 except ValueError:return ""
 return html.unescape("".join(parser.out))
def parse(post):
 title=str(post.get("標題") or "")
 body=clean(post.get("內文") or "")
 lines=[re.sub(r"\s+"," ",s).strip() for s in body.splitlines()]
 lines=[s for s in lines if s]
 output={}
 if any(s in title for s in ("前瞻","特別節目","直播")):
  output["preview"]={"source":post["網址"],"title":title,"status":"官方預告，時間待解析"}
 if any(s in title for s in ("躍遷","祈願","調頻")):
  time_lines=[s[:240] for s in lines if re.search(r"(?:伺服器時間|服务器时间|UTC|GMT|活動時間|祈願時間|躍遷時間|調頻時間)",s,re.I)]
  output["banner_evidence"]={"source":post["網址"],"title":title,"time_evidence":time_lines[:12],"time_status":"待確認伺服器時區，不啟用倒數","characters":[],"equipment":[]}
 if re.search(r"(?:版本更新說明|版本更新維護預告)",title):
  evidence=[s[:240] for s in lines if re.search(r"(?:UTC|GMT)\s*[+\-]\s*\d{1,2}|維護時間|維護預計",s,re.I)]
  output["maintenance_evidence"]={"source":post["網址"],"lines":evidence[:8]}
 return output
