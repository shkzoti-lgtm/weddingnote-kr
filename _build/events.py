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
CANON_HD  = ["지역","행사명","시작일","종료일","장소","상태","이미지","신청링크","혜택"]
WARN = []          # 빌드 중 발견한 시트 이상 (gen.py 가 진단 파일로 뽑는다)

# 시트 날짜 칸이 서식 때문에 텍스트를 거부하면 '상시'가 통째로 지워진다.
# 그럴 때 종료일·상태 칸에 남은 반복 표현으로도 상시를 알아보게 한다.
_RECUR_RE = re.compile(r"매주|매월|주말|평일|연중|상시|수시|상설")

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
    # 시작일이 비었는데 종료일·상태에 '매주 토요일/일요일' 같은 반복 표현이 남아 있으면 상시로 본다
    if not st:
        for v in (en, sc):
            if v and _RECUR_RE.search(v) and not re.search(r"\d{4}\D+\d{1,2}\D+\d{1,2}", v):
                return v
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

    # 1행이 표준 헤더인지 확인한다. 셀에 여러 줄을 한꺼번에 붙여넣으면
    # 헤더가 통째로 덮여, 예전에는 여기서 조용히 전체가 어긋났다.
    hd_ok = hd[:2] == CANON_HD[:2]
    if not hd_ok:
        WARN.append("시트1 1행(헤더)이 표준이 아닙니다 → 표준 순서로 대체해 읽었습니다. "
                    "1행 첫 칸: %r" % (hd[0][:60] if hd else ""))
        print("  [경고] 시트1 헤더 손상 — 표준 순서로 대체")
        hd = list(CANON_HD)

    # '수동추가' 탭은 자기 헤더만 정상이면 병합한다 (시트1 헤더 상태와 무관)
    try:
        extra = _fetch_tab("수동추가")
        if len(extra) > 1 and any(c.strip() for c in extra[0]):
            ehd = [c.strip() for c in extra[0]]
            if ehd[:2] == CANON_HD[:2]:
                rows += extra[1:]
                print("  수동추가 탭: %d건 병합" % (len(extra)-1))
            else:
                WARN.append("수동추가 탭 헤더가 표준이 아니라 병합하지 않았습니다: %r" % ehd[:2])
    except Exception as e:
        WARN.append("수동추가 탭을 읽지 못했습니다 (%s)" % type(e).__name__)
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
    prev = 0
    try:
        prev = sum(1 for _ in open(CACHE, encoding="utf-8"))
    except Exception:
        pass
    # 시트 사고(헤더 덮어쓰기·행 삭제)로 건수가 반토막 나면 캐시를 지키고 경고만 남긴다.
    if prev >= 50 and len(out) < prev * 0.5:
        WARN.append("시트 건수가 %d → %d 로 급감해 캐시를 유지했습니다. 시트를 확인하세요." % (prev, len(out)))
        print("  [경고] 시트 급감 %d → %d — 캐시 유지" % (prev, len(out)))
        return prev
    if len(out) >= 10:
        open(CACHE, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return len(out)

def slugify(name):
    """URL 슬러그. 넷리파이가 대문자 경로를 소문자로 301 리다이렉트하기 때문에
       처음부터 소문자로 만든다. (대문자 슬러그는 canonical 과 실제 URL 이 어긋나
       네이버에서 '수집제한(리다이렉션된 페이지)'으로 잡힌다)"""
    s = unicodedata.normalize("NFC", name).strip().lower()
    s = re.sub(r'[^\w가-힣]+', '-', s).strip('-')
    return s[:60]

def sortkey(x):
    """목록 정렬 기준 — 상시 진행을 맨 위로, 그다음 시작일이 빠른 순.
       (not always) 이라 상시는 0, 나머지는 1 이 되어 앞에 선다."""
    return (not x.get("always"), x["start"], x["city"])

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
        if s.strip() in ALWAYS_WORDS:
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
    evs.sort(key=sortkey)
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
