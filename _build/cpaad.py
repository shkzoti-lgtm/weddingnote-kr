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

CPAAD_ORIGIN = "https://ad.cpaad.co.kr"

DIAG = []          # 빌드 진단 로그 — site/_cpaad-status.txt 로 출력된다
def _log(msg):
    DIAG.append(msg)
    print("  " + msg)

def _absolutize(u):
    """cpaad 페이지의 상대경로를 절대 URL로 만든다."""
    u = (u or "").strip().strip('"\'')
    if not u: return ""
    if u.lower().startswith(("http://", "https://")): return u
    if u.startswith("//"): return "https:" + u
    if u.startswith("/"):  return CPAAD_ORIGIN + u
    return CPAAD_ORIGIN + "/" + u

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

_DATE_RE = re.compile(
    r'(?P<y>20\d{2})\s*[.\-/년]\s*(?P<ym>\d{1,2})\s*[.\-/월]\s*(?P<yd>\d{1,2})'      # 2026.09.22 / 2026년 9월 22일
    r'|(?P<km>\d{1,2})\s*월\s*(?P<kd>\d{1,2})\s*일'                                    # 9월 22일
    r'|(?<!\d)(?P<m>0?[1-9]|1[0-2])\s*[.\-/]\s*(?P<d>0?[1-9]|[12]\d|3[01])(?!\d)'      # 09.22 / 9/22
)

def _dates(txt):
    """날짜 표기를 한 번에 훑어 처음·마지막 날짜를 뽑는다.
       기존엔 'M월 D일' 한 형식만 받아, 표기가 다르면 그 행사가 통째로 버려졌다."""
    t = txt or ''
    if not t: return None
    # 금액·수량 표기 오탐 방지 (3.5만원 → 3월 5일)
    t = re.sub(r'[\d.,]+\s*(?:만원|천원|원|[%％]|억)', ' ', t)
    today = datetime.date.today()

    def infer_year(mm, dd):
        y = today.year
        try: cand = datetime.date(y, mm, dd)
        except ValueError: return None
        if (today - cand).days > 90: y += 1
        return "%d-%02d-%02d" % (y, mm, dd)

    vals = []
    for m in _DATE_RE.finditer(t):
        g = m.groupdict()
        if g['y']:
            try:
                datetime.date(int(g['y']), int(g['ym']), int(g['yd']))
                vals.append("%04d-%02d-%02d" % (int(g['y']), int(g['ym']), int(g['yd'])))
            except ValueError: pass
        elif g['km']:
            v = infer_year(int(g['km']), int(g['kd']))
            if v: vals.append(v)
        elif g['m']:
            v = infer_year(int(g['m']), int(g['d']))
            if v: vals.append(v)
    if not vals: return None
    s0, e0 = vals[0], vals[-1]
    # 종료일이 시작일보다 앞서면 연도 추정 오차 → 종료일을 다음 해로
    if e0 < s0:
        try:
            ed = datetime.date.fromisoformat(e0)
            e0 = ed.replace(year=ed.year + 1).isoformat()
        except ValueError: e0 = s0
    return (s0, e0)

def fetch_html():
    for url in (CPAAD_URL,
                CPAAD_URL.replace("https://", "http://"),
                "https://r.jina.ai/" + CPAAD_URL):
        tag = url.split('//')[1][:34]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                    "Accept": "text/html,*/*", "Accept-Language": "ko-KR,ko;q=0.9"})
            with urllib.request.urlopen(req, timeout=25) as r:
                code = r.getcode()
                html = r.read().decode("utf-8", "ignore")
            has_title = "ad_title" in html
            has_id = CPAAD_ID in html
            _log("cpaad 응답 %s → HTTP %s, %d bytes, ad_title=%s, %s=%s"
                 % (tag, code, len(html), has_title, CPAAD_ID, has_id))
            if has_title:
                return html
            # 내용이 기대와 다르면 앞부분을 남겨 원인 판단에 쓴다
            head = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html[:1500]))[:400]
            _log("  받은 내용 앞부분: " + head)
        except Exception as e:
            _log("cpaad 실패 %s → %s: %s" % (tag, type(e).__name__, str(e)[:90]))
    _log("cpaad 수집 실패 — 세 경로 모두 사용 불가")
    return None

def parse(html):
    marks = [(m.start(), _bigcat(m.group(1))) for m in
             re.finditer(r'(서울|경기도|인천|부산|충청도|전라도|강원도|경상도|제주도)\s*웨딩박람회\s*일정', html)]
    out = []
    drop = {"권역미확인": 0, "제목없음": 0, "날짜파싱실패": 0, "도시미매칭": 0}
    seen_blocks = 0
    _unmatched = []
    for a in re.finditer(r"""<a[^>]+href=["']([^"']*/%s)["'][^>]*>(.*?)</a>""" % CPAAD_ID, html, re.S):
        href, block = a.group(1), a.group(2)
        if 'ad_title' not in block: continue
        seen_blocks += 1
        cat = None
        for idx, c in marks:
            if idx < a.start(): cat = c
            else: break
        if not cat:
            drop["권역미확인"] += 1; continue
        def pick(cls):
            mm = re.search(r"""<div class=["']?%s["']?>(.*?)</div>""" % cls, block, re.S)
            if not mm: return ''
            t = re.sub(r'<br\s*/?>', ' ', mm.group(1))
            return re.sub(r'\s+',' ', re.sub(r'<[^>]*>','',t)).strip()
        name = _fix_trunc(pick('ad_title'))
        if not name:
            drop["제목없음"] += 1; continue
        info, date, loc = pick('ad_info'), pick('ad_date'), pick('ad_location')
        d = _dates(date)
        if not d:
            drop["날짜파싱실패"] += 1; continue
        city = None
        if cat in SINGLE: city = cat
        else:
            for c in GROUP.get(cat, []):
                if c in loc: city = c; break
        if not city:
            drop["도시미매칭"] += 1
            if len(_unmatched) < 12: _unmatched.append("%s / %s" % (cat, loc[:30]))
            continue
        im = re.search(r'<img[^>]+src=["\']?([^\s"\'>]+)', block)
        img = _absolutize(im.group(1)) if im else ''
        link = _absolutize(href)
        out.append({"city":city, "name":name, "start":d[0], "end":d[1],
                    "place":loc, "img":img, "link":link, "benefit":info})
    if seen_blocks:
        _lost = sum(drop.values())
        _log("cpaad 파싱: 블록 %d개 중 %d건 인식, %d건 누락 %s"
             % (seen_blocks, len(out), _lost,
                {k: v for k, v in drop.items() if v} if _lost else ""))
        if _unmatched:
            _log("  도시 미매칭 예시: " + " | ".join(_unmatched))
    else:
        _log("cpaad 파싱: 행사 블록을 하나도 못 찾음 — 페이지 구조가 바뀌었을 수 있습니다")
    return out

def merge_new(existing):
    """existing: events.load() 결과. cpaad에만 있는 행사를 dict 리스트로 반환"""
    html = fetch_html()
    if not html:
        _log("cpaad 수집 건너뜀 (접속 불가)")
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
    _log("cpaad: 파싱 %d건 중 시트에 없는 신규 %d건" % (len(rows), len(new)))
    if rows and not new:
        _log("  (파싱은 됐으나 전부 시트와 중복으로 판정됨)")
    for _r in new[:8]:
        _log("  신규: %s %s %s~%s" % (_r["city"], _r["name"][:22], _r["start"], _r["end"]))
    return new
