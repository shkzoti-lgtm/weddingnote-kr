# -*- coding: utf-8 -*-
"""행사 데이터 로더 — 빌드 시 구글시트에서 가져와 정적 HTML로 주입
   네트워크 되면 시트 fetch, 안 되면 events_cache.psv 사용"""
import os, re, csv, io, json, datetime, unicodedata
from data import SHEET_ID, DOMAIN

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "events_cache.psv")
BANNER = "https://replyalba.com/banner/"
PT = "https://replyalba.com/pt/"

def _norm_date(s):
    s = (s or "").strip()
    m = re.search(r'(\d{4})\D+(\d{1,2})\D+(\d{1,2})', s)
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else ""

def _fetch_tab(sheet_name=None):
    """구글시트 한 탭을 CSV로 읽어 행 리스트 반환"""
    import urllib.request, urllib.parse
    base = "https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&t=%d" % (
        SHEET_ID, int(datetime.datetime.now().timestamp()))
    if sheet_name:
        base += "&sheet=" + urllib.parse.quote(sheet_name)
    txt = urllib.request.urlopen(base, timeout=25).read().decode("utf-8")
    return list(csv.reader(io.StringIO(txt)))

def fetch_sheet():
    """시트에서 최신 데이터 가져와 캐시 갱신 (시트1 + 수동추가 탭 병합)"""
    rows = _fetch_tab()
    if len(rows) < 2: raise RuntimeError("빈 시트")
    hd = [c.strip() for c in rows[0]]

    # '수동추가' 탭이 있으면 이어붙임 (헤더 제외)
    try:
        extra = _fetch_tab("수동추가")
        if len(extra) > 1 and any(c.strip() for c in extra[0]):
            ehd = [c.strip() for c in extra[0]]
            if ehd[:2] == hd[:2]:          # 헤더 구조 동일할 때만
                rows += extra[1:]
                print("  수동추가 탭: %d건 병합" % (len(extra)-1))
    except Exception as e:
        pass
    def ix(n, d):
        return hd.index(n) if n in hd else d
    iR,iN,iS,iE,iP,iIMG,iL = ix('지역',0),ix('행사명',1),ix('시작일',2),ix('종료일',3),ix('장소',4),ix('이미지',6),ix('신청링크',7)
    iB = hd.index('혜택') if '혜택' in hd else -1
    out = []
    for r in rows[1:]:
        if len(r) <= iL or not r[iN].strip(): continue
        img = r[iIMG].strip().replace(BANNER, "")
        link = r[iL].strip().replace(PT, "")
        ben = r[iB].strip().replace("|"," ") if (iB >= 0 and len(r) > iB) else ""
        out.append("|".join([r[iR].strip(), r[iN].strip().replace("|","/"),
            _norm_date(r[iS]), _norm_date(r[iE]), r[iP].strip().replace("|"," "), img, link, ben]))
    if len(out) >= 10:
        open(CACHE, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return len(out)

def slugify(name):
    s = unicodedata.normalize("NFC", name).strip()
    s = re.sub(r'[^\w가-힣]+', '-', s).strip('-')
    return s[:60]

def load(refresh=True):
    if refresh:
        try:
            n = fetch_sheet(); print("  시트 최신화: %d건" % n)
        except Exception as e:
            print("  시트 fetch 실패 → 캐시 사용 (%s)" % type(e).__name__)
    evs = []
    today = datetime.date.today()
    seen = set()
    for line in open(CACHE, encoding="utf-8"):
        p = line.rstrip("\n").split("|")
        if len(p) < 7: continue
        city, name, s, e, place, img, code = p[:7]
        benefit = p[7] if len(p) > 7 else ""
        if not (city and name and s): continue
        try:
            sd = datetime.date.fromisoformat(s)
            ed = datetime.date.fromisoformat(e) if e else sd
        except ValueError:
            continue
        if ed < today: continue                      # 지난 행사 제외
        key = (city, name, s)
        if key in seen: continue
        seen.add(key)
        evs.append({
            "city": city, "name": name, "start": sd, "end": ed,
            "place": place,
            "img": (BANNER + img) if img else "",
            "link": (PT + code) if code else "/초대권-신청/",
            "slug": slugify(name) + "-" + s.replace("-", ""),
            "benefit": benefit,
            "dday": (sd - today).days,
            "month": s[:7],
        })
    evs.sort(key=lambda x: (x["start"], x["city"]))
    return evs

DOW = "월화수목금토일"
def fmt(d):     return "%d.%02d.%02d(%s)" % (d.year, d.month, d.day, DOW[d.weekday()])
def fmt_short(d): return "%02d.%02d(%s)" % (d.month, d.day, DOW[d.weekday()])

VENUE_KEYS = [
 ("코엑스","코엑스"),("SETEC","SETEC"),("킨텍스","킨텍스"),("벡스코","벡스코"),
 ("송도컨벤시아","송도컨벤시아"),("수원컨벤션센터","수원컨벤션센터"),("수원메쎄","수원메쎄"),
 ("스타필드","스타필드"),("롯데백화점","롯데백화점"),("신세계백화점","신세계백화점"),
 ("현대백화점","현대백화점"),("AK플라자","AK플라자"),("갤러리아","갤러리아"),
 ("아이파크","용산 아이파크"),("엑스코","엑스코"),("DCC","DCC 대전컨벤션센터"),
 ("오스코","청주 오스코"),("타임빌라스","타임빌라스"),
]
def venue_of(ev):
    hay = ev["place"] + " " + ev["name"]
    for k, label in VENUE_KEYS:
        if k in hay: return label
    return None
