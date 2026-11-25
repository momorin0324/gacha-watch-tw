import re, sys, json, io, hashlib, html, concurrent.futures as cf
from urllib.parse import quote, urljoin
from pathlib import Path
sys.path.insert(0,'scripts')
import resolve_character_art as ar
from PIL import Image
names={"wuwa":["奧古斯塔","珂萊塔","守岸人","熾霞","釉瑚","淵武","尤諾","夏空","秋水","白芷","桃祈","嘉貝莉娜","露帕","散華","莫特斐","燈燈","仇遠","贊妮","秧秧","丹瑾","千咲","菲比","弗洛洛","坎特蕾拉","卜靈","琳奈","莫寧","卡提希婭","愛彌斯","陸·赫斯","西格莉卡","緋雪","達妮婭","露西","蕾貝卡","洛瑟菈","秧秧·玄翎","忌炎","吟霖","今汐","長離","折枝","相里要","穗穗","清宵","景燃","椿","洛可可","布蘭特","心","鎖暝","莉莉"],"endfield":["萊萬汀","潔爾佩塔","伊馮","湯湯","洛西","莊方宜","弭弗","卡繆","訣","梨諾","提弗洛斯","祀","明河","小刻"],"nte":["娜娜莉","埃德嘉","薄荷","阿德勒","潯","哈尼婭","海月","翳","安魂曲","卡厄斯","真紅","伊洛伊","殘虹","靈可","黑羽","明音凜","曳爾沐","Exe"],"promilia":[],"silver":[]}
art=json.loads(Path('data/character-art.json').read_text())
disc=json.loads(Path('data/discovered-art.json').read_text())
def get(u,n=10000000): return ar.fetch(u,n)
def txt(u): return get(u).decode()
def end_assets():
    root='https://endfield.gryphline.com/zh-tw'
    operators=txt(root+'/operator'); main=txt(root)
    key_names=dict(re.findall(r'data-key="([^"]+)" style="background-image:[^>]+></div><div class="OperatorItem_contentBlock[^>]*><div[^>]+><span[^>]+>([^<]+)',operators))
    css_urls=re.findall(r'<link rel="stylesheet" href="([^"]+)',main)
    with cf.ThreadPoolExecutor(8) as e: css=''.join(e.map(txt,css_urls))
    assets=dict(re.findall(r'Operator_illustration__\w+\[data-key=([^\]]+)\]\{background-image:url\(([^)]+)',css))
    return {name:assets[k] for k,name in key_names.items() if k in assets}
try: ef=end_assets()
except Exception as ex: print('Endfield',str(ex));ef={}
en=dict(zip('奧古斯塔 珂萊塔 守岸人 熾霞 釉瑚 淵武 尤諾 夏空 秋水 白芷 桃祈 嘉貝莉娜 露帕 散華 莫特斐 燈燈 贊妮 秧秧 丹瑾 千咲 弗洛洛 坎特蕾拉 卜靈 琳奈 莫寧 卡提希婭 愛彌斯 陸·赫斯 達妮婭 露西 蕾貝卡 洛瑟菈 忌炎 吟霖 今汐 長離 折枝 相里要'.split(),'Augusta Carlotta Shorekeeper Chixia Youhu Yuanwu Iuno Ciaccona Aalto Baizhi Taoqi Galbrena Lupa Sanhua Mortefi Lumi Zani Yangyang Danjin Chisa Phrolova Cantarella Buling Lynae Mornye Cartethyia Aemeath Luuk_Herssen Denia Lucy Rebecca Lucilla Jiyan Yinlin Jinhsi Changli Zhezhi Xiangli_Yao'.split()))
def variants(g,n):
    if g=='endfield' and n in ef: yield ef[n]
    if g=='wuwa' and n in en:
        f=en[n]+'_Convene_Still.png';h=hashlib.md5(f.encode()).hexdigest()
        yield 'https://static.wikia.nocookie.net/wutheringwaves/images/'+h[0]+'/'+h[:2]+'/'+f+'/revision/latest'
    u=ar.image_url(g,n)
    if u: yield u
    if g in ('wuwa','nte'):
        title=ar.CONVERT.convert(n)
        page=txt('https://wiki.biligame.com/'+ar.WIKIS[g]+'/'+quote(('共鸣者/' if g=='wuwa' else '')+title))
        for a,url in re.findall(r'<img alt="([^"]*)" src="([^"]+)"',page):
            if title in a and ('立绘' in a or '角色海报' in a):
                u=html.unescape(url)
                yield u.rsplit('/',1)[0].replace('/thumb/','/') if '/thumb/' in u else u
def find(row):
    g,n=row
    for mapping in (art,disc):
        if n in mapping.get(g,{}):return g,n,mapping[g][n]
    try:
        for u in variants(g,n):
            try:
                raw=get(u,24000000); im=Image.open(io.BytesIO(raw));im.verify()
                if min(im.size)>=250:return g,n,u
            except Exception:pass
    except Exception as ex:print(g,n,str(ex))
    return g,n,None
out={};missing={}
with cf.ThreadPoolExecutor(8) as e:
    for g,n,u in e.map(find,[(g,n) for g,ns in names.items() for n in ns]):
        if u:out.setdefault(g,{})[n]=u
        else:missing.setdefault(g,[]).append(n)
for path,obj in [('data/history-art-additional.json',out),('history-art-missing.json',missing)]:
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print('MISSING',missing)
