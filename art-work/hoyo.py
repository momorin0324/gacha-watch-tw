import concurrent.futures as futures
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image, ImageOps

TARGETS = json.loads(Path("art-work/hoyo-targets.json").read_text())
EXISTING = json.loads(Path("data/character-art.json").read_text())
DIRECTORY = Path("assets/history-hoyo")
DIRECTORY.mkdir(parents=True, exist_ok=True)

def fetch(url, request_headers=None):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GachaWatchTW/1.0)"}
    headers.update(request_headers or {})
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(22000001)
                if len(data) > 22000000:
                    raise ValueError("image too large")
                return data
        except Exception:
            if attempt == 1:
                raise
            time.sleep(0.3)

class NamedImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.title_text = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "img":
            self.items.append((attrs.get("alt", ""), attrs.get("data-src") or attrs.get("src", "")))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_text.append(data)

def normalize(name):
    return re.sub(r'[ ・·•「」&＆]', '', name)

def wiki_sources(name):
    wiki_name = name.strip('「」')
    parser = NamedImages()
    page = "https://wiki.biligame.com/zzz/" + urllib.parse.quote(wiki_name)
    parser.feed(fetch(page).decode())
    base = normalize(wiki_name)
    if base not in normalize(''.join(parser.title_text)):
        raise ValueError("page title did not match exact name")
    accepted = [normalize("角色立绘-" + wiki_name + suffix + ".png") for suffix in ("", "-官方介绍", "-官方介绍2")]
    found = {normalize(filename): src for filename, src in parser.items if src.startswith("https://patchwiki.biligame.com/images/zzz/")}
    return [found[key] for key in accepted if key in found]

def resolve(game, name, value):
    local = EXISTING.get(game, {}).get(name)
    if local and Path(local).is_file():
        with Image.open(local) as image:
            image.verify()
        return local, "existing"
    urls = [value]
    if game == "zzz":
        urls = wiki_sources(value)
    if game == "genshin":
        filename = value.rsplit("/", 1)[-1]
        urls.extend(["https://enka.network/ui/" + filename, "https://api.ambr.top/assets/UI/" + filename])
    errors = []
    for url in urls:
        try:
            headers = {"Referer": "https://wiki.biligame.com/"} if game == "zzz" else {}
            with Image.open(io.BytesIO(fetch(url, headers))) as source:
                if min(source.size) < 175:
                    raise ValueError("not splash art dimensions")
                image = ImageOps.exif_transpose(source).convert("RGBA")
                image = image.crop(image.getbbox())
                image.thumbnail((1100, 950), Image.Resampling.LANCZOS)
                filename = game + "-" + hashlib.sha256(url.encode()).hexdigest()[:14] + ".webp"
                path = DIRECTORY / filename
                buffer = io.BytesIO()
                image.save(buffer, format="WEBP", quality=82, method=4)
                path.write_bytes(buffer.getvalue())
                return str(path), url
        except Exception as exc:
            errors.append(str(exc))
    raise ValueError("; ".join(errors) or "no exact named art on character page")

def process(entry):
    game, name, value = entry
    try:
        local, url = resolve(game, name, value)
        return game, name, local, url
    except Exception as exc:
        return game, name, None, str(exc)

if __name__ == "__main__":
    entries = [(game,name,value) for game,rows in TARGETS.items() for name,value in rows.items()]
    mapping = {game:{} for game in TARGETS}
    evidence = {game:{} for game in TARGETS}
    missing = {game:{} for game in TARGETS}
    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        for game,name,local,src in pool.map(process, entries):
            if local:
                mapping[game][name] = local
                evidence[game][name] = src
            else:
                missing[game][name] = src
    for file,data in [("data/history-art-hoyo.json",mapping),("art-work/hoyo-report.json",{"sources":evidence,"missing":missing})]:
        Path(file).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    print({g:len(rows) for g, rows in mapping.items()}, flush=True)
