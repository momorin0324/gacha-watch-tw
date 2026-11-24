#!/usr/bin/env python3
"""Promote verified upcoming versions to current and archive expired versions.

The source of truth is a version's explicit start/end timestamp, never an
announcement publication time or an inferred six-week cadence.
"""
import datetime
import json
import os
import pathlib
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data/updates.json"

def timestamp(value):
 if not isinstance(value,str) or not value.strip():return None
 try:
  t=datetime.datetime.fromisoformat(value.replace("Z","+00:00"))
  return t.astimezone(datetime.timezone.utc) if t.tzinfo else None
 except ValueError:return None

def valid_version(v):
 if not isinstance(v,dict) or not isinstance(v.get("version"),str) or not v["version"].strip():return False
 a,b=timestamp(v.get("start")),timestamp(v.get("end"))
 return bool(a and b and a<b and v.get("verified") is True and isinstance(v.get("source"),str) and v["source"].startswith("https://"))

def advance(doc,now):
 """Only move verified version records; preserve every other game field."""
 result=dict(doc)
 history=list(doc.get("history") or [])
 seen={(h.get("game"),h.get("version")) for h in history if isinstance(h,dict)}
 games=[]
 changed=False
 for original in doc.get("games",[]):
  g=dict(original)
  current=g.get("current_version")
  upcoming=g.get("next_version")
  if not valid_version(current) and not valid_version(upcoming):
   games.append(g);continue
  if valid_version(current) and timestamp(current["end"])<=now:
   key=(g["id"],current["version"])
   if key not in seen:
    history.append({"game":g["id"],**current});seen.add(key)
   g["current_version"]=None
   changed=True
  if valid_version(upcoming) and timestamp(upcoming["start"])<=now and (g.get("current_version") is None):
   # Do not promote a version that has already ended. Archive it instead.
   if timestamp(upcoming["end"])<=now:
    key=(g["id"],upcoming["version"])
    if key not in seen:history.append({"game":g["id"],**upcoming});seen.add(key)
   else:g["current_version"]=upcoming
   g["next_version"]=None
   changed=True
  games.append(g)
 if changed:
  result["games"]=games
  result["history"]=history
  result["updated_at"]=now.isoformat()
 return result,changed

def run():
 if not DATA.exists():return
 old=json.loads(DATA.read_text(encoding="utf-8"))
 new,changed=advance(old,datetime.datetime.now(datetime.timezone.utc))
 if changed:
  with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=DATA.parent,delete=False) as f:
   json.dump(new,f,ensure_ascii=False,indent=2);f.write("\n");tmp=f.name
  os.replace(tmp,DATA)
 print(json.dumps({"advanced":changed,"history_count":len(new.get("history",[]))}))

if __name__=="__main__":run()
