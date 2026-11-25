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
 return bool(a and ((b and a<b) or v.get("end") is None) and
             v.get("verified") is True and isinstance(v.get("source"),str) and
             v["source"].startswith("https://"))

def advance(doc, now):
 """Use the successor's opening time as the handover and archive boundary."""
 history = {(h["game"], h["version"]): h for h in doc.get("history", [])}
 games = []
 for original in doc.get("games", []):
  game = dict(original)
  current = game.get("current_version")
  upcoming = game.get("next_version")
  if (valid_version(upcoming) and timestamp(upcoming["start"]) <= now and
      (not valid_version(current) or timestamp(current["start"]) < timestamp(upcoming["start"]))):
   if valid_version(current):
    key = (game["id"], current["version"])
    end = current.get("end") or upcoming.get("previous_end")
    if not timestamp(end) or not timestamp(current["start"]) < timestamp(end) <= timestamp(upcoming["start"]):
     end = upcoming["start"]
    previous = history.get(key, {})
    history[key] = {**previous, **current, "game": game["id"], "end": end,
                    "phases": current.get("phases") or previous.get("phases", [])}
   game["current_version"] = upcoming
   game["next_version"] = None
   end = timestamp(upcoming.get("end"))
   if end and end <= now:
    key = (game["id"], upcoming["version"])
    history.setdefault(key, {"game": game["id"], **upcoming})
    game["current_version"] = None
  games.append(game)
 changed = games != doc.get("games", [])
 if not changed:
  return doc, False
 return {**doc, "games": games, "history": list(history.values()),
         "updated_at": now.isoformat()}, True

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
