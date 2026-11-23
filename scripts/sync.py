#!/usr/bin/env python3
"""Strict ingestion: only structured, trusted JSON feeds. No speculative parsing of announcement prose."""
import json,os,datetime,urllib.request,urllib.parse,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/sources.json'; OUTPUT=ROOT/'data/updates.json'
GAMES={'genshin','hsr','zzz','wuwa','endfield','nter','azurpromilia','silverpalace','bd2','gfl2','nikke'}
# Actual site identifiers are read from the site snapshot; aliases below are configurable.
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def valid_phase(p):
 if not isinstance(p,dict):return False
 for k in ('characters','start','end','source'):
  if not isinstance(p.get(k),str) or not p[k].strip():return False
 try:
  a=datetime.datetime.fromisoformat(p['start'].replace('Z','+00:00'))
  b=datetime.datetime.fromisoformat(p['end'].replace('Z','+00:00'))
  return a.tzinfo is not None and b.tzinfo is not None and a<b and p['source'].startswith('https://')
 except ValueError:return False

def fetch(url,domain):
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or u.hostname!=domain:raise ValueError('source domain mismatch')
 req=urllib.request.Request(url,headers={'User-Agent':'GachaWatchTW/132 (+verified-json-sync)'})
 with urllib.request.urlopen(req,timeout=20) as resp:
  if resp.status!=200:raise ValueError('bad status')
  raw=resp.read(2_000_001)
  if len(raw)>2_000_000:raise ValueError('oversize feed')
  return json.loads(raw)

def run():
 cfg=load(CONFIG); old=load(OUTPUT)
 games={x['id']:x for x in old.get('games',[]) if isinstance(x,dict) and x.get('verified')}
 history={(x['game'],x['version']):x for x in old.get('history',[]) if isinstance(x,dict) and x.get('verified')}
 successes=0;errors=[]
 for src in cfg.get('sources',[]):
  try:
   if not src.get('enabled',False):continue
   # Sources must be explicitly allowlisted and provide verified structured records.
   doc=fetch(src['url'],src['domain'])
   if doc.get('schema')!=1:raise ValueError('schema mismatch')
   for g in doc.get('games',[]):
    if g.get('id') not in GAMES or g.get('verified') is not True:continue
    if g.get('phases') and not all(valid_phase(p) for p in g['phases']):continue
    if not g.get('evidence_url','').startswith('https://'):continue
    games[g['id']]=g
   for h in doc.get('history',[]):
    if h.get('game') not in GAMES or not h.get('version') or h.get('verified') is not True:continue
    if not h.get('source','').startswith('https://') or not h.get('phases') or not all(valid_phase(p) for p in h['phases']):continue
    history[(h['game'],h['version'])]=h
   successes+=1
  except Exception as exc:errors.append(f"{src.get('id','unknown')}: {exc}")
 result={'schema':1,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat() if successes else old.get('updated_at'), 'games':list(games.values()),'history':list(history.values())}
 if result['games']!=old.get('games',[]) or result['history']!=old.get('history',[]):
  with tempfile.NamedTemporaryFile('w',dir=OUTPUT.parent,encoding='utf-8',delete=False) as f:
   json.dump(result,f,ensure_ascii=False,indent=2);tmp=f.name
  os.replace(tmp,OUTPUT)
 print(json.dumps({'sources_success':successes,'errors':errors,'games':len(games),'history':len(history)},ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':run()
