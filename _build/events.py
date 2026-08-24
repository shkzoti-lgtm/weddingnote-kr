# -*- coding: utf-8 -*-
"""행사 데이터 로더 — 빌드 시 구글시트에서 가져와 정적 HTML로 주입
   네트워크 되면 시트 fetch, 안 되면 events_cache.psv 사용"""
import os, re, csv, io, json, datetime, unicodedata
from data import SHEET_ID, DOMAIN

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "events_cache.psv")
BANNER = "https://replyalba.com/banner/"
PT = "https://replyalba.com/pt/"

ALWAYS_WORDS = ("상시", "상시진행", "상시모집", "연중", "수시")

def _always_label(start, end, status):
    """상시 행사인지 판별하고 화면에 쓸 문구를 돌려준다.
       시트의 날짜 칸이 서식 때문에 텍스트를 못 받는 경우가 있어
       '상태' 칸으로도 지정할 수 있게 열어 둔다.
         · 시작일 = 상시        / 종료일 = 매주 토요일·일요일
         · 상태  = 상시 · 매주 토요일·일요일   (날짜 칸은 비워도 됨)
       상시가 아니면 None."""
    st = (start or "").strip()
    en = (end or "").strip()
    sc = (status or "").strip()
    if st in ALWAYS_WORDS:
        return en or "상시 진행"
    for w in ALWAYS_WORDS:
        if sc.startswith(w):
            tail = sc[len(w):].lstrip(" ·-—|/")
            return tail or en or "상시 진행"
    return None

def _strip_prefix(prefix, v):
    """알려진 접두어로 시작할 때만 떼어낸다. 문자열 중간은 건드리지 않는다."""
    v = (v or "").strip()
    return v[len(prefix):] if v.startswith(prefix) else v

def _abs_url(prefix, v):
    """이미 절대 URL이면 그대로 쓰고, 코드/파일명일 때만 접두어를 붙인다.
       시트에 replyalba 외 매체(cpaad 등) URL이 통째로 들어오는 경우 대응."""
    v = (v or "").strip()
    if not v: return ""
    if v.lower().startswith(("http://", "https://")): return v
    if v.startswith("//"): return "https:" + v
    return prefix + v

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
    iST = ix('상태', 5)
    out = []
    for r in rows[1:]:
        if len(r) <= iL or not r[iN].strip(): continue
        img  = _strip_prefix(BANNER, r[iIMG])
        link = _strip_prefix(PT, r[iL])
        ben = r[iB].strip().replace("|"," ") if (iB >= 0 and len(r) > iB) else ""
        _st = r[iST].strip() if (iST >= 0 and len(r) > iST) else ""
        _lab = _always_label(r[iS], r[iE], _st)
        if _lab is not None:
            d1, d2 = "상시", _lab.replace("|", " ")
        else:
            d1, d2 = _norm_date(r[iS]), _norm_date(r[iE])
        out.append("|".join([r[iR].strip(), r[iN].strip().replace("|","/"),
            d1, d2, r[iP].strip().replace("|"," "), img, link, ben]))
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

        # 상시 진행 행사 — 시작일 칸에 '상시', 종료일 칸에 표기할 문구
        # (예: 시작일=상시 / 종료일=매주 토요일·일요일)
        if s.strip() in ("상시", "상시진행", "상시모집"):
            label = (e or "").strip() or "상시 진행"
            key = (city, name, "상시")
            if key in seen: continue
            seen.add(key)
            evs.append({
                "city": city, "name": name,
                "start": today, "end": today + datetime.timedelta(days=365),
                "place": place,
                "img": _abs_url(BANNER, img),
                "link": _abs_url(PT, code) or "/초대권-신청/",
                "slug": slugify(name) + "-상시",     # 날짜가 안 붙어 URL 이 고정된다
                "benefit": benefit,
                "dday": 0,
                "month": "",                          # 월별 페이지에는 넣지 않는다
                "always": True,
                "date_text": label,                   # 화면에 이 문구를 그대로 쓴다
            })
            continue

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
            "img": _abs_url(BANNER, img),
            "link": _abs_url(PT, code) or "/초대권-신청/",
            "slug": slugify(name) + "-" + s.replace("-", ""),
            "benefit": benefit,
            "dday": (sd - today).days,
            "month": s[:7],
            "always": False,
            "date_text": "",
        })
    evs.sort(key=lambda x: (bool(x.get("always")), x["start"], x["city"]))
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
