# -*- coding: utf-8 -*-
"""신규 B사이트 생성기 — 한글 클린URL + 문서 SEO 전면 적용
   실행: python3 gen.py     출력: ../site/"""
import os, re, json, html, random, datetime, shutil
from urllib.parse import quote
from data import *
from seo import *
import events as EV
import cpaad as CP

OUT = os.path.join(os.path.dirname(__file__), "..", "site")
TODAY_D = datetime.date.today()
TODAY = TODAY_D.isoformat()
URLS = []

def w(path, content):
    p = os.path.join(OUT, path.lstrip("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)

def enc_url(u):
    m = re.match(r'^(https?://[^/]+)(/.*)?$', u)
    host, path = m.group(1), m.group(2) or "/"
    return html.escape(host + quote(path, safe="/-_.~"))

def rnd_for(key):
    return random.Random(sum(ord(c)*(i+7) for i,c in enumerate(key)) * 7331 + 13)

# ── 공통 레이아웃 ────────────────────────────────────────────────
def header(active_region="", active_city=""):
    tabs = "".join(
        '<a class="%s" href="/%s/">%s</a>' % ("on" if n==active_region else "", n, n)
        for n,_ in REGIONS)
    sub = ""
    cs = cities_of(active_region)
    if cs:
        links = '<a class="%s" href="/%s/">전체</a>' % ("on" if not active_city else "", active_region)
        links += "".join('<a class="%s" href="/%s/%s/">%s</a>' %
                         ("on" if c==active_city else "", active_region, c, c) for c in cs)
        sub = '<nav class="subnav">%s</nav>' % links
    return f"""<header>
 <div class="bar"><div class="wrap">
   <a class="logo" href="/"><span class="mark">W</span>{SITE}</a>
   <nav class="gnb">
     <a href="/이번주-웨딩박람회/">이번주</a>
     <a href="/일정/">달력</a>
     <a href="/행사장/">행사장</a>
     <a href="/가이드/웨딩박람회-활용법/">활용법</a>
     <a href="/가이드/스드메-견적-비교/">스드메 견적</a>
     <a href="/가이드/결혼준비-체크리스트/">체크리스트</a>
     <a class="btn-sm" href="/초대권-신청/">초대권 신청</a>
   </nav>
 </div></div>
 <div class="wrap"><nav class="regionnav">{tabs}</nav>{sub}</div>
</header>"""

def breadcrumb_html(items):
    return '<div class="wrap"><nav class="bc">%s</nav></div>' % (
        " › ".join('<a href="%s">%s</a>'%(u.replace(DOMAIN,""),n) for n,u in items))

def footer():
    hub = "".join('<a href="/%s/">%s 웨딩박람회</a>'%(n,n) for n,_ in REGIONS)
    return f"""<footer>
 <div class="wrap">
  <div class="fnav"><b>지역별 일정</b><div class="chips">{hub}</div></div>
  <div class="fnav"><b>결혼준비 가이드</b><div class="chips">
    <a href="/이번주-웨딩박람회/">이번주 웨딩박람회</a>
    <a href="/일정/">월별 일정 달력</a>
    <a href="/행사장/">주요 행사장</a>
    <a href="/가이드/웨딩박람회-활용법/">웨딩박람회 활용법</a>
    <a href="/가이드/스드메-견적-비교/">스드메 견적 비교</a>
    <a href="/가이드/결혼준비-체크리스트/">결혼준비 체크리스트</a>
    <a href="/초대권-신청/">무료 초대권 신청</a>
    <a href="/개인정보처리방침/">개인정보처리방침</a></div></div>
  <p class="disc">본 사이트는 제휴 광고를 포함하며 일부 링크를 통해 수익이 발생할 수 있습니다.
   방문자에게 추가 비용은 없습니다. 행사 일정과 혜택은 주최 측 사정에 따라 변경될 수 있습니다.</p>
  <p class="biz">Copyright © {YEAR} {SITE}. All rights reserved.</p>
 </div></footer>
<script src="/assets/events.js" defer></script></body></html>"""

# ── 지역 페이지 ─────────────────────────────────────────────────
def faqs_for(loc):
    return [
     ("%s 웨딩박람회는 얼마나 자주 열리나요?"%loc,
      "%s에서는 %s을 중심으로 주말마다 크고 작은 박람회가 이어집니다. 규모와 참여 업체는 주최에 따라 달라지므로 최신 일정에서 확인하세요."%(loc, VENUE.get(loc,"주요 행사장"))),
     ("입장료가 있나요?",
      "대부분 무료 초대권으로 입장합니다. 사전 예약자에게는 우선 상담과 방문 선물 같은 혜택이 제공되는 경우가 많습니다."),
     ("%s 박람회 방문 전에 무엇을 준비해야 하나요?"%loc,
      "총 예산 상한선과 희망 예식 날짜 1~3순위, 그리고 반드시 지킬 조건을 부부가 미리 합의해 가면 상담이 빠르고 충동 계약을 막을 수 있습니다."),
     ("현장에서 꼭 계약해야 하나요?",
      "아닙니다. 여러 박람회를 비교한 뒤 결정해도 늦지 않습니다. 다만 인기 예식장 날짜는 조기 마감될 수 있어 일정 확인은 서두르는 편이 좋습니다."),
     ("계약할 때 무엇을 확인해야 하나요?",
      "촬영 원본·수정본 비용, 드레스 피팅비와 헬퍼비, 예식장 수수료 포함 여부를 확인하고 구두 약속은 계약서 특약란에 남겨야 합니다."),
     ("사전 신청은 언제까지 해야 하나요?",
      "대부분 행사 당일 오전까지 가능하지만 인기 박람회는 정원이 조기 마감됩니다. 2~3일 전에 신청하면 원하는 시간대를 배정받기 수월합니다."),
     ("주차는 어떤가요?",
      "컨벤션센터와 대형 쇼핑몰은 자체 주차장이 있고 박람회 방문 시 할인되는 경우가 많습니다. 백화점 행사장은 주말 혼잡하니 대중교통을 권합니다."),
     ("평일과 주말 중 언제 가는 게 좋나요?",
      "주말은 참여 업체와 사은품이 많고, 평일은 한산해 담당자와 여유롭게 상담할 수 있습니다. 시간이 된다면 평일 오전 방문이 가장 효율적입니다."),
     ("신청하면 이 사이트가 개인정보를 보관하나요?",
      "아닙니다. 이 사이트는 일정 안내만 하며 신청은 각 박람회 운영사 공식 페이지에서 진행됩니다. 입력한 정보는 운영사가 관리합니다."),
    ]

def loc_page(loc, region, path, my_evs=None, total_ev=0):
    url = DOMAIN + path
    is_hub = (loc == region)
    r = rnd_for(loc)
    intro = r.choice(POOL_INTRO)
    tips  = r.sample(POOL_TIP, r.randint(4,5))
    cautions = r.sample(POOL_CAUTION, 3)
    label = REGION_LABEL.get(region, region)

    title = f"{YEAR} {loc} 웨딩박람회 일정, 무료초대권 신청 | {loc} 결혼박람회 총정리"
    desc  = (f"{YEAR}년 {loc} 웨딩박람회 일정을 매일 업데이트합니다. {VENUE.get(loc,'주요 행사장')}에서 열리는 "
             f"{loc} 결혼박람회 무료 초대권 신청과 웨딩홀·스드메 비교 요령을 정리했습니다.")
    kw = (f"{loc}웨딩박람회, {loc}웨딩박람회일정, {loc}결혼박람회, {loc}웨딩박람회무료초대권, "
          f"{loc}스드메, {loc}웨딩홀, {YEAR}{loc}웨딩박람회, {label}웨딩박람회, 웨딩박람회일정")

    bc = [("홈", DOMAIN+"/")]
    if not is_hub: bc.append((region, DOMAIN+"/%s/"%region))
    bc.append((loc, url))

    # data-cities: 허브면 소속 도시 전체, 단일 광역이면 자기 이름
    cs = cities_of(loc)
    cities_csv = ",".join(cs) if cs else loc

    # 내부링크: 같은 권역 인근 도시
    sibs = [c for c in cities_of(region) if c != loc]
    near = sibs[:6] if sibs else [n for n,_ in REGIONS if n != loc][:6]
    near_links = "".join('<a href="/%s/%s/">%s 웨딩박람회</a>' %
                         (region, c, c) if sibs else '<a href="/%s/">%s 웨딩박람회</a>'%(c,c)
                         for c in near)

    my_evs = my_evs or []
    # 개최지 카드 (이 지역 행사들의 실제 행사장에서 추출)
    _vs, _seen = [], set()
    for _e in my_evs:
        _v = EV.venue_of(_e)
        if _v and _v not in _seen:
            _seen.add(_v); _vs.append(_v)
    if not _vs: _vs = [v for v in VENUE_INFO if VENUE_INFO[v][0].find(loc) >= 0][:3]
    venue_cards = "".join(
        '<div class="vcard"><h3>%s</h3><p class="vloc">%s</p><p>%s</p><p class="vtip">%s</p></div>'
        % (esc(v), esc(VENUE_INFO[v][0]), esc(VENUE_INFO[v][1]),
           esc(VENUE_INFO[v][3] if len(VENUE_INFO[v]) > 3 else VENUE_INFO[v][2]))
        for v in _vs[:6] if v in VENUE_INFO) or \
        '<div class="vcard"><h3>%s 지역 행사장</h3><p>%s에서는 컨벤션센터와 백화점 특별행사장을 중심으로 박람회가 열립니다. 정확한 위치는 각 일정 카드에서 확인하세요.</p></div>' % (esc(loc), esc(loc))
    steps_html = "".join('<li><b>%s</b><span>%s</span></li>' % (esc(t), esc(d)) for t, d in HOW_STEPS)
    why_html = "".join('<div class="wcard"><i>%02d</i><b>%s</b><p>%s</p></div>' % (i+1, esc(t), esc(d))
                        for i, (t, d) in enumerate(WHY_US))

    static_cards = cards_html(my_evs, show_city=bool(cs),
        empty=f"{loc} 지역 일정을 준비 중입니다. 새로운 일정이 확정되면 이곳에 바로 표시됩니다.")
    ev_count = len(my_evs)
    tips_html = "".join(f"<div class='tip'><h3>{t}</h3><p>{d}</p></div>" for t,d in tips)
    caution_html = "".join(f"<li>{c}</li>" for c in cautions)
    faq = faqs_for(loc)
    faq_html = "".join(
      f"<details><summary><span class='qmark'>Q</span><span class='qtxt'>{q}</span></summary>"
      f"<div class='a'><span class='amark'>A</span><span>{a}</span></div></details>" for q,a in faq)

    lds = [ld_breadcrumb(bc), ld_faq(faq), ld_howto(loc), ld_website()]
    if my_evs: lds.append(ld_itemlist(loc, [x["name"] for x in my_evs]))

    body = f"""{header(region, "" if is_hub else loc)}
{breadcrumb_html(bc)}
<main>
 <section class="hero">
  <div class="wrap">
   <p class="eyebrow">{label} · {YEAR}년 최신</p>
   <h1>{loc} 웨딩박람회 일정</h1>
   <p class="lead">{intro} {loc}에서 열리는 웨딩박람회·결혼박람회·허니문박람회 일정과
    무료 초대권 정보를 매일 갱신해 정리합니다.</p>
   <div class="stats">
     <div><b>{ev_count}</b><span>{loc} 진행 예정</span></div>
     <div><b>{total_ev}</b><span>전국 등록 일정</span></div>
     <div><b>100%</b><span>무료 초대권</span></div>
     <div><b>{TODAY}</b><span>최근 갱신</span></div>
   </div>
  </div>
 </section>

 <section class="wrap sched-top">
  <p class="seclabel">SCHEDULE</p>
  <h2 class="sec">{loc} 웨딩박람회 최신 일정 {("("+str(ev_count)+"건)") if ev_count else ""}</h2>
  <p class="sub">모집 중인 일정만 표시됩니다. 카드를 눌러 상세 정보와 무료 초대권을 확인하세요.</p>
  <div class="cards" id="event-cards" data-cities="{cities_csv}" data-loc="{loc}">{static_cards}</div>
 </section>

 <section class="wrap">{aeo_block(loc, region)}</section>

 <section class="wrap">
  <p class="seclabel">VENUES</p>
  <h2 class="sec">{loc} 주요 박람회 개최지</h2>
  <p class="sub">자주 이용되는 행사장의 위치와 특징입니다.</p>
  <div class="venues">{venue_cards}</div>
 </section>

 <section class="wrap">
  <p class="seclabel">COMPARE</p>
  <h2 class="sec">{loc} 웨딩박람회 유형 비교</h2>
  {compare_table(loc)}
 </section>

 <section class="wrap">
  <p class="seclabel">HOW IT WORKS</p>
  <h2 class="sec">참여 방법 3단계</h2>
  <p class="sub">처음 방문하는 예비부부도 어렵지 않습니다.</p>
  <ol class="steps">{steps_html}</ol>
 </section>

 <section class="wrap">
  <p class="seclabel">CHECKPOINT</p>
  <h2 class="sec">{loc} 방문 전 준비 체크포인트</h2>
  <div class="tips">{tips_html}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">{loc} 계약 전 주의사항</h2>
  <ul class="cautions">{caution_html}</ul>
 </section>

 <section class="wrap">
  <p class="seclabel">WHY WEDDINGNOTE</p>
  <h2 class="sec">웨딩노트가 정리하는 방식</h2>
  <div class="whygrid">{why_html}</div>
 </section>

 <section class="wrap">
  <p class="seclabel">FAQ</p>
  <h2 class="sec">{loc} 웨딩박람회 자주 묻는 질문</h2>
  <div class="faq">{faq_html}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">가까운 지역 일정도 확인해 보세요</h2>
  <div class="chips near">{near_links}</div>
 </section>
</main>
{footer()}"""
    w(path + "index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)


# ── 행사 카드 정적 렌더 (검색봇이 읽는 HTML) ──────────────────────
def event_card(e, show_city=False):
    d1, d2 = EV.fmt(e["start"]), EV.fmt(e["end"])
    dates = d1 if e["start"] == e["end"] else "%s ~ %s" % (d1, EV.fmt_short(e["end"]))
    dday = ("<span class='dday'>D-%d</span>" % e["dday"]) if 0 < e["dday"] <= 30 else \
           ("<span class='dday now'>진행중</span>" if e["dday"] <= 0 else "")
    img = ('<a class="poster" href="/행사/%s/"><img src="%s" alt="%s 포스터" loading="lazy"></a>'
           % (quote(e["slug"]), esc(e["img"]), esc(e["name"]))) if e["img"] else ""
    city = ("<span class='ctag'>%s</span>" % esc(e["city"])) if show_city else ""
    ben = ("<div class='benefit'>혜택 %s</div>" % esc(e.get("benefit",""))) if e.get("benefit") else ""
    return f"""<article class="card">{img}<div class="body">
 <div class="tags"><span class="status">모집중</span>{city}{dday}</div>
 <h3><a href="/행사/{quote(e['slug'])}/">{esc(e['name'])}</a></h3>
 <div class="meta">일정 {dates}</div>
 <div class="meta">장소 {esc(e['place'])}</div>
 {ben}
 <a class="cta" href="{esc(e['link'])}" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청</a>
</div></article>"""

def cards_html(evs, show_city=False, empty="현재 모집 중인 일정이 없습니다. 새 일정이 확정되면 이곳에 표시됩니다."):
    if not evs: return '<div class="loading">%s</div>' % empty
    return "".join(event_card(e, show_city) for e in evs)

def ld_event(e):
    return json.dumps({"@context":"https://schema.org","@type":"Event",
      "name":e["name"], "startDate":e["start"].isoformat(), "endDate":e["end"].isoformat(),
      "eventStatus":"https://schema.org/EventScheduled",
      "eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
      "location":{"@type":"Place","name":e["place"],
                  "address":{"@type":"PostalAddress","addressLocality":e["city"],
                             "addressCountry":"KR","streetAddress":e["place"]}},
      "image":[e["img"]] if e["img"] else [],
      "description":"%s에서 열리는 %s 일정과 무료 초대권 안내" % (e["city"], e["name"]),
      "offers":{"@type":"Offer","price":"0","priceCurrency":"KRW",
                "availability":"https://schema.org/InStock","url":e["link"]},
      "organizer":{"@type":"Organization","name":SITE}}, ensure_ascii=False)


# ── 행사 상세 보조 함수 ─────────────────────────────────────
def map_links(place):
    q = quote(place)
    return ('<a href="https://map.naver.com/p/search/%s" target="_blank" rel="noopener">네이버 지도</a>'
            '<a href="https://map.kakao.com/?q=%s" target="_blank" rel="noopener">카카오맵</a>'
            '<a href="https://www.google.com/maps/search/?api=1&query=%s" target="_blank" rel="noopener">구글 지도</a>'
            % (q, q, q))

def district_of(place):
    m = re.search(r'([가-힣]+(?:구|시|군))\s', place + " ")
    return m.group(1) if m else ""

def location_text(e):
    d = district_of(e["place"])
    desc = DISTRICT_DESC.get(d, "")
    t = "%s 일대에서 진행됩니다." % e["place"]
    if d: t += " 행정구역상 %s에 해당합니다." % d
    if desc: t += " %s입니다." % desc
    return t

MONTH_NOTE = {
 1:"연초 결혼 준비를 시작하는 예비부부가 많이 찾는 시기입니다.",
 2:"봄 예식을 앞두고 막바지 준비를 정리하기 좋은 시기입니다.",
 3:"봄 성수기를 앞두고 참여 업체가 늘어나는 시기입니다.",
 4:"봄 예식 시즌과 맞물려 규모가 큰 박람회가 몰리는 시기입니다.",
 5:"가을 예식을 준비하는 예비부부의 방문이 많은 시기입니다.",
 6:"여름 비수기를 앞두고 혜택이 강화되는 경우가 많습니다.",
 7:"여름 휴가철 전 준비를 마무리하기 좋은 시기입니다.",
 8:"가을 성수기 예식을 준비하기에 적절한 시기입니다.",
 9:"가을 예식 시즌과 함께 참여 업체가 가장 많아지는 시기입니다.",
 10:"내년 봄 예식을 준비하는 예비부부가 많이 찾습니다.",
 11:"연말 프로모션과 함께 혜택이 커지는 시기입니다.",
 12:"연말·연초 계약 혜택을 노리기 좋은 시기입니다.",
}
def intro_text(e):
    d1 = EV.fmt(e["start"]); d2 = EV.fmt(e["end"])
    span = d1 if e["start"] == e["end"] else "%s ~ %s" % (d1, d2)
    t = "%s 진행되는 「%s」의 일정과 정보를 정리했습니다. " % (span, e["name"])
    t += MONTH_NOTE.get(e["start"].month, "") + " "
    t += "웨딩홀과 스튜디오·드레스·메이크업, 예물과 혼수, 신혼여행까지 여러 업체를 한자리에서 상담할 수 있습니다."
    if e.get("benefit"): t += " 이번 회차에는 %s 혜택이 안내되고 있습니다." % e["benefit"]
    return t

def is_weekday(e):
    return e["start"].weekday() < 5 and e["start"] == e["end"]

# ── 개별 행사 상세 페이지 ────────────────────────────────────────
def event_page(e, same_city, all_evs=None):
    path = "/행사/%s/" % e["slug"]; url = DOMAIN + path
    region = region_of_city(e["city"])
    d1, d2 = EV.fmt(e["start"]), EV.fmt(e["end"])
    dates = d1 if e["start"] == e["end"] else "%s ~ %s" % (d1, d2)
    title = "%s 일정 %s | 무료초대권 신청 - %s 웨딩박람회" % (e["name"], EV.fmt_short(e["start"]), e["city"])
    desc = "%s은 %s %s에서 열립니다. 무료 초대권 신청과 웨딩홀·스드메 상담 정보를 확인하세요." % (
        e["name"], dates, e["place"])
    kw = "%s, %s 웨딩박람회, %s 일정, %s 무료초대권, %s결혼박람회" % (
        e["name"], e["city"], e["name"], e["name"], e["city"])
    bc = [("홈", DOMAIN+"/"), (region, DOMAIN+"/%s/"%region)]
    if e["city"] != region: bc.append((e["city"], DOMAIN+"/%s/%s/"%(region, e["city"])))
    bc.append((e["name"], url))
    others = [x for x in same_city if x["slug"] != e["slug"]][:6]
    rel = "".join('<li><a href="/행사/%s/">%s <span>%s</span></a></li>'
                  % (quote(x["slug"]), esc(x["name"]), EV.fmt_short(x["start"])) for x in others)
    _wk = []
    for x in (all_evs or []):
        if x["slug"] == e["slug"] or x["city"] == e["city"]: continue
        if abs((x["start"] - e["start"]).days) <= 3: _wk.append(x)
    week_rel = "".join('<li><a href="/행사/%s/">%s <span>%s · %s</span></a></li>'
                       % (quote(x["slug"]), esc(x["name"]), esc(x["city"]), EV.fmt_short(x["start"]))
                       for x in _wk[:6])
    _wd = is_weekday(e)
    faq = [
      ("%s은 언제 열리나요?" % e["name"],
       "%s에 진행됩니다. %s" % (dates,
         "평일 일정이라 비교적 한산하게 부스를 둘러볼 수 있습니다." if _wd
         else "주말 일정이라 참여 업체와 사은품이 많은 편이며, 오전 방문이 대기가 짧습니다.")),
      ("행사장은 어디인가요?",
       "%s에서 진행됩니다. %s" % (e["place"],
         DISTRICT_DESC.get(district_of(e["place"]), "방문 전 주차 여건과 대중교통 동선을 확인하면 좋습니다.") + ("입니다." if DISTRICT_DESC.get(district_of(e["place"])) else ""))),
      ("무료 초대권은 어떻게 받나요?",
       "이 페이지의 「무료 초대권 신청하기」를 누르면 운영사 공식 신청 페이지로 이동합니다. 이름과 연락처를 남기면 초대권이 발급되며 별도 비용은 없습니다."),
      ("초대권으로 어떤 혜택을 받을 수 있나요?",
       (("이번 회차 안내 혜택은 %s입니다. " % e["benefit"]) if e.get("benefit") else "") +
       "일반적으로 현장 계약 시 스드메 패키지 할인, 예식장 식대 혜택, 혼수 견적 비교, 방문 사은품 등이 제공됩니다. 혜택은 회차와 업체에 따라 달라집니다."),
      ("예식 날짜가 아직 정해지지 않았어도 방문할 수 있나요?",
       "네, 가능합니다. 박람회는 정보 수집 단계에서 방문하는 분이 가장 많습니다. 예식 예정 월만 대략 정해 두어도 견적 비교와 식장 답사에 충분히 활용할 수 있습니다."),
      ("현장에서 꼭 계약해야 하나요?",
       "아닙니다. 견적만 받고 비교한 뒤 결정해도 됩니다. 다만 인기 예식장의 날짜는 조기 마감될 수 있어 일정 확인은 서두르는 편이 좋습니다."),
    ]
    faq_html = "".join("<details><summary><span class='qmark'>Q</span><span class='qtxt'>%s</span></summary>"
                       "<div class='a'><span class='amark'>A</span><span>%s</span></div></details>" % (q,a) for q,a in faq)
    lds = [ld_event(e), ld_breadcrumb(bc), ld_faq(faq), ld_howto(e["city"])]
    hero_img = ('<div class="ephoto"><img src="%s" alt="%s 포스터" loading="lazy"></div>'
                % (esc(e["img"]), esc(e["name"]))) if e["img"] else ""
    body = f"""{header(region, "" if e["city"]==region else e["city"])}
{breadcrumb_html(bc)}
<main>
 <section class="hero">
  <div class="wrap">
   <p class="eyebrow">{esc(e['city'])} 웨딩박람회 · 모집중</p>
   <h1>{esc(e['name'])}</h1>
   <table class="factsheet">
    <tr><th>행사일</th><td>{dates}</td></tr>
    <tr><th>장소</th><td>{esc(e['place'])}</td></tr>
    <tr><th>지역</th><td><a href="/{region}/{'' if e['city']==region else e['city']+'/'}">{esc(e['city'])} 웨딩박람회 전체 일정</a></td></tr>
    <tr><th>입장</th><td>무료 초대권 사전 신청</td></tr>
    {("<tr><th>혜택</th><td>"+esc(e.get("benefit",""))+"</td></tr>") if e.get("benefit") else ""}
   </table>
   <a class="btn big" href="{esc(e['link'])}" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청하기</a>
  </div>
 </section>
 {('<section class="wrap">'+hero_img+'</section>') if hero_img else ''}
 <section class="wrap">
  <div class="aeo">
   <h2>{esc(e['name'])}, 어떻게 신청하나요?</h2>
   <p class="ans">{esc(e['name'])}은 <b>{dates}</b> {esc(e['place'])}에서 열립니다.
    입장은 무료 초대권 사전 신청으로 진행되며, 현장에서 웨딩홀과 스드메, 예물·혼수, 신혼여행 상담을 한 번에 받을 수 있습니다.</p>
   <p class="ans-sub"><b>신청 방법</b></p>
   <ol><li>위 무료 초대권 신청 버튼을 누릅니다.</li>
       <li>이름과 연락처, 희망 방문 시간을 남깁니다.</li>
       <li>예산 상한과 희망 예식 날짜를 정리해 커플이 함께 방문합니다.</li></ol>
   <p class="pnote">※ 일정과 혜택은 주최 측 사정에 따라 변경될 수 있습니다.</p>
  </div>
 </section>
 <section class="wrap">
  <p class="seclabel">ABOUT</p>
  <h2 class="sec">{esc(e['name'])} 안내</h2>
  <p class="para">{esc(intro_text(e))}</p>
 </section>

 <section class="wrap">
  <p class="seclabel">LOCATION</p>
  <h2 class="sec">위치 안내</h2>
  <p class="para">{esc(location_text(e))}</p>
  <p class="sub">방문 전 정확한 위치를 지도에서 확인해 보세요.</p>
  <div class="maplinks">{map_links(e['place'])}</div>
 </section>

 <section class="wrap">
  <p class="seclabel">CHECKPOINT</p>
  <h2 class="sec">방문 전 체크포인트</h2>
  <ul class="cautions">
   <li>보증 인원과 식대 부가세 포함 여부를 확인하세요.</li>
   <li>촬영 원본·수정본 비용과 드레스 피팅비·헬퍼비 포함 여부를 물어보세요.</li>
   <li>구두로 약속받은 사은품은 계약서 특약란에 기재해야 합니다.</li>
   <li>취소 시점별 위약금과 예식일 변경 규정을 미리 확인하세요.</li>
  </ul>
 </section>
 {('<section class="wrap"><p class="seclabel">NEARBY</p><h2 class="sec">'+esc(e['city'])+' 다른 웨딩박람회 일정</h2><ul class="rellist">'+rel+'</ul></section>') if rel else ''}
 {('<section class="wrap"><p class="seclabel">SAME WEEK</p><h2 class="sec">같은 주 다른 지역 박람회</h2><ul class="rellist">'+week_rel+'</ul></section>') if week_rel else ''}

 <section class="wrap">
  <div class="applybox">
   <h2>무료 초대권 신청</h2>
   <p>{esc(e['name'])}는 입장료 없이 무료 초대권만으로 입장할 수 있습니다.
      현장 계약 의무는 없으며, 정보 수집 목적으로 방문하셔도 좋습니다.</p>
   <a class="btn big" href="{esc(e['link'])}" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청 페이지로 이동</a>
  </div>
 </section>
 <section class="wrap"><p class="seclabel">FAQ</p><h2 class="sec">자주 묻는 질문</h2><div class="faq">{faq_html}</div></section>
</main>
{footer()}"""
    w(path+"index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)

# ── 행사장별 페이지 ─────────────────────────────────────────────
def venue_page(venue, evs, all_venues=None):
    slug = EV.slugify(venue)
    path = "/행사장/%s/" % slug; url = DOMAIN + path
    title = "%s 웨딩박람회 일정 %d건 | 무료초대권 - %s" % (venue, len(evs), SITE)
    desc = "%s에서 열리는 웨딩박람회 일정 %d건을 정리했습니다. 날짜와 장소, 무료 초대권 신청 정보를 확인하세요." % (venue, len(evs))
    kw = "%s 웨딩박람회, %s 결혼박람회, %s 웨딩박람회 일정, %s 무료초대권" % (venue, venue, venue, venue)
    bc = [("홈",DOMAIN+"/"),("행사장",DOMAIN+"/행사장/"),(venue,url)]
    info = VENUE_INFO.get(venue)
    loc_txt = info[0] if info else "전국"
    desc_txt = info[1] if info else ("%s에서 열리는 웨딩박람회 일정을 모았습니다. 참여 업체와 규모는 회차마다 다르므로 아래 일정에서 확인하세요." % venue)
    park_txt = info[2] if info else "방문 전 주차 여건과 대중교통 동선을 확인하면 좋습니다."
    other_venues = "".join('<a href="/행사장/%s/">%s</a>' % (quote(EV.slugify(v)), esc(v))
                           for v in (all_venues or []) if v != venue)
    faqv = [("%s 웨딩박람회는 얼마나 자주 열리나요?" % venue,
             "%s에서는 주최사에 따라 매주 또는 격주로 박람회가 열립니다. 현재 확인된 일정은 %d건입니다." % (venue, len(evs))),
            ("입장료가 있나요?", "무료 초대권을 사전 신청하면 무료로 입장할 수 있습니다."),
            ("%s 방문 시 주차는 어떤가요?" % venue, park_txt)]
    faqv_html = "".join("<details><summary><span class='qmark'>Q</span><span class='qtxt'>%s</span></summary>"
                        "<div class='a'><span class='amark'>A</span><span>%s</span></div></details>" % (q,a)
                        for q,a in faqv)
    lds = [ld_breadcrumb(bc), ld_itemlist(venue, [e["name"] for e in evs]), ld_faq(faqv)]
    body = f"""{header()}
{breadcrumb_html(bc)}
<main>
 <section class="hero"><div class="wrap">
  <p class="eyebrow">행사장별 일정 · {loc_txt}</p>
  <h1>{esc(venue)} 웨딩박람회 일정</h1>
  <p class="lead">{esc(venue)}에서 열리는 웨딩박람회 {len(evs)}건입니다. 날짜를 확인하고 무료 초대권을 신청하세요.</p>
 </div></section>
 <section class="wrap"><div class="aeo">
  <h2>{esc(venue)}에서는 어떤 웨딩박람회가 열리나요?</h2>
  <p class="ans">{desc_txt}</p>
  <p class="ans-sub"><b>방문 전 알아두면 좋은 점</b></p>
  <ol><li>{park_txt}</li>
      <li>주말 오전 방문이 대기가 짧고 상담이 여유롭습니다.</li>
      <li>무료 초대권을 미리 신청하면 우선 상담과 방문 선물 혜택을 받을 수 있습니다.</li></ol>
  <p class="pnote">※ 일정과 참여 업체는 주최 측 사정에 따라 변경될 수 있습니다.</p>
 </div></section>
 <section class="wrap">
  <p class="seclabel">SCHEDULE</p>
  <h2 class="sec">{esc(venue)} 진행 예정 일정 ({len(evs)}건)</h2>
  <div class="cards">{cards_html(evs, show_city=True)}</div>
 </section>
 <section class="wrap">
  <p class="seclabel">CHECKPOINT</p>
  <h2 class="sec">{esc(venue)} 방문 체크포인트</h2>
  <ul class="cautions">
   <li>보증 인원과 식대 부가세 포함 여부를 확인하세요.</li>
   <li>촬영 원본·수정본 비용과 드레스 피팅비 포함 여부를 물어보세요.</li>
   <li>구두 약속은 계약서 특약란에 기재해야 합니다.</li>
   <li>여러 박람회를 비교한 뒤 결정해도 늦지 않습니다.</li>
  </ul>
 </section>
 <section class="wrap">
  <p class="seclabel">FAQ</p>
  <h2 class="sec">{esc(venue)} 자주 묻는 질문</h2>
  <div class="faq">{faqv_html}</div>
 </section>
 <section class="wrap">
  <p class="seclabel">OTHER VENUES</p>
  <h2 class="sec">다른 행사장 일정</h2>
  <div class="chips near">{other_venues}</div>
 </section>
</main>{footer()}"""
    w(path+"index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)

def venue_index(vmap):
    path="/행사장/"; url=DOMAIN+path
    items = "".join('<a class="gcard" href="/행사장/%s/"><b>%s</b><span>진행 예정 %d건</span></a>'
                    % (quote(EV.slugify(v)), esc(v), len(es))
                    for v, es in sorted(vmap.items(), key=lambda x:-len(x[1])))
    bc=[("홈",DOMAIN+"/"),("행사장",url)]
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><p class="eyebrow">행사장</p>
      <h1>전국 주요 웨딩박람회장</h1>
      <p class="lead">코엑스·SETEC·킨텍스·벡스코 등 주요 행사장별로 일정을 모아 확인할 수 있습니다.</p></div></section>
     <section class="wrap"><div class="guidegrid">{items}</div></section></main>{footer()}"""
    w(path+"index.html", head("전국 주요 웨딩박람회장 일정 | "+SITE,
      "코엑스, SETEC, 킨텍스, 벡스코, 송도컨벤시아 등 전국 주요 웨딩박람회장별 일정을 모았습니다.",
      "웨딩박람회장, 코엑스 웨딩박람회, 킨텍스 웨딩박람회, SETEC 웨딩박람회, 벡스코 웨딩박람회", url,
      [ld_breadcrumb(bc)]) + body)
    URLS.append(url)

# ── 이번주 / 월별 페이지 ────────────────────────────────────────
def week_page(evs):
    path="/이번주-웨딩박람회/"; url=DOMAIN+path
    mon = TODAY_D - datetime.timedelta(days=TODAY_D.weekday())
    sun = mon + datetime.timedelta(days=13)
    cur = [e for e in evs if e["start"] <= sun and e["end"] >= TODAY_D]
    title = "이번주 웨딩박람회 일정 %d건 (%s~%s) | %s" % (len(cur), EV.fmt_short(mon), EV.fmt_short(sun), SITE)
    desc = "이번주와 다음주 전국에서 열리는 웨딩박람회 %d건을 모았습니다. 지역별 일정과 무료 초대권 신청 정보를 확인하세요." % len(cur)
    bc=[("홈",DOMAIN+"/"),("이번주 웨딩박람회",url)]
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><p class="eyebrow">{EV.fmt_short(mon)} ~ {EV.fmt_short(sun)}</p>
      <h1>이번주 웨딩박람회 일정</h1>
      <p class="lead">지금 신청 가능한 전국 웨딩박람회 {len(cur)}건입니다. 주말 방문 계획을 세워 보세요.</p></div></section>
     <section class="wrap"><div class="cards">{cards_html(cur, show_city=True, empty="이번주 예정된 일정이 없습니다.")}</div></section>
    </main>{footer()}"""
    w(path+"index.html", head(title, desc,
      "이번주 웨딩박람회, 주말 웨딩박람회, 웨딩박람회 일정, 무료초대권", url,
      [ld_breadcrumb(bc), ld_itemlist("이번주 웨딩박람회", [e["name"] for e in cur])]) + body)
    URLS.append(url)

MON_KO = {1:"1월",2:"2월",3:"3월",4:"4월",5:"5월",6:"6월",7:"7월",8:"8월",9:"9월",10:"10월",11:"11월",12:"12월"}
def month_page(ym, evs, all_months):
    y, m = int(ym[:4]), int(ym[5:7])
    path="/일정/%s/" % ym; url=DOMAIN+path
    label = "%d년 %s" % (y, MON_KO[m])
    title = "%s 웨딩박람회 일정 %d건 총정리 | 무료초대권 - %s" % (label, len(evs), SITE)
    desc = "%s에 열리는 전국 웨딩박람회 %d건의 날짜와 장소를 정리했습니다. 지역별 일정과 무료 초대권 신청 정보를 확인하세요." % (label, len(evs))
    kw = "%s 웨딩박람회, %s 웨딩박람회 일정, %d년 웨딩박람회, 웨딩박람회 무료초대권" % (label, label, y)
    bc=[("홈",DOMAIN+"/"),("월별 일정",DOMAIN+"/일정/"),(label,url)]
    nav = "".join('<a class="%s" href="/일정/%s/">%s</a>' %
                  ("on" if x==ym else "", x, "%d년 %s"%(int(x[:4]), MON_KO[int(x[5:7])]))
                  for x in all_months)
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><p class="eyebrow">월별 일정</p>
      <h1>{label} 웨딩박람회 일정</h1>
      <p class="lead">{label}에 전국에서 열리는 웨딩박람회 {len(evs)}건입니다.</p>
      <div class="monthnav">{nav}</div></div></section>
     <section class="wrap"><div class="cards">{cards_html(evs, show_city=True)}</div></section>
    </main>{footer()}"""
    w(path+"index.html", head(title, desc, kw, url,
      [ld_breadcrumb(bc), ld_itemlist(label+" 웨딩박람회", [e["name"] for e in evs])]) + body)
    URLS.append(url)

def month_index(mmap):
    path="/일정/"; url=DOMAIN+path
    items="".join('<a class="gcard" href="/일정/%s/"><b>%d년 %s</b><span>박람회 %d건</span></a>'
                  %(ym,int(ym[:4]),MON_KO[int(ym[5:7])],len(es)) for ym,es in sorted(mmap.items()))
    bc=[("홈",DOMAIN+"/"),("월별 일정",url)]
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><p class="eyebrow">달력</p>
      <h1>월별 웨딩박람회 일정</h1>
      <p class="lead">원하는 달을 선택하면 그 달에 열리는 전국 박람회를 모아 볼 수 있습니다.</p></div></section>
     <section class="wrap"><div class="guidegrid">{items}</div></section></main>{footer()}"""
    w(path+"index.html", head("월별 웨딩박람회 일정 달력 | "+SITE,
      "월별로 전국 웨딩박람회 일정을 모아 확인할 수 있습니다. 원하는 달을 선택하세요.",
      "웨딩박람회 달력, 월별 웨딩박람회, 웨딩박람회 일정표", url, [ld_breadcrumb(bc)]) + body)
    URLS.append(url)

# ── 홈 ──────────────────────────────────────────────────────────
def home(EVS=None):
    url = DOMAIN + "/"
    title = f"{YEAR} 전국 웨딩박람회 일정 총정리 | 무료초대권 신청 - {SITE}"
    desc = (f"{YEAR}년 전국 웨딩박람회·결혼박람회 일정을 지역별로 매일 정리합니다. "
            f"서울·경기·부산 등 56개 지역 일정과 무료 초대권 신청, 웨딩홀·스드메 비교 가이드를 제공합니다.")
    kw = "웨딩박람회일정, 전국웨딩박람회, 결혼박람회일정, 웨딩박람회 무료초대권, 스드메 견적, 허니문박람회, 웨딩홀 비교"
    EVS = EVS or []
    _sun = TODAY_D + datetime.timedelta(days=10)
    week = [e for e in EVS if e["start"] <= _sun and e["end"] >= TODAY_D][:6]
    week_cards = cards_html(week, show_city=True, empty="이번주 예정된 일정이 없습니다.")
    blocks = ""
    for n, cs in REGIONS:
        inner = "".join('<a href="/%s/%s/">%s</a>'%(n,c,c) for c in cs) or \
                '<a href="/%s/">%s 전체</a>'%(n,n)
        blocks += f"""<div class="regionbox">
          <h3><a href="/{n}/">{n} 웨딩박람회</a></h3><div class="chips">{inner}</div></div>"""
    faq = [
      ("웨딩박람회는 얼마나 자주 열리나요?",
       "전국적으로 주말마다 열립니다. 지역과 규모에 따라 1주에서 4주 간격으로 개최되며 이 사이트에서 지역별 최신 일정을 확인할 수 있습니다."),
      ("무료 초대권은 어떻게 신청하나요?",
       "원하는 지역 페이지에서 박람회를 고른 뒤 초대권 신청 버튼을 눌러 이름과 연락처를 남기면 됩니다. 대부분 무료이며 사전 예약자 혜택이 있습니다."),
      ("박람회에 가면 무엇을 할 수 있나요?",
       "웨딩홀 잔여 날짜 확인부터 스튜디오·드레스·메이크업 비교, 예물과 혼수, 신혼여행 상담까지 한자리에서 진행할 수 있습니다."),
    ]
    lds = [ld_website(), ld_faq(faq),
           ld_breadcrumb([("홈", DOMAIN+"/")])]
    faq_html = "".join(
      f"<details><summary><span class='qmark'>Q</span><span class='qtxt'>{q}</span></summary>"
      f"<div class='a'><span class='amark'>A</span><span>{a}</span></div></details>" for q,a in faq)
    body = f"""{header()}
<main>
 <section class="hero home">
  <div class="wrap">
   <p class="eyebrow">{YEAR}년 · 전국 56개 지역</p>
   <h1>전국 웨딩박람회 일정<br>한 곳에서 확인하세요</h1>
   <p class="lead">지역을 선택하면 그 지역에서 열리는 웨딩박람회·결혼박람회·허니문박람회 일정과
    무료 초대권 정보를 바로 볼 수 있습니다. 일정은 매일 자동으로 갱신됩니다.</p>
   <div class="badges"><span>매일 자동 갱신</span><span>전국 56개 지역</span><span>무료 초대권</span></div>
  </div>
 </section>

 <section class="wrap">
  <div class="aeo">
   <h2>웨딩박람회, 언제 가는 게 가장 좋을까요?</h2>
   <p class="ans">예식 예정일 기준 <b>6개월에서 1년 전</b>이 가장 적당합니다. 이 시기에 방문해야
    원하는 날짜의 웨딩홀을 선점하고 스드메 일정까지 여유 있게 잡을 수 있습니다.</p>
   <p class="ans-sub"><b>이용 방법</b></p>
   <ol><li>아래에서 방문할 지역을 선택합니다.</li>
       <li>지역 페이지에서 일정과 장소를 확인합니다.</li>
       <li>무료 초대권을 신청하고 커플이 함께 방문합니다.</li></ol>
   <p class="pnote">※ 일정과 혜택은 주최 측 사정에 따라 변경될 수 있습니다.</p>
  </div>
 </section>

 <section class="wrap">
  <p class="seclabel">THIS WEEK</p>
  <h2 class="sec">이번주 열리는 웨딩박람회</h2>
  <p class="sub">지금 신청 가능한 일정입니다. <a href="/이번주-웨딩박람회/">전체 보기</a></p>
  <div class="cards">{week_cards}</div>
 </section>

 <section class="wrap">
  <p class="seclabel">REGIONS</p>
  <h2 class="sec">지역별 웨딩박람회 일정</h2>
  <p class="sub">원하는 지역을 선택하세요.</p>
  <div class="regiongrid">{blocks}</div>
 </section>

 <section class="wrap">
  <p class="seclabel">GUIDE</p>
  <h2 class="sec">결혼준비 가이드</h2>
  <div class="guidegrid">
   <a class="gcard" href="/가이드/웨딩박람회-활용법/"><b>웨딩박람회 200% 활용법</b>
     <span>방문 순서와 상담 요령, 놓치기 쉬운 혜택까지</span></a>
   <a class="gcard" href="/가이드/스드메-견적-비교/"><b>스드메 견적 비교 요령</b>
     <span>같은 금액도 구성에 따라 달라지는 이유</span></a>
   <a class="gcard" href="/가이드/결혼준비-체크리스트/"><b>결혼준비 체크리스트</b>
     <span>순서대로 따라가는 준비 항목 정리</span></a>
  </div>
 </section>

 <section class="wrap">
  <p class="seclabel">FAQ</p>
  <h2 class="sec">자주 묻는 질문</h2>
  <div class="faq">{faq_html}</div>
 </section>
</main>
{footer()}"""
    w("index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)

print("gen.py loaded")

# ── 가이드(아티클) ───────────────────────────────────────────────
ART_BODY = {
"웨딩박람회-활용법": [
 ("박람회 하루를 어떻게 쓰면 좋을까","도착하면 먼저 전체 부스 배치도를 확인하고 웨딩홀 → 스드메 → 예물·혼수 → 허니문 순서로 동선을 잡으세요. 예식 날짜가 확정돼야 나머지 일정이 정리되기 때문에 웨딩홀 상담을 가장 먼저 하는 것이 효율적입니다."),
 ("상담 전에 정리해 갈 것","총 예산 상한선, 희망 예식 월과 요일, 예상 하객 수, 선호 지역 이 네 가지만 메모해 가도 상담 속도가 크게 빨라집니다. 상담사가 조건에 맞는 곳만 추려 주기 때문입니다."),
 ("현장에서 꼭 물어볼 질문","보증 인원을 조정할 수 있는지, 식대에 부가세가 포함인지, 대관료와 꽃 장식이 기본에 들어 있는지, 주차는 몇 대까지 지원되는지를 반드시 확인하세요."),
 ("사은품보다 중요한 것","눈에 띄는 사은품보다 계약 조건이 훨씬 중요합니다. 같은 금액이라도 촬영 원본 제공 여부나 드레스 벌수에 따라 실제 가치가 크게 달라집니다."),
 ("당일 계약을 미뤄도 되는 이유","대부분의 혜택은 다음 회차에도 비슷하게 제공됩니다. 여러 곳을 비교한 뒤 결정해도 늦지 않으며, 다만 인기 날짜는 조기 마감될 수 있으니 일정만 먼저 확인해 두세요."),
],
"스드메-견적-비교": [
 ("스드메 견적이 업체마다 다른 이유","스드메는 스튜디오·드레스·메이크업을 묶은 패키지라 구성 방식에 따라 총액이 달라집니다. 같은 가격이라도 촬영 컷수와 드레스 벌수가 다르면 실제 가치는 크게 차이 납니다."),
 ("반드시 확인할 항목 다섯 가지","촬영 원본과 수정본 제공 범위, 드레스 착용 벌수와 등급, 헬퍼비와 피팅비 포함 여부, 메이크업 담당자 지정 가능 여부, 앨범과 액자 구성입니다."),
 ("추가금이 붙는 지점","주말 촬영 할증, 수입 드레스 업그레이드, 원본 데이터 구매, 헬퍼 교통비가 대표적입니다. 견적서에 포함으로 적혀 있는지 항목별로 확인하세요."),
 ("비교표를 만들어 보세요","업체명, 총액, 촬영 컷수, 드레스 벌수, 추가금 항목을 표로 정리하면 어느 곳이 실제로 합리적인지 한눈에 보입니다. 상담마다 견적서를 사진으로 남겨 두면 편합니다."),
 ("계약서에 남겨야 할 것","구두로 약속받은 업그레이드나 서비스는 반드시 특약란에 문구로 기재해야 합니다. 취소 시 환불 규정과 일정 변경 가능 횟수도 함께 확인하세요."),
],
"결혼준비-체크리스트": [
 ("12개월 전 · 큰 틀 정하기","예산 상한선과 희망 예식 시기를 정하고 양가 상견례 일정을 잡습니다. 이 시기에 웨딩박람회를 방문하면 전체 시세를 파악하기 좋습니다."),
 ("9개월 전 · 예식장 확정","하객 규모와 예산에 맞는 웨딩홀을 두세 곳 비교한 뒤 계약합니다. 보증 인원과 식대 조건이 총액을 좌우하므로 꼼꼼히 확인하세요."),
 ("6개월 전 · 스드메 계약","촬영 콘셉트를 정하고 스튜디오·드레스·메이크업을 계약합니다. 원본 제공과 추가금 조건을 반드시 확인해야 합니다."),
 ("3개월 전 · 예물과 혼수","예물과 예단, 가전·가구를 준비합니다. 배송과 설치 일정이 입주일과 맞는지 확인이 필요합니다."),
 ("1개월 전 · 최종 점검","청첩장 발송, 신혼여행 준비물, 예식 당일 동선과 진행 순서를 확정합니다. 잔금 일정과 환불 규정도 다시 확인해 두세요."),
],
}

def article_page(slug, title_ko, kw):
    path = "/가이드/%s/" % slug
    url = DOMAIN + path
    secs = ART_BODY[slug]
    title = f"{title_ko} | {SITE}"
    desc = secs[0][1][:78]
    bc = [("홈",DOMAIN+"/"),("결혼준비 가이드",DOMAIN+"/가이드/"),(title_ko,url)]
    faq = [(q, a) for q,a in secs[:3]]
    lds = [ld_breadcrumb(bc), ld_faq(faq),
      json.dumps({"@context":"https://schema.org","@type":"Article","headline":title_ko,
        "inLanguage":"ko-KR","datePublished":"%s-01-15"%YEAR,"dateModified":TODAY,
        "author":{"@type":"Organization","name":"에이치에스컴퍼니"},
        "publisher":{"@type":"Organization","name":SITE}}, ensure_ascii=False)]
    inner = "".join(f"<h2 class='sec'>{h}</h2><p class='para'>{p}</p>" for h,p in secs)
    body = f"""{header()}
{breadcrumb_html(bc)}
<main>
 <section class="hero"><div class="wrap">
   <p class="eyebrow">결혼준비 가이드</p><h1>{title_ko}</h1></div></section>
 <section class="wrap article">{inner}
   <div class="cta-box"><b>우리 지역 웨딩박람회 일정이 궁금하다면</b>
     <a class="btn" href="/">지역별 일정 보기</a></div>
 </section>
</main>
{footer()}"""
    w(path+"index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)

def guide_index():
    path="/가이드/"; url=DOMAIN+path
    items = "".join(f'<a class="gcard" href="/가이드/{s}/"><b>{t}</b><span>{ART_BODY[s][0][1][:60]}…</span></a>'
                    for s,t,_ in ARTICLES)
    bc=[("홈",DOMAIN+"/"),("결혼준비 가이드",url)]
    body = f"""{header()}
{breadcrumb_html(bc)}
<main><section class="hero"><div class="wrap"><p class="eyebrow">가이드</p>
 <h1>결혼준비 가이드</h1><p class="lead">웨딩박람회 활용법부터 스드메 견적 비교, 준비 순서까지 정리했습니다.</p></div></section>
<section class="wrap"><div class="guidegrid">{items}</div></section></main>{footer()}"""
    w(path+"index.html", head("결혼준비 가이드 | "+SITE,
        "웨딩박람회 활용법과 스드메 견적 비교, 결혼준비 체크리스트를 정리한 가이드 모음입니다.",
        "결혼준비 가이드, 웨딩박람회 활용법, 스드메 견적, 결혼준비 체크리스트", url,
        [ld_breadcrumb(bc)]) + body)
    URLS.append(url)

def apply_page():
    path="/초대권-신청/"; url=DOMAIN+path
    opts = "".join("<option>%s</option>"%n for n,_ in REGIONS)
    bc=[("홈",DOMAIN+"/"),("무료 초대권 신청",url)]
    body = f"""{header()}
{breadcrumb_html(bc)}
<main><section class="hero"><div class="wrap"><p class="eyebrow">무료</p>
  <h1>웨딩박람회 무료 초대권 신청</h1>
  <p class="lead">희망 지역과 일정을 남겨 주시면 조건에 맞는 박람회 정보를 안내해 드립니다.</p></div></section>
<section class="wrap">
 <form class="formbox" name="apply" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="/신청완료/">
  <input type="hidden" name="form-name" value="apply">
  <p class="hp"><label>이 칸은 비워두세요 <input name="bot-field"></label></p>
  <label>이름</label><input name="name" required placeholder="성함">
  <label>연락처</label><input name="phone" required placeholder="010-0000-0000">
  <label>희망 지역</label><select name="region">{opts}</select>
  <label>희망 일정 / 문의</label><textarea name="memo" rows="3" placeholder="예: 9월 초, 강남권 희망"></textarea>
  <div class="agree"><input type="checkbox" id="ag" required>
    <label for="ag">개인정보 수집·이용(신청 접수 및 방문 안내 목적)에 동의합니다.
      <a href="/개인정보처리방침/">개인정보처리방침</a></label></div>
  <button type="submit">무료 초대권 신청하기</button>
 </form></section></main>{footer()}"""
    w(path+"index.html", head("웨딩박람회 무료 초대권 신청 | "+SITE,
      "웨딩박람회 무료 초대권을 신청하세요. 희망 지역과 일정을 남기면 담당자가 방문 안내를 드립니다.",
      "웨딩박람회 초대권, 무료초대권 신청, 결혼박람회 사전예약", url, [ld_breadcrumb(bc)]) + body)
    URLS.append(url)

def thanks_page():
    path="/신청완료/"
    body = f"""{header()}<main><section class="hero"><div class="wrap">
      <h1>신청이 접수되었습니다</h1>
      <p class="lead">담당자가 순차적으로 연락드립니다. 그동안 다른 지역 일정도 살펴보세요.</p>
      <a class="btn" href="/">지역별 일정 보기</a></div></section></main>{footer()}"""
    w(path+"index.html", head("신청 완료 | "+SITE, "초대권 신청이 접수되었습니다.",
        "초대권 신청 완료", DOMAIN+path) .replace('content="index,follow','content="noindex,follow') + body)

def privacy_page():
    path="/개인정보처리방침/"; url=DOMAIN+path
    bc=[("홈",DOMAIN+"/"),("개인정보처리방침",url)]
    secs=[("수집하는 개인정보 항목","이름, 연락처, 희망 지역 및 일정 등 신청 시 입력한 정보를 수집합니다."),
     ("수집 및 이용 목적","웨딩박람회 초대권 신청 접수와 방문 안내, 문의 응대를 위해 이용합니다."),
     ("보유 및 이용 기간","이용 목적 달성 후 지체 없이 파기합니다. 관계 법령에 따라 보존이 필요한 경우 해당 기간 동안 보관합니다."),
     ("제3자 제공","이용자의 동의 없이 제3자에게 제공하지 않습니다. 다만 신청한 박람회 주최사의 방문 안내를 위해 필요한 범위에서 제공될 수 있습니다."),
     ("이용자의 권리","이용자는 언제든지 자신의 개인정보 열람, 정정, 삭제, 처리정지를 요구할 수 있습니다."),
     ("문의처","개인정보 관련 문의는 사이트 내 신청 양식을 통해 접수해 주시기 바랍니다.")]
    inner="".join(f"<h2 class='sec'>{h}</h2><p class='para'>{p}</p>" for h,p in secs)
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><h1>개인정보처리방침</h1></div></section>
     <section class="wrap article">{inner}<p class="sub">본 방침은 {TODAY}부터 적용됩니다.</p></section></main>{footer()}"""
    w(path+"index.html", head("개인정보처리방침 | "+SITE,"개인정보 수집 이용 목적과 보유 기간을 안내합니다.",
      "개인정보처리방침", url, [ld_breadcrumb(bc)]) + body)
    URLS.append(url)

# ── 실행 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
    # 정적 파일(css/js/favicon 등) 복사
    SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    if os.path.isdir(SRC):
        for root, dirs, files in os.walk(SRC):
            rel = os.path.relpath(root, SRC)
            dst = OUT if rel == "." else os.path.join(OUT, rel)
            os.makedirs(dst, exist_ok=True)
            for f in files: shutil.copy2(os.path.join(root, f), os.path.join(dst, f))
        print("  정적 파일 복사 완료")
    print("행사 데이터 로드…")
    EVS = EV.load(refresh=True)
    print("  replyalba(시트): %d건" % len(EVS))

    # cpaad 보완 — 시트에 없는 행사만 추가 (넷리파이 빌드 서버에서 수집)
    try:
        import datetime as _dt
        for r in CP.merge_new(EVS):
            sd = _dt.date.fromisoformat(r["start"]); ed = _dt.date.fromisoformat(r["end"])
            if ed < _dt.date.today(): continue
            EVS.append({"city":r["city"], "name":r["name"], "start":sd, "end":ed,
                        "place":r["place"], "img":r["img"], "link":r["link"],
                        "benefit":r["benefit"],
                        "slug": EV.slugify(r["name"]) + "-" + r["start"].replace("-",""),
                        "dday": (sd - _dt.date.today()).days, "month": r["start"][:7]})
    except Exception as _e:
        print("  cpaad 병합 생략:", type(_e).__name__, _e)

    EVS.sort(key=lambda x: (x["start"], x["city"]))
    print("  진행/예정 행사 총계: %d건" % len(EVS))

    by_city = {}
    for e in EVS: by_city.setdefault(e["city"], []).append(e)
    def evs_for(loc):
        cs = cities_of(loc)
        if cs:
            out = []
            for c in cs: out += by_city.get(c, [])
            out += by_city.get(loc, [])
            return sorted(out, key=lambda x: x["start"])
        return by_city.get(loc, [])

    home(EVS)
    for loc, region, path in ALL_LOCS:
        loc_page(loc, region, path, evs_for(loc), len(EVS))

    # 개별 행사 페이지
    for e in EVS: event_page(e, by_city.get(e["city"], []), EVS)
    # 행사장 페이지
    vmap = {}
    for e in EVS:
        v = EV.venue_of(e)
        if v: vmap.setdefault(v, []).append(e)
    vmap = {k:v for k,v in vmap.items() if len(v) >= 2}
    venue_index(vmap)
    _vn = sorted(vmap.keys())
    for v, es in vmap.items(): venue_page(v, es, _vn)
    # 이번주 / 월별
    week_page(EVS)
    mmap = {}
    for e in EVS: mmap.setdefault(e["month"], []).append(e)
    months = sorted(mmap.keys())
    month_index(mmap)
    for ym in months: month_page(ym, mmap[ym], months)

    guide_index()
    for s,t,k in ARTICLES: article_page(s,t,k)
    apply_page(); thanks_page(); privacy_page()

    # sitemap (lastmod=당일, changefreq=daily, 퍼센트인코딩)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in URLS:
        pr = "1.0" if u==DOMAIN+"/" else ("0.9" if u.count("/")<=4 else "0.8")
        sm.append('<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>daily</changefreq><priority>%s</priority></url>'
                  % (enc_url(u), TODAY, pr))
    sm.append('</urlset>')
    w("sitemap.xml", "\n".join(sm))
    w("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % DOMAIN)
    w("%s.txt" % INDEXNOW_KEY, INDEXNOW_KEY)
    # RSS
    pd = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "".join('<item><title>%s 웨딩박람회 일정</title><link>%s</link><guid>%s</guid>'
                    '<pubDate>%s</pubDate><description>%s 웨딩박람회 일정과 무료 초대권 정보</description></item>'
                    % (l, enc_url(DOMAIN+p), enc_url(DOMAIN+p), pd, l) for l,r,p in ALL_LOCS)
    w("rss.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
      f'<title>{SITE}</title><link>{DOMAIN}/</link>'
      f'<description>{TAGLINE}</description><language>ko</language>'
      f'<lastBuildDate>{pd}</lastBuildDate>{items}</channel></rss>')
    # URL 목록(IndexNow용)
    w("_urls.txt", "\n".join(URLS))
    print("생성 완료: %d URL / sitemap lastmod=%s" % (len(URLS), TODAY))
