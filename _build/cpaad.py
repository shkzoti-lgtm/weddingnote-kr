# -*- coding: utf-8 -*-
"""cpaad 보조 수집 — 넷리파이 빌드 시 실행.
   구글 Apps Script에서 접속이 막히는 경우를 대비한 2차 경로.
   replyalba(시트)에 없는 행사만 반환한다."""
import re, datetime, urllib.request

CPAAD_ID  = "imigin84"
CPAAD_URL = "https://ad.cpaad.co.kr/wedunited01drc/" + CPAAD_ID
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

SINGLE = {'서울','인천','부산','제주'}
GROUP = {
 '경기':['고양','광명','구리','군포','김포','남양주','부천','성남','수원','시흥','안산','안성','안양','양주','오산','용인','의정부','이천','파주','평택','하남','화성'],
 '충청':['대전','당진','서산','아산','제천','진천','천안','청주','충주'],
 '전라':['광주','군산','익산','전주'],
 '강원':['강릉','동해','속초','원주','춘천'],
 '경상':['대구','거제','김해','울산','진주','창원','포항'],
}

def _cat(name):
    n = re.sub(r'\s+','',name)
    if re.search(r'허니문|신혼여행', n): return 'honeymoon'
    if re.search(r'혼수|가전', n):       return 'home'
    if re.search(r'드레스', n):          return 'dress'
    if re.search(r'예물|주얼리|한복|예복', n): return 'jewel'
    if re.search(r'웨딩홀', n):          return 'hall'
    return 'wedding'

def _fix_trunc(n):
    n = n.strip()
    if '…' not in n and not n.endswith('...'): return n
    n = n.replace('…','').rstrip('.').strip()
    if n.endswith('박람'): n += '회'
    return n

def _norm(n): return re.sub(r'[·/,()\-]','', re.sub(r'\s+','',n))

def _bigcat(t):
    t = re.sub(r'\s+','',t)
    for k in ['서울','경기','인천','부산','충청','전라','강원','경상','제주']:
        if t.startswith(k): return k
    return None

def _dates(txt):
    md = re.findall(r'(\d{1,2})월\s*(\d{1,2})일', txt or '')
    if not md: return None
    today = datetime.date.today()
    def iso(mm, dd):
        mm, dd = int(mm), int(dd)
        y = today.year
        try: cand = datetime.date(y, mm, dd)
        except ValueError: return None
        if (today - cand).days > 90: y += 1
        return "%d-%02d-%02d" % (y, mm, dd)
    s = iso(*md[0]); e = iso(*md[-1])
    return (s, e) if s and e else None

def fetch_html():
    for url in (CPAAD_URL,
                CPAAD_URL.replace("https://","http://"),
                "https://r.jina.ai/" + CPAAD_URL):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                    "Accept":"text/html,*/*", "Accept-Language":"ko-KR,ko;q=0.9"})
            html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8","ignore")
            if "ad_title" in html:
                print("  cpaad 접속 성공: %s (%d bytes)" % (url.split('//')[1][:28], len(html)))
                return html
        except Exception as e:
            print("  cpaad 실패(%s): %s" % (url.split('//')[1][:20], type(e).__name__))
    return None

def parse(html):
    marks = [(m.start(), _bigcat(m.group(1))) for m in
             re.finditer(r'(서울|경기도|인천|부산|충청도|전라도|강원도|경상도|제주도)\s*웨딩박람회\s*일정', html)]
    out = []
    for a in re.finditer(r"""<a[^>]+href=["']([^"']*/%s)["'][^>]*>(.*?)</a>""" % CPAAD_ID, html, re.S):
        href, block = a.group(1), a.group(2)
        if 'ad_title' not in block: continue
        cat = None
        for idx, c in marks:
            if idx < a.start(): cat = c
            else: break
        if not cat: continue
        def pick(cls):
            mm = re.search(r"""<div class=["']?%s["']?>(.*?)</div>""" % cls, block, re.S)
            if not mm: return ''
            t = re.sub(r'<br\s*/?>', ' ', mm.group(1))
            return re.sub(r'\s+',' ', re.sub(r'<[^>]*>','',t)).strip()
        name = _fix_trunc(pick('ad_title'))
        if not name: continue
        info, date, loc = pick('ad_info'), pick('ad_date'), pick('ad_location')
        d = _dates(date)
        if not d: continue
        city = None
        if cat in SINGLE: city = cat
        else:
            for c in GROUP.get(cat, []):
                if c in loc: city = c; break
        if not city: continue
        im = re.search(r'<img[^>]+src=["\']?([^\s"\'>]+)', block)
        img = im.group(1) if im else ''
        link = ('https:' + href) if href.startswith('//') else href
        out.append({"city":city, "name":name, "start":d[0], "end":d[1],
                    "place":loc, "img":img, "link":link, "benefit":info})
    return out

def merge_new(existing):
    """existing: events.load() 결과. cpaad에만 있는 행사를 dict 리스트로 반환"""
    html = fetch_html()
    if not html:
        print("  cpaad 수집 건너뜀 (접속 불가)")
        return []
    rows = parse(html)
    by_name, by_place = set(), set()
    for e in existing:
        s = e["start"].isoformat()
        by_name.add(_norm(e["name"]) + "|" + s)
        by_place.add("%s|%s|%s|%s" % (e["city"], s, re.sub(r'\s+','',e["place"])[:10], _cat(e["name"])))
    new = []
    for r in rows:
        k1 = _norm(r["name"]) + "|" + r["start"]
        k2 = "%s|%s|%s|%s" % (r["city"], r["start"], re.sub(r'\s+','',r["place"])[:10], _cat(r["name"]))
        if k1 in by_name or k2 in by_place: continue
        by_name.add(k1); by_place.add(k2)
        new.append(r)
    print("  cpaad: 파싱 %d건 중 신규 %d건" % (len(rows), len(new)))
    return new
