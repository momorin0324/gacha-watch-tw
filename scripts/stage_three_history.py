"""Inspect structured records delivered to BannerHistory's public history page."""
import collections,json,re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

for slug in ("bd2","gf2","nikke"):
    url = f"https://bannerhistory.app/tw/{slug}-pickup-history"
    response = requests.get(url,timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
    flight = ""
    for script in soup.find_all("script"):
        text = script.get_text()
        if text.startswith("self.__next_f.push("):
            data = json.loads(text[len("self.__next_f.push("):-1])
            if data[0] == 1:
                flight += data[1]
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values(): yield from walk(child)
        elif isinstance(value,list):
            for child in value: yield from walk(child)
    shapes=collections.Counter()
    examples={}
    for line in flight.splitlines():
        try: v=json.loads(line.partition(":")[2])
        except ValueError: continue
        for obj in walk(v):
            keys=",".join(obj.keys())
            shapes[keys]+=1
            if keys not in examples:examples[keys]=str(obj)[:2400]
    report={"shapes":[[k,shapes[k],examples[k]] for k in shapes if any(t in k.lower() for t in ["date","start","char","banner","costume","nikke","region","page"])][:65],"article_count":len(soup.select("article")),"page_text":soup.find("main").get_text(" ",strip=True)[:450],"bottom":soup.find("main").get_text(" ",strip=True)[-430:],"head_flight":flight[:900]}
    Path("evidence/three-history/"+slug+"-shape.json").write_text(json.dumps(report,ensure_ascii=False,indent=1))

    if slug == "nikke":
        report["contexts"]={}
        for word in ["sky-temp","2026-11-19","Sky","招募","startAt","pickups","banners","characters","rows"]:
            idx=flight.find(word)
            if idx != -1:report["contexts"][word]=flight[max(0,idx-200):idx+1100]
        report["shapeAll"]=[[k,n,examples[k][:700]] for k,n in shapes.most_common(48)]
        report["start"]=[(line[:130],len(line)) for line in flight.splitlines()][:150]
        Path("evidence/three-history/nikke-debug.json").write_text(json.dumps(report,ensure_ascii=False,indent=1))
