"""Cache exact-name character illustrations from each game's own BWIKI."""
import hashlib
import io
import json
import re
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from opencc import OpenCC
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
WIKIS = {
    "genshin": "ys", "starrail": "sr", "zzz": "zzz", "wuwa": "wutheringwaves",
    "endfield": "zmd", "nte": "yh", "gfl2": "gf2", "nikke": "nikke",
    "bd2": "browndust2", "promilia": "ap",
}
ALIASES = {"hsr": "starrail", "azurpromilia": "promilia", "nter": "nte", "silverpalace": "silver"}
SPECIAL_FILES = {
    "genshin": ["{}抽卡立绘.png"],
    "starrail": ["{}立绘2.png"],
    "zzz": ["角色立绘-{}-官方介绍.png"],
    "wuwa": ["角色 {} 立绘.png"],
    "promilia": ["{}官方海报.jpg"],
}
CONVERT = OpenCC("tw2s")
ART_LIMIT = 24 * 1024 * 1024


def banner_names():
    html = (ROOT / "index.html").read_text()
    games, _ = json.JSONDecoder().raw_decode(html.split("const seed=", 1)[1])
    updates = json.loads((ROOT / "data/updates.json").read_text())
    found = set()
    for game in games + updates["games"]:
        game_id = ALIASES.get(game["id"], game["id"])
        records = [game] + [game[k] for k in ("current_version", "next_version") if game.get(k)]
        for record in records:
            for field in ("phases", "next_phases", "special_banners"):
                for phase in record.get(field, []):
                    names = phase.get("characters") or phase.get("five_star") or ""
                    for name in names if isinstance(names, list) else re.split("、", names):
                        name = name.strip()
                        if (game_id in WIKIS or game_id == "silver") and name and len(name) <= 64 and "待官方" not in name:
                            found.add((game_id, name))
    return sorted(found)


def fetch(url, limit):
    req = Request(url, headers={"User-Agent": "GachaWatchTW/1.0 (+https://github.com/momorin0324/gacha-watch-tw)"})
    with urlopen(req, timeout=15) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("response too large")
    return data


class SilverCharacters(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag != "a" or "char-card" not in attrs.get("class", "").split():
            return
        match = re.fullmatch(r"/characters/(\d+)/", attrs.get("href", ""))
        for name in attrs.get("data-name", "").split():
            if match:
                self.ids.setdefault(name, set()).add(match[1])


@lru_cache(maxsize=1)
def silver_characters():
    catalog = SilverCharacters()
    catalog.feed(fetch("https://sp-cbt2.csxylic.com/characters/", 1_000_000).decode())
    return catalog.ids


def image_url(game, name):
    simplified = CONVERT.convert(name).replace("・", "·")
    if game == "silver":
        matches = silver_characters().get(simplified, set())
        if len(matches) == 1:
            char_id = next(iter(matches))
            return f"https://sp-cbt2.csxylic.com/icons/Character/GachaResultCharacter/T_GachaResultCharacter_{char_id}.png"
        return None
    patterns = ["{}横版立绘.png", "{}横幅角色立绘.png", "{}横版立绘.jpg"] + SPECIAL_FILES.get(game, []) + ["{}立绘.png", "{}立绘.jpg", "角色立绘-{}.png", "{}官方立绘.png"]
    titles = [p.format(simplified) for p in patterns]
    query = urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size|mime",
                       "titles": "|".join("File:" + title for title in titles)})
    result = json.loads(fetch(f"https://wiki.biligame.com/{WIKIS[game]}/api.php?{query}", 500_000))
    pages = {p["title"].split(":", 1)[-1]: p for p in result["query"]["pages"].values()}
    candidates = []
    for title in titles:
        for img in pages.get(title, {}).get("imageinfo", []):
            url = urlparse(img["url"])
            if (url.scheme == "https" and url.hostname == "patchwiki.biligame.com"
                    and url.path.startswith("/images/" + WIKIS[game] + "/")
                    and img["mime"] in ("image/png", "image/jpeg", "image/webp")
                    and img["size"] <= ART_LIMIT and min(img["width"], img["height"]) >= 350):
                candidates.append(img)
    # Prefer landscape illustrations, retaining game-specific title priority on ties.
    best = max(candidates, key=lambda img: img["width"] >= 1.5 * img["height"], default=None)
    return best["url"] if best else None


def cache_image(data, destination):
    with Image.open(io.BytesIO(data)) as source:
        if source.width * source.height > 50_000_000:
            raise ValueError("excessive image dimensions")
        image = ImageOps.exif_transpose(source).convert("RGBA")
        bbox = image.getchannel("A").getbbox()
        if not bbox or min(bbox[2] - bbox[0], bbox[3] - bbox[1]) < 250:
            raise ValueError("empty or undersized artwork")
        image = image.crop(bbox)
        image.thumbnail((1600, 1400), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_suffix(".tmp")
        image.save(temp, "WEBP", quality=85)
        temp.replace(destination)


def main():
    manifest = ROOT / "data/discovered-art.json"
    discovered = json.loads(manifest.read_text()) if manifest.exists() else {}
    curated = json.loads((ROOT / "data/character-art.json").read_text())
    for game, name in banner_names():
        if name in curated.get(game, {}) or name in discovered.get(game, {}):
            continue
        try:
            url = image_url(game, name)
            if not url:
                print(f"No exact artwork yet: {game} / {name}")
                continue
            key = hashlib.sha256(name.encode()).hexdigest()[:20]
            path = f"assets/pool-art/discovered/{game}-{key}.webp"
            cache_image(fetch(url, ART_LIMIT), ROOT / path)
            discovered.setdefault(game, {})[name] = path
        except (OSError, ValueError, KeyError, Image.DecompressionBombError) as error:
            print(f"Will retry {game} / {name}: {error}")
    manifest.write_text(json.dumps(discovered, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
