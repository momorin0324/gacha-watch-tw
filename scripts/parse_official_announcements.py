#!/usr/bin/env python3
"""官方公告保守解析：保留原文證據，未證實的時間不轉成倒數。"""
import re,html,datetime
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
DATE=re.compile(r"(20\\d{2})[年/.-](\\d{1,2})[月/.-](\\d{1,2})日?\\s*(?:[（(]?\\s*(?:UTC|GMT)\\s*([+-]\\d{1,2})(?::?00)?\\s*[）)]?\\s*)?(\\d{1,2}):(\\d{2})",re.I)
def verified_times(body):
 """Only absolute timestamps with explicit UTC/GMT offsets in the same date expression."""
 hits=[]
 for m in DATE.finditer(body):
  if m.group(4) is None:continue
  try:
   y,mo,d,off,h,mi=map(int,m.groups())
   dt=datetime.datetime(y,mo,d,h,mi,tzinfo=datetime.timezone(datetime.timedelta(hours=off)))
   hits.append({"iso":dt.isoformat(),"source":m.group(0)[:100]})
  except (ValueError,TypeError):continue
 return hits
def featured_candidates(lines):
 """Capture explicitly labelled five-star names; keep candidates separate from verified banners."""
 result=[]
 pattern=re.compile(r"(?:5星|五星|★5|5★)\\s*(?:角色|光錐|武器|代理人)?\\s*[：:]\\s*([^。；;\\n]{1,90})")
 for line in lines:
  for m in pattern.finditer(line):
   val=m.group(1).strip()
   if val and val not in result:result.append(val[:90])
 return result[:12]
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
  times=verified_times(body)
  output["banner_evidence"]={"source":post["網址"],"title":title,"time_evidence":time_lines[:12],"time_status":"已找到明確 UTC/GMT 時區" if times else "待確認伺服器時區，不啟用倒數","characters":[],"equipment":[],"verified_timestamps":times[:12],"five_star_candidates":featured_candidates(lines)}
  # A date inside an announcement can refer to unrelated events; never infer phase start/end from ordering alone.
 if re.search(r"(?:版本更新說明|版本更新維護預告)",title):
  evidence=[s[:240] for s in lines if re.search(r"(?:UTC|GMT)\s*[+\-]\s*\d{1,2}|維護時間|維護預計",s,re.I)]
  output["maintenance_evidence"]={"source":post["網址"],"lines":evidence[:8]}
 return output
