# -*- coding: utf-8 -*-
"""신규 B사이트 생성기 — 한글 클린URL + 문서 SEO 전면 적용
   실행: python3 gen.py     출력: ../site/"""
import os, re, json, html, random, datetime, shutil
from urllib.parse import quote
from data import *
from seo import *
import events as EV
import evdata as ED
import cpaad as CP

OUT = os.path.join(os.path.dirname(__file__), "..", "site")
TODAY_D = datetime.date.today()
TODAY = TODAY_D.isoformat()
TOTAL_EV = 0      # 전국 등록 일정 수 (히어로 통계용)
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
  <p class="biz">{BIZ}<br>Copyright © {YEAR} {SITE}. All rights reserved.</p>
 </div></footer>
<script src="/assets/events.js" defer></script></body></html>"""

# ── 지역 페이지 ─────────────────────────────────────────────────
def faqs_for(loc):
    v = VENUE.get(loc, "주요 행사장")
    return [(q.format(loc=loc, v=v), a.format(loc=loc, v=v))
            for q, a in ED.sample(ED.LOC_FAQ, loc, 8, "locfaq")]
    faq = [(ED.fix_josa(q), ED.fix_josa(a)) for q, a in faq]

def loc_page(loc, region, path, my_evs=None):
    url = DOMAIN + path
    is_hub = (loc == region)
    intro    = ED.pick(ED.LOC_INTRO, loc, "intro").format(loc=loc)
    tips     = ED.sample(ED.LOC_TIP, loc, 8, "tip")
    cautions = ED.sample(ED.LOC_CAUTION, loc, 9, "cau")
    h2_tip   = ED.pick(ED.LOC_H2_TIP,  loc).format(loc=loc)
    h2_cau   = ED.pick(ED.LOC_H2_CAU,  loc).format(loc=loc)
    h2_faq   = ED.pick(ED.LOC_H2_FAQ,  loc).format(loc=loc)
    h2_near  = ED.pick(ED.LOC_H2_NEAR, loc).format(loc=loc)
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
    ADJ = {"서울": ["경기", "인천", "강원", "충청"],
           "인천": ["경기", "서울", "충청", "강원"],
           "경기": ["서울", "인천", "강원", "충청"],
           "부산": ["경상", "전라", "제주", "충청"],
           "제주": ["부산", "전라", "경상", "서울"]}
    near = sibs[:6] if sibs else ADJ.get(loc, [n for n, _ in REGIONS if n != loc][:4])
    near_links = "".join('<a href="/%s/%s/">%s 웨딩박람회</a>' %
                         (region, c, c) if sibs else '<a href="/%s/">%s 웨딩박람회</a>'%(c,c)
                         for c in near)

    my_evs = my_evs or []
    _v = VENUE.get(loc, "주요 행사장")
    _near2 = (near + ["인근 지역", "가까운 지역"])[:2]
    loc_facts = [ED.pick(ED.LOC_VENUE_LEAD, loc, "vl").format(loc=loc, v=_v),
                 ED.pick(ED.LOC_NEAR_LEAD, loc, "nl").format(loc=loc, n1=_near2[0], n2=_near2[1])]
    loc_facts.append((ED.pick(ED.LOC_COUNT_LEAD, loc, "cl").format(loc=loc, c=len(my_evs)))
                     if my_evs else ED.pick(ED.LOC_EMPTY_LEAD, loc, "el").format(loc=loc))
    loc_fact_html = "".join("<p>%s</p>" % f for f in loc_facts)
    h2_cost_l = ED.pick(ED.H2_COST, loc, "lc")
    cost_lead_l = ED.pick(ED.COST_LEAD, loc, "lc2")
    costs_l = ED.sample(ED.COST_NOTE, loc, 6, "lcost")
    cost_html_l = "".join(f"<div class='tip'><h3>{t}</h3><p>{v}</p></div>" for t, v in costs_l)
    _th_t, _th_p = ED.pick(ED.LOC_THEME, loc, "theme")
    theme_h2 = "%s — %s" % (loc, _th_t)
    theme_html = "".join("<p>%s</p>" % esc(p) for p in _th_p)
    static_cards = cards_html(my_evs, show_city=bool(cs),
        empty=f"{loc} 지역 일정을 준비 중입니다. 새로운 일정이 확정되면 이곳에 바로 표시됩니다.")
    ev_count = len(my_evs)
    tips_html = "".join(f"<div class='tip'><h3>{t}</h3><p>{d}</p></div>" for t,d in tips)
    caution_html = "".join(f"<li>{c}</li>" for c in cautions)
    faq = faqs_for(loc)
    faq_html = "".join(f"<details><summary>{q}</summary><div class='a'>{a}</div></details>" for q,a in faq)

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
     <div><b>{TOTAL_EV}</b><span>전국 등록 일정</span></div>
     <div><b>100%</b><span>무료 초대권</span></div>
     <div><b>{TODAY_D.month}.{TODAY_D.day}</b><span>최근 갱신</span></div>
   </div>
  </div>
 </section>

 <section class="wrap"><div class="factbox">{loc_fact_html}</div></section>

 <section class="wrap">{aeo_block(loc, region)}</section>

 <section class="wrap">
  <h2 class="sec">{loc} 웨딩박람회 최신 일정 {("("+str(ev_count)+"건)") if ev_count else ""}</h2>
  <p class="sub">모집 중인 일정만 표시됩니다. 카드를 눌러 상세 정보와 무료 초대권을 확인하세요.</p>
  <div class="cards" id="event-cards" data-cities="{cities_csv}" data-loc="{loc}">{static_cards}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">{loc} 웨딩박람회 유형 비교</h2>
  {compare_table(loc)}
 </section>

 <section class="wrap">
  <h2 class="sec">{h2_tip}</h2>
  <div class="tips">{tips_html}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">{h2_cau}</h2>
  <ul class="cautions">{caution_html}</ul>
 </section>

 <section class="wrap">
  <div class="theme"><h2>{theme_h2}</h2>{theme_html}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">{h2_cost_l}</h2>
  <p class="sub">{cost_lead_l}</p>
  <div class="tips">{cost_html_l}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">{h2_faq}</h2>
  <div class="faq">{faq_html}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">{h2_near}</h2>
  <div class="chips near">{near_links}</div>
 </section>
</main>
{footer()}"""
    w(path + "index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)


# ── 행사 카드 정적 렌더 (검색봇이 읽는 HTML) ──────────────────────
def event_card(e, show_city=False):
    if e.get("always"):
        dates = e.get("date_text") or "상시 진행"
        dday = "<span class='dday now'>상시</span>"
    else:
        d1, d2 = EV.fmt(e["start"]), EV.fmt(e["end"])
        dates = d1 if e["start"] == e["end"] else "%s ~ %s" % (d1, EV.fmt_short(e["end"]))
        dday = ("<span class='dday'>D-%d</span>" % e["dday"]) if 0 < e["dday"] <= 30 else \
               ("<span class='dday now'>진행중</span>" if e["dday"] <= 0 else "")
    # 썸네일 클릭 → 무료 초대권 신청(외부). 상세 페이지는 아래 '자세히 보기' 버튼으로만 이동.
    img = ('<a class="poster" href="%s" target="_blank" rel="noopener nofollow sponsored" '
           'aria-label="%s 무료 초대권 신청"><img src="%s" alt="%s 포스터" loading="lazy"></a>'
           % (esc(e["link"]), esc(e["name"]), esc(e["img"]), esc(e["name"]))) if e["img"] else ""
    city = ("<span class='ctag'>%s</span>" % esc(e["city"])) if show_city else ""
    ben = ('<div class="benefit">혜택 %s</div>' % esc(e["benefit"])) if e.get("benefit") else ""
    return f"""<article class="card">{img}<div class="body">
 <div class="tags"><span class="status">모집중</span>{city}{dday}</div>
 <h3><a href="/행사/{quote(e['slug'])}/">{esc(e['name'])}</a></h3>
 <div class="meta">일정 {dates}</div>
 <div class="meta">장소 {esc(e['place'])}</div>{ben}
 <a class="cta" href="{esc(e['link'])}" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청</a>
 <a class="detail" href="/행사/{quote(e['slug'])}/">박람회 정보 자세히 보기</a>
</div></article>"""

def cards_html(evs, show_city=False, empty="현재 모집 중인 일정이 없습니다. 새 일정이 확정되면 이곳에 표시됩니다."):
    if not evs: return '<div class="loading">%s</div>' % empty
    return "".join(event_card(e, show_city) for e in evs)

_DAYMAP = [("월", "Monday"), ("화", "Tuesday"), ("수", "Wednesday"), ("목", "Thursday"),
           ("금", "Friday"), ("토", "Saturday"), ("일", "Sunday")]

def _bydays(txt):
    """'매주 토요일/일요일' 같은 표기에서 요일을 뽑는다. 못 찾으면 주말로 둔다."""
    t = txt or ""
    days = ["https://schema.org/%s" % en for ko, en in _DAYMAP if (ko + "요일") in t]
    if not days and "주말" in t:
        days = ["https://schema.org/Saturday", "https://schema.org/Sunday"]
    return days or ["https://schema.org/Saturday", "https://schema.org/Sunday"]

def ld_event(e):
    return json.dumps({"@context":"https://schema.org","@type":"Event",
      "name":e["name"],
      **({"eventSchedule": {"@type": "Schedule",
                            "repeatFrequency": "P1W",
                            "byDay": _bydays(e.get("date_text", "")),
                            "startDate": e["start"].isoformat()}}
         if e.get("always") else
         {"startDate": e["start"].isoformat(), "endDate": e["end"].isoformat()}),
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

# ── 개별 행사 상세 페이지 ────────────────────────────────────────
def event_page(e, same_city):
    """행사 상세 — 페이지마다 내용이 달라지도록 4개 층을 적용한다.
       ① 주소 파싱 실데이터 ② 날짜 파생 ③ 규모 분기 ④ 변형 풀 해시 배정"""
    slug = e["slug"]
    path = "/행사/%s/" % slug; url = DOMAIN + path
    region = region_of_city(e["city"])
    if e.get("always"):
        d1 = d2 = ""
        dates = e.get("date_text") or "상시 진행"
    else:
        d1, d2 = EV.fmt(e["start"]), EV.fmt(e["end"])
        dates = d1 if e["start"] == e["end"] else "%s ~ %s" % (d1, d2)

    ad = ED.parse_addr(e["place"])
    if e.get("always"):
        # 상시 행사는 날짜 파생 문장(요일·일수·성수기)이 성립하지 않는다
        df = None
        _lbl = e.get("date_text") or "상시 진행"
        fact_sents = ED.addr_sentences(ad, e["city"], slug) + [
            "이 행사는 특정 날짜가 아니라 %s 일정으로 진행됩니다." % _lbl,
            "방문 전 신청 페이지에서 해당 주 운영 여부를 확인해 주세요.",
        ]
    else:
        df = ED.date_facts(e["start"], e["end"])
        fact_sents = ED.addr_sentences(ad, e["city"], slug) + ED.date_sentences(df, slug)
    scale = ED.scale_sentence(e["name"])
    if scale: fact_sents.append(scale)

    title = ("%s 일정 %s | 무료초대권 신청 - %s 웨딩박람회"
             % (e["name"], "상시 진행" if e.get("always")
                else EV.fmt_short(e["start"]), e["city"]))
    desc = "%s%s %s %s에서 열립니다. %s" % (e["name"], ED.josa(e["name"]),
        dates, ad["gu"] or e["city"],
        ED.pick(["무료 초대권 신청과 웨딩홀·스드메 상담 정보를 확인하세요.",
                 "초대권 사전 신청 방법과 방문 전 확인 사항을 정리했습니다.",
                 "무료 입장 신청과 상담 준비 항목을 안내합니다."], slug, "desc"))
    kw = "%s, %s 웨딩박람회, %s 일정, %s 무료초대권, %s결혼박람회" % (
        e["name"], e["city"], e["name"], e["name"], e["city"])

    bc = [("홈", DOMAIN+"/"), (region, DOMAIN+"/%s/"%region)]
    if e["city"] != region: bc.append((e["city"], DOMAIN+"/%s/%s/"%(region, e["city"])))
    bc.append((e["name"], url))

    others = [x for x in same_city if x["slug"] != slug][:6]
    rel = "".join('<li><a href="/행사/%s/">%s <span>%s</span></a></li>'
                  % (quote(x["slug"]), esc(x["name"]), EV.fmt_short(x["start"])) for x in others)

    # ── FAQ: 20종 풀에서 5개를 해시로 배정 ──
    faq = [(q.format(n=e["name"], p=e["place"], c=e["city"]),
            a.format(n=e["name"], p=e["place"], c=e["city"]))
           for q, a in ED.sample(ED.FAQ_POOL, slug, 7, "faq")]
    faq = [(ED.fix_josa(q), ED.fix_josa(a)) for q, a in faq]
    faq_html = "".join("<details><summary>%s</summary><div class='a'>%s</div></details>"
                       % (esc(q), esc(a)) for q, a in faq)

    # ── 변형 블록 ──
    h2_apply = ED.pick(ED.H2_APPLY, slug); h2_check = ED.pick(ED.H2_CHECK, slug)
    h2_prep  = ED.pick(ED.H2_PREP,  slug); h2_info  = ED.pick(ED.H2_INFO,  slug)
    h2_faq   = ED.pick(ED.H2_FAQ,   slug)
    lead     = ED.pick(ED.APPLY_LEAD, slug, "lead")
    steps    = ED.pick(ED.APPLY_STEPS, slug, "step")
    cautions = ED.sample(ED.CAUTION, slug, 7, "cau")
    preps    = ED.sample(ED.PREP,    slug, 6, "prep")
    closing  = ED.pick(ED.CLOSING, slug, "cl")
    h2_cost  = ED.pick(ED.H2_COST, slug)
    cost_lead = ED.pick(ED.COST_LEAD, slug, "cl2")
    costs    = ED.sample(ED.COST_NOTE, slug, 5, "cost")
    cost_html = "".join("<div class='tip'><h3>%s</h3><p>%s</p></div>" % (esc(t), esc(v)) for t, v in costs)

    steps_html = "".join("<li>%s</li>" % esc(s) for s in steps)
    cau_html   = "".join("<li>%s</li>" % esc(c) for c in cautions)
    prep_html  = "".join("<li>%s</li>" % esc(p) for p in preps)
    fact_html  = "".join("<p>%s</p>" % esc(s) for s in fact_sents)

    lds = [ld_event(e), ld_breadcrumb(bc), ld_faq(faq), ld_howto(e["city"]),
           ld_itemlist(e["name"], [x["name"] for x in others] or [e["name"]])]
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
    <tr><th>행사일</th><td>{dates}{(' · ' + str(df['days']) + '일간') if df and df['days'] > 1 else ''}</td></tr>
    <tr><th>장소</th><td>{esc(e['place'])}</td></tr>
    <tr><th>지역</th><td><a href="/{region}/{'' if e['city']==region else e['city']+'/'}">{esc(e['city'])} 웨딩박람회 전체 일정</a></td></tr>
    <tr><th>입장</th><td>무료 초대권 사전 신청</td></tr>
   </table>
   <a class="btn big" href="{esc(e['link'])}" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청하기</a>
  </div>
 </section>
 {('<section class="wrap">'+hero_img+'</section>') if hero_img else ''}
 <section class="wrap">
  <h2 class="sec">{esc(h2_info)}</h2>
  <div class="factbox">{fact_html}</div>
 </section>
 <section class="wrap">
  <div class="aeo">
   <h2>{esc(e['name'])}, {esc(h2_apply)}</h2>
   <p class="ans">{esc(e['name'])}{ED.josa(e['name'])} <b>{dates}</b> {esc(e['place'])}에서 열립니다. {esc(lead)}</p>
   <p class="ans-sub"><b>신청 방법</b></p>
   <ol>{steps_html}</ol>
   <p class="pnote">※ {esc(closing)}</p>
  </div>
 </section>
 <section class="wrap">
  <h2 class="sec">{esc(h2_prep)}</h2>
  <ul class="cautions">{prep_html}</ul>
 </section>
 <section class="wrap">
  <h2 class="sec">{esc(h2_check)}</h2>
  <ul class="cautions">{cau_html}</ul>
 </section>
 <section class="wrap">
  <h2 class="sec">{esc(h2_cost)}</h2>
  <p class="sub">{esc(cost_lead)}</p>
  <div class="tips">{cost_html}</div>
 </section>
 {('<section class="wrap"><h2 class="sec">'+esc(e['city'])+' 다른 웨딩박람회 일정</h2><ul class="rellist">'+rel+'</ul></section>') if rel else ''}
 <section class="wrap"><h2 class="sec">{esc(h2_faq)}</h2><div class="faq">{faq_html}</div></section>
</main>
{footer()}"""
    w(path+"index.html", head(title, desc, kw, url, lds) + body)
    URLS.append(url)

# ── 행사장별 페이지 ─────────────────────────────────────────────
VENUE_ALL = []
def venue_page(venue, evs):
    slug = EV.slugify(venue)
    path = "/행사장/%s/" % slug; url = DOMAIN + path
    evs = sorted(evs, key=lambda x: x["start"])
    cities = []
    for e in evs:
        if e["city"] not in cities: cities.append(e["city"])
    c1 = cities[0] if cities else "전국"
    title = "%s 웨딩박람회 일정 %d건 | 무료초대권 - %s" % (venue, len(evs), SITE)
    desc = "%s에서 열리는 웨딩박람회 일정 %d건을 정리했습니다. 날짜와 장소, 무료 초대권 신청 정보를 확인하세요." % (venue, len(evs))
    kw = "%s 웨딩박람회, %s 결혼박람회, %s 웨딩박람회 일정, %s 무료초대권" % (venue, venue, venue, venue)
    bc = [("홈",DOMAIN+"/"),("행사장",DOMAIN+"/행사장/"),(venue,url)]
    lds = [ld_breadcrumb(bc), ld_itemlist(venue, [e["name"] for e in evs])]

    # 사실 문단 — 실제 데이터에서만 뽑는다
    facts = [ED.pick(ED.VEN_LEAD, venue, "vl").format(v=venue, c1=c1),
             ED.pick(ED.VEN_COUNT, venue, "vc").format(v=venue, n=len(evs))]
    if evs:
        d1, d2 = EV.fmt(evs[0]["start"]), EV.fmt(evs[-1]["end"])
        facts.append(ED.pick(ED.VEN_SPAN, venue, "vs").format(d1=d1, d2=d2) if d1 != d2
                     else ED.pick(ED.VEN_ONE, venue, "vo").format(d1=d1))
    if len(cities) > 1:
        facts.append("확인된 회차는 %s 지역에 걸쳐 있습니다." % "·".join(cities[:4]))
    elif cities:
        facts.append("%s 지역 예비부부께서 방문하기 좋은 위치입니다." % c1)
    wk = sorted({"%s요일" % "월화수목금토일"[e["start"].weekday()]
                 for e in evs if not e.get("always")})
    if wk: facts.append("시작 요일은 %s 기준으로 잡혀 있습니다." % "·".join(wk))
    fact_html = "".join("<p>%s</p>" % f for f in facts)

    tips = ED.sample(ED.VEN_TIP, venue, 6, "vt")
    caus = ED.sample(ED.VEN_CAU, venue, 6, "vcau")
    faqs = [(ED.fix_josa(q.format(v=venue)), ED.fix_josa(a.format(v=venue)))
            for q, a in ED.sample(ED.VEN_FAQ, venue, 6, "vf")]
    lds.append(ld_faq(faqs))
    h2i = ED.pick(ED.VEN_H2_INFO, venue).format(v=venue)
    h2t = ED.pick(ED.VEN_H2_TIP,  venue).format(v=venue)
    h2c = ED.pick(ED.VEN_H2_CAU,  venue).format(v=venue)
    h2f = ED.pick(ED.VEN_H2_FAQ,  venue).format(v=venue)
    tips_html = "".join(f"<div class='tip'><h3>{esc(t)}</h3><p>{esc(d)}</p></div>" for t, d in tips)
    cau_html  = "".join(f"<li>{esc(c)}</li>" for c in caus)
    faq_html  = "".join(f"<details><summary>{esc(q)}</summary><div class='a'>{esc(a)}</div></details>" for q, a in faqs)
    other = "".join('<a href="/행사장/%s/">%s 일정</a>' % (quote(EV.slugify(v)), esc(v))
                    for v in VENUE_ALL if v != venue)
    body = f"""{header()}
{breadcrumb_html(bc)}
<main>
 <section class="hero"><div class="wrap">
  <p class="eyebrow">행사장별 일정</p>
  <h1>{esc(venue)} 웨딩박람회 일정</h1>
  <p class="lead">{esc(venue)}에서 열리는 웨딩박람회 {len(evs)}건입니다. 날짜를 확인하고 무료 초대권을 신청하세요.</p>
 </div></section>
 <section class="wrap"><h2 class="sec">{esc(h2i)}</h2><div class="factbox">{fact_html}</div></section>
 <section class="wrap"><div class="cards">{cards_html(evs, show_city=True)}</div></section>
 <section class="wrap"><h2 class="sec">{esc(h2t)}</h2><div class="tips">{tips_html}</div></section>
 <section class="wrap"><h2 class="sec">{esc(h2c)}</h2><ul class="cautions">{cau_html}</ul></section>
 <section class="wrap"><h2 class="sec">{esc(h2f)}</h2><div class="faq">{faq_html}</div></section>
 <section class="wrap"><h2 class="sec">다른 행사장 일정</h2><div class="chips near">{other}</div></section>
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
     <section class="wrap"><div class="guidegrid">{items}</div></section>
     <section class="wrap"><h2 class="sec">행사장별로 보면 좋은 이유</h2><div class="factbox">
      <p>같은 행사장에서도 회차마다 주최와 참여 업체 구성이 달라집니다. 행사장을 기준으로 일정을 모아 보면 이동 경로가 익숙한 곳에서 여러 회차를 비교하실 수 있습니다.</p>
      <p>현재 {len(vmap)}개 행사장에서 진행 예정 일정이 확인됩니다. 총 {sum(len(v) for v in vmap.values())}건이며, 각 행사장 페이지에서 날짜와 지역을 함께 확인하실 수 있습니다.</p>
      <p>행사장이 넓은 경우 입구에서 배치도를 먼저 확인하고 볼 순서를 정하시면 이동에만 쓰는 시간을 줄일 수 있습니다.</p>
      <p>주말 회차는 주차장이 일찍 차는 편이라 대중교통 경로를 함께 확인해 두시면 좋습니다.</p></div></section>
     <section class="wrap"><h2 class="sec">기간으로 찾기</h2><div class="chips near">
      <a href="/이번주-웨딩박람회/">이번주 일정</a><a href="/일정/">월별 일정</a><a href="/가이드/">결혼준비 가이드</a></div></section>
     </main>{footer()}"""
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

    # 이 페이지만의 사실 — 주말/평일, 요일 분포, 남은 일수
    wknd = [x for x in cur if x["start"].weekday() >= 5]
    today_run = [x for x in cur if x["start"] <= TODAY_D <= x["end"]]
    soon = [x for x in cur if 0 < x["dday"] <= 3]
    wk_cities = []
    for x in cur:
        if x["city"] not in wk_cities: wk_cities.append(x["city"])
    facts = ["%s부터 %s까지 2주 구간에서 확인된 일정은 %d건입니다." % (EV.fmt(mon), EV.fmt(sun), len(cur))]
    if today_run: facts.append("오늘 기준 진행 중인 행사는 %d건입니다." % len(today_run))
    if wknd and len(wknd) < len(cur):
        facts.append("이 가운데 주말에 시작하는 회차는 %d건, 평일 시작은 %d건입니다." % (len(wknd), len(cur)-len(wknd)))
    if soon:      facts.append("3일 안에 시작하는 일정이 %d건 있어 신청을 서두르셔야 합니다." % len(soon))
    if wk_cities: facts.append("지역은 %s 등 %d개 도시에 분포합니다." % ("·".join(wk_cities[:5]), len(wk_cities)))
    facts.append("이 페이지는 매일 갱신되며, 지난 일정은 자동으로 내려갑니다.")
    fact_html = "".join("<p>%s</p>" % esc(f) for f in facts)

    # 요일별 표 — 월별 페이지에는 없는 구성
    days = []
    for i in range(14):
        d = mon + datetime.timedelta(days=i)
        if d < TODAY_D: continue
        n = [x for x in cur if x["start"] <= d <= x["end"]]
        if n: days.append((d, n))
    day_rows = "".join(
        "<tr><th>%s</th><td>%d건</td><td>%s</td></tr>" %
        (EV.fmt_short(d), len(n), esc("·".join(sorted({x["city"] for x in n}))[:60]))
        for d, n in days)
    day_html = ("<table class='wtable'><thead><tr><th>날짜</th><th>일정</th><th>지역</th></tr></thead>"
                "<tbody>%s</tbody></table>" % day_rows) if day_rows else ""

    tips = ED.sample(ED.WEEK_TIP, "week%s" % mon.isoformat(), 4, "wt")
    tips_html = "".join(f"<div class='tip'><h3>{esc(t)}</h3><p>{esc(d)}</p></div>" for t, d in tips)
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><p class="eyebrow">{EV.fmt_short(mon)} ~ {EV.fmt_short(sun)}</p>
      <h1>이번주 웨딩박람회 일정</h1>
      <p class="lead">지금 신청 가능한 전국 웨딩박람회 {len(cur)}건입니다. 주말 방문 계획을 세워 보세요.</p></div></section>
     <section class="wrap"><h2 class="sec">{esc(ED.pick(ED.WEEK_H2, mon.isoformat()))}</h2>
      <div class="factbox">{fact_html}</div></section>
     <section class="wrap"><div class="cards">{cards_html(cur, show_city=True, empty="이번주 예정된 일정이 없습니다.")}</div></section>
     <section class="wrap"><h2 class="sec">날짜별 진행 현황</h2>{day_html}</section>
     <section class="wrap"><h2 class="sec">이번주 방문 요령</h2><div class="tips">{tips_html}</div></section>
     <section class="wrap"><h2 class="sec">다른 기간 일정</h2>
      <div class="chips near"><a href="/일정/">월별 일정 보기</a><a href="/행사장/">행사장별 보기</a></div></section>
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
    evs = sorted(evs, key=lambda x: x["start"])
    title = "%s 웨딩박람회 일정 %d건 총정리 | 무료초대권 - %s" % (label, len(evs), SITE)
    desc = "%s에 열리는 전국 웨딩박람회 %d건의 날짜와 장소를 정리했습니다. 지역별 일정과 무료 초대권 신청 정보를 확인하세요." % (label, len(evs))
    kw = "%s 웨딩박람회, %s 웨딩박람회 일정, %d년 웨딩박람회, 웨딩박람회 무료초대권" % (label, label, y)
    bc=[("홈",DOMAIN+"/"),("월별 일정",DOMAIN+"/일정/"),(label,url)]
    nav = "".join('<a class="%s" href="/일정/%s/">%s</a>' %
                  ("on" if x==ym else "", x, "%d년 %s"%(int(x[:4]), MON_KO[int(x[5:7])]))
                  for x in all_months)

    # 월 고유 사실 — 주차 분포·지역 분포·성수기 구분
    facts = [ED.pick(ED.MON_LEAD, ym, "ml").format(label=label)]
    season = ("성수기" if m in (3,4,5,9,10,11) else
              "혹서기" if m in (7,8) else "혹한기" if m in (12,1,2) else "비수기")
    facts.append("%s은 %s에 해당합니다. %s" % (label, season, ED.MON_PEAK[season]))
    wcnt = {}
    for x in evs: wcnt[(x["start"].day - 1)//7 + 1] = wcnt.get((x["start"].day - 1)//7 + 1, 0) + 1
    if wcnt:
        top = max(wcnt, key=lambda k: wcnt[k])
        facts.append("주차별로 보면 %d주차에 %d건으로 가장 많이 몰려 있습니다." % (top, wcnt[top]))
    mcity = []
    for x in evs:
        if x["city"] not in mcity: mcity.append(x["city"])
    if mcity:
        facts.append("개최 지역은 %s 등 %d개 도시입니다." % ("·".join(mcity[:6]), len(mcity)))
    wknd = sum(1 for x in evs if x["start"].weekday() >= 5)
    if evs: facts.append("주말에 시작하는 회차는 %d건, 평일 시작은 %d건입니다." % (wknd, len(evs)-wknd))
    fact_html = "".join("<p>%s</p>" % esc(f) for f in facts)

    # 주차별 표 — 이번주 페이지의 날짜별 표와 구성이 다르다
    wrows = "".join("<tr><th>%d주차</th><td>%d건</td></tr>" % (k, wcnt[k]) for k in sorted(wcnt))
    week_html = ("<table class='wtable'><thead><tr><th>주차</th><th>일정 수</th></tr></thead>"
                 "<tbody>%s</tbody></table>" % wrows) if wrows else ""
    # 지역별 표
    cc = {}
    for x in evs: cc[x["city"]] = cc.get(x["city"], 0) + 1
    crows = "".join("<tr><th>%s</th><td>%d건</td></tr>" % (esc(k), v)
                    for k, v in sorted(cc.items(), key=lambda t: -t[1])[:12])
    city_html = ("<table class='wtable'><thead><tr><th>지역</th><th>일정 수</th></tr></thead>"
                 "<tbody>%s</tbody></table>" % crows) if crows else ""

    tips = ED.sample(ED.MON_TIP, ym, 4, "mt")
    tips_html = "".join(f"<div class='tip'><h3>{esc(t)}</h3><p>{esc(d)}</p></div>" for t, d in tips)
    body=f"""{header()}{breadcrumb_html(bc)}<main>
     <section class="hero"><div class="wrap"><p class="eyebrow">월별 일정</p>
      <h1>{label} 웨딩박람회 일정</h1>
      <p class="lead">{label}에 전국에서 열리는 웨딩박람회 {len(evs)}건입니다.</p>
      <div class="monthnav">{nav}</div></div></section>
     <section class="wrap"><h2 class="sec">{label} 일정 개요</h2><div class="factbox">{fact_html}</div></section>
     <section class="wrap"><div class="cards">{cards_html(evs, show_city=True)}</div></section>
     <section class="wrap"><h2 class="sec">{label} 주차별 분포</h2>{week_html}</section>
     <section class="wrap"><h2 class="sec">{label} 지역별 분포</h2>{city_html}</section>
     <section class="wrap"><h2 class="sec">{label} 방문 계획 세우기</h2><div class="tips">{tips_html}</div></section>
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
     <section class="wrap"><div class="guidegrid">{items}</div></section>
     <section class="wrap"><h2 class="sec">월별로 계획을 세울 때</h2><div class="factbox">
      <p>예식 예정일이 정해져 있다면 그 시점에서 6~9개월 전이 박람회를 둘러보기 좋은 시기입니다. 예식장을 먼저 확정해야 스드메 일정을 역산할 수 있기 때문입니다.</p>
      <p>봄과 가을은 예식이 몰리는 성수기라 원하는 날짜를 잡기 어려운 편이고, 여름과 겨울은 선택지가 넓은 대신 이동 여건을 함께 고려하셔야 합니다.</p>
      <p>현재 {len(mmap)}개 달에 걸쳐 총 {sum(len(v) for v in mmap.values())}건의 일정이 확인됩니다. 각 달 페이지에서 주차별·지역별 분포를 확인하실 수 있습니다.</p>
      <p>한 달에 두 곳 이상 방문하시는 경우 간격을 1~2주 두시면 앞서 받은 견적을 정리할 시간이 생깁니다.</p></div></section>
     <section class="wrap"><h2 class="sec">다른 방식으로 찾기</h2><div class="chips near">
      <a href="/이번주-웨딩박람회/">이번주 일정</a><a href="/행사장/">행사장별 일정</a><a href="/가이드/">결혼준비 가이드</a></div></section>
     </main>{footer()}"""
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
    faq_html = "".join(f"<details><summary>{q}</summary><div class='a'>{a}</div></details>" for q,a in faq)
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
  <h2 class="sec">이번주 열리는 웨딩박람회</h2>
  <p class="sub">지금 신청 가능한 일정입니다. <a href="/이번주-웨딩박람회/">전체 보기</a></p>
  <div class="cards">{week_cards}</div>
 </section>

 <section class="wrap">
  <h2 class="sec">지역별 웨딩박람회 일정</h2>
  <p class="sub">원하는 지역을 선택하세요.</p>
  <div class="regiongrid">{blocks}</div>
 </section>

 <section class="wrap">
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
 ("혼자 갈지, 함께 갈지","혼자 오셔도 상담은 가능합니다. 다만 예산과 홀 선택은 두 분이 함께 결정할 항목이라 같이 오시는 경우가 많습니다. 혼주가 결정에 관여하신다면 혼주 의견이 필요한 항목을 미리 표시해 두시면 상담이 두 번 반복되지 않습니다."),
 ("몇 곳을 다녀야 적당한가","두세 곳이 적당합니다. 한 곳만 보면 제시된 금액이 높은지 낮은지 판단할 기준이 없고, 네 곳을 넘기면 조건이 뒤섞여 오히려 정리가 어려워집니다. 방문 간격은 1~2주가 무난합니다."),
 ("무료 초대권은 어떤 개념인가","사전 신청자에게 안내되는 입장 방식입니다. 현장 접수가 가능한 회차도 있지만 대기가 생길 수 있어 날짜가 정해지셨다면 미리 신청해 두시는 편이 확실합니다. 신청 후 주최 측에서 방문 일정을 확인하는 연락이 오는 것이 일반적입니다."),
 ("다녀온 뒤에 할 일","돌아오는 길에 바로 정리하시는 것이 좋습니다. 업체명, 담당자, 총액, 포함 항목 네 가지만 적어 두어도 다음 상담에서 질문이 훨씬 구체적으로 나옵니다. 하루만 지나도 부스별 조건이 섞이기 시작합니다."),
],
"스드메-견적-비교": [
 ("스드메 견적이 업체마다 다른 이유","스드메는 스튜디오·드레스·메이크업을 묶은 패키지라 구성 방식에 따라 총액이 달라집니다. 같은 가격이라도 촬영 컷수와 드레스 벌수가 다르면 실제 가치는 크게 차이 납니다."),
 ("반드시 확인할 항목 다섯 가지","촬영 원본과 수정본 제공 범위, 드레스 착용 벌수와 등급, 헬퍼비와 피팅비 포함 여부, 메이크업 담당자 지정 가능 여부, 앨범과 액자 구성입니다."),
 ("추가금이 붙는 지점","주말 촬영 할증, 수입 드레스 업그레이드, 원본 데이터 구매, 헬퍼 교통비가 대표적입니다. 견적서에 포함으로 적혀 있는지 항목별로 확인하세요."),
 ("비교표를 만들어 보세요","업체명, 총액, 촬영 컷수, 드레스 벌수, 추가금 항목을 표로 정리하면 어느 곳이 실제로 합리적인지 한눈에 보입니다. 상담마다 견적서를 사진으로 남겨 두면 편합니다."),
 ("계약서에 남겨야 할 것","구두로 약속받은 업그레이드나 서비스는 반드시 특약란에 문구로 기재해야 합니다. 취소 시 환불 규정과 일정 변경 가능 횟수도 함께 확인하세요."),
 ("패키지 안의 업체가 지정인지 확인하세요","같은 금액의 패키지라도 스튜디오와 드레스숍을 고를 수 있는 경우와 지정된 경우가 있습니다. 선택 가능 범위가 총액만큼이나 만족도를 좌우하므로 상담에서 먼저 확인하시는 편이 좋습니다."),
 ("현장 결제 항목을 따로 적으세요","헬퍼비, 추가 보정비, 드레스 피팅 추가 비용처럼 계약 금액과 별개로 당일 현장에서 결제하는 항목이 있습니다. 이 부분이 빠진 견적끼리 비교하면 실제 지출이 어긋납니다."),
 ("항목명을 통일해 적어 두세요","업체마다 부르는 이름이 달라 같은 항목이 다르게 보입니다. 촬영 시간·의상 벌수·제공 원본 수·메이크업 횟수 네 가지 기준으로 통일해 적으면 어느 쪽이 실제로 넉넉한 구성인지 바로 드러납니다."),
 ("견적 유효기간을 물어보세요","현장에서 안내된 조건이 그날에만 유효한지, 일정 기간 유지되는지 확인해 두시면 비교할 시간을 벌 수 있습니다. 담당자에게 직접 물어보시면 대부분 알려 줍니다."),
],
"결혼준비-체크리스트": [
 ("12개월 전 · 큰 틀 정하기","예산 상한선과 희망 예식 시기를 정하고 양가 상견례 일정을 잡습니다. 이 시기에 웨딩박람회를 방문하면 전체 시세를 파악하기 좋습니다."),
 ("9개월 전 · 예식장 확정","하객 규모와 예산에 맞는 웨딩홀을 두세 곳 비교한 뒤 계약합니다. 보증 인원과 식대 조건이 총액을 좌우하므로 꼼꼼히 확인하세요."),
 ("6개월 전 · 스드메 계약","촬영 콘셉트를 정하고 스튜디오·드레스·메이크업을 계약합니다. 원본 제공과 추가금 조건을 반드시 확인해야 합니다."),
 ("3개월 전 · 예물과 혼수","예물과 예단, 가전·가구를 준비합니다. 배송과 설치 일정이 입주일과 맞는지 확인이 필요합니다."),
 ("1개월 전 · 최종 점검","청첩장 발송, 신혼여행 준비물, 예식 당일 동선과 진행 순서를 확정합니다. 잔금 일정과 환불 규정도 다시 확인해 두세요."),
 ("순서를 바꿔도 되는 경우","예식 날짜가 이미 정해져 있거나 홀이 확정된 경우에는 스드메부터 진행하셔도 무리가 없습니다. 순서 자체보다 앞 단계가 확정되지 않은 채 뒤 단계를 계약하지 않는 것이 중요합니다."),
 ("예산을 나누는 기준","총액 상한을 먼저 정하고 예식장·스드메·예물 혼수 세 덩어리로 나눠 두시면 상담 중에 한쪽으로 몰리는 일을 줄일 수 있습니다. 항목별 상한이 없으면 앞에서 쓴 만큼 뒤가 빠듯해집니다."),
 ("두 분의 역할을 나눠 두세요","연락 담당과 기록 담당을 나누면 상담이 훨씬 빨라집니다. 한 분이 질문하는 동안 다른 분이 조건을 적어 두면 놓치는 항목이 줄어듭니다."),
 ("일정이 밀렸을 때","준비 기간이 짧아도 순서만 지키면 진행할 수 있습니다. 예식장을 먼저 확정하고 남은 기간을 역산해 스드메 일정을 잡으시면 됩니다. 촬영 일정이 가장 먼저 마감되는 편이라 이 부분을 우선 확인하세요."),
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
    def _fmt(s):
        return s.replace("{loc}", "우리 지역").replace("{v}", "행사장")
    afaq = [(ED.fix_josa(_fmt(q)), ED.fix_josa(_fmt(a))) for q, a in ED.sample(ED.LOC_FAQ, slug, 6, "art")]
    lds.append(ld_faq(afaq))
    afaq_html = "".join("<details><summary>%s</summary><div class='a'>%s</div></details>"
                        % (esc(q), esc(a)) for q, a in afaq)
    others = "".join('<a href="/가이드/%s/">%s</a>' % (quote(s), esc(t))
                     for s, t, _ in ARTICLES if s != slug)
    body = f"""{header()}
{breadcrumb_html(bc)}
<main>
 <section class="hero"><div class="wrap">
   <p class="eyebrow">결혼준비 가이드</p><h1>{title_ko}</h1></div></section>
 <section class="wrap article">{inner}
   <div class="cta-box"><b>우리 지역 웨딩박람회 일정이 궁금하다면</b>
     <a class="btn" href="/">지역별 일정 보기</a></div>
 </section>
 <section class="wrap"><h2 class="sec">자주 묻는 질문</h2><div class="faq">{afaq_html}</div></section>
 <section class="wrap"><h2 class="sec">다른 가이드</h2><div class="chips near">{others}</div></section>
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
<section class="wrap"><div class="guidegrid">{items}</div></section>
<section class="wrap"><h2 class="sec">가이드를 읽는 순서</h2><div class="factbox">
 <p>처음 준비를 시작하셨다면 결혼준비 체크리스트를 먼저 보시면 전체 흐름이 잡힙니다. 시기별로 무엇을 정해야 하는지 순서가 정리되어 있습니다.</p>
 <p>박람회 방문 날짜가 정해지셨다면 웨딩박람회 활용법을 보시면 됩니다. 현장에서 무엇을 물어보고 무엇을 적어 와야 하는지 정리했습니다.</p>
 <p>견적을 이미 받으신 상태라면 스드메 견적 비교를 참고하세요. 업체마다 다르게 부르는 항목을 같은 기준으로 놓고 보는 방법을 다룹니다.</p>
 <p>세 편 모두 특정 업체를 권하지 않습니다. 조건을 확인하는 방법만 정리했습니다.</p></div></section>
<section class="wrap"><h2 class="sec">일정 찾아보기</h2><div class="chips near">
 <a href="/이번주-웨딩박람회/">이번주 일정</a><a href="/일정/">월별 일정</a><a href="/행사장/">행사장별 일정</a></div></section>
</main>{footer()}"""
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
 </form></section>
<section class="wrap"><h2 class="sec">신청은 이렇게 진행됩니다</h2><div class="factbox">
 <p>희망 지역과 일정을 남겨 주시면, 조건에 맞는 박람회가 열릴 때 상담 파트너를 통해 방문 안내를 드립니다. 신청 자체에는 비용이 들지 않습니다.</p>
 <p>연락처는 방문 일정을 확인하기 위한 용도로만 사용되며, 안내를 원하지 않으시면 그 자리에서 말씀해 주시면 됩니다.</p>
 <p>예식 날짜가 아직 정해지지 않으셨어도 신청하실 수 있습니다. 시세를 먼저 파악할 목적으로 방문하시는 분도 많습니다.</p>
 <p>희망 지역에 당장 일정이 없더라도 신청 내용은 보관되며, 새 일정이 확정되면 안내드립니다.</p></div></section>
<section class="wrap"><h2 class="sec">신청 전에 정해두면 좋은 것</h2><div class="tips">
 <div class="tip"><h3>예상 하객 수</h3><p>이 숫자 하나로 후보 홀이 크게 좁혀집니다. 대략적인 범위만 있어도 충분합니다.</p></div>
 <div class="tip"><h3>희망 예식 시기</h3><p>월과 요일을 두세 개 후보로 준비하시면 상담이 빨라집니다.</p></div>
 <div class="tip"><h3>예산 상한</h3><p>총액 기준을 먼저 정하시면 맞지 않는 제안을 걸러낼 수 있습니다.</p></div>
 <div class="tip"><h3>이동 가능 범위</h3><p>인근 지역까지 열어두시면 날짜 선택지가 넓어집니다.</p></div></section>
<section class="wrap"><h2 class="sec">신청 전 자주 묻는 질문</h2><div class="faq">
 <details><summary>신청하면 비용이 발생하나요?</summary><div class='a'>신청과 초대권 안내에는 비용이 들지 않습니다. 이후 계약 여부는 상담 후 직접 결정하시면 됩니다.</div></details>
 <details><summary>연락은 언제 오나요?</summary><div class='a'>희망 지역에 진행 예정 일정이 있는 경우 순차적으로 안내드립니다. 원하시는 연락 시간대를 문의란에 적어 주시면 참고합니다.</div></details>
 <details><summary>여러 지역을 함께 신청할 수 있나요?</summary><div class='a'>문의란에 함께 적어 주시면 됩니다. 이동 가능한 범위를 알려 주시면 선택지를 넓혀 안내드립니다.</div></details>
 <details><summary>초대권 없이 현장 방문이 되나요?</summary><div class='a'>회차에 따라 다릅니다. 사전 신청자에게 우선 안내되는 경우가 많아 미리 신청해 두시는 편이 확실합니다.</div></details>
 <details><summary>신청 내용을 수정하고 싶습니다</summary><div class='a'>다시 신청해 주시면 최신 내용으로 안내드립니다.</div></details></div></section>
<section class="wrap"><h2 class="sec">일정 먼저 확인하기</h2><div class="chips near">
 <a href="/이번주-웨딩박람회/">이번주 일정</a><a href="/일정/">월별 일정</a><a href="/행사장/">행사장별 일정</a><a href="/가이드/">결혼준비 가이드</a></div></section>
</main>{footer()}"""
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

    # cpaad 보완 — 넷리파이(해외 IP)에서는 cpaad 접속이 타임아웃이라 기본 비활성.
    # 매 빌드마다 25초 x 3회를 헛되이 쓰게 되므로 끕니다.
    # 수집은 사장님 PC의 cpaad자동.py 가 시트에 직접 넣습니다.
    # 되살리려면 넷리파이 환경변수 CPAAD_ENABLE=1 을 넣으세요.
    if os.environ.get("CPAAD_ENABLE") != "1":
        print("  cpaad 빌드측 수집: 비활성 (PC 수집기가 시트에 직접 기록)")
        CP.DIAG.append("빌드측 cpaad 수집 비활성 — CPAAD_ENABLE=1 로 켤 수 있습니다")
        _skip_cpaad = True
    else:
        _skip_cpaad = False

    try:
        if _skip_cpaad:
            raise StopIteration
        _today = datetime.date.today()
        _added = 0
        for r in CP.merge_new(EVS):
            try:
                sd = datetime.date.fromisoformat(r["start"])
                ed = datetime.date.fromisoformat(r["end"]) if r["end"] else sd
            except ValueError:
                continue
            if ed < _today: continue
            EVS.append({"city": r["city"], "name": r["name"], "start": sd, "end": ed,
                        "place": r["place"], "img": r["img"], "link": r["link"],
                        "benefit": r.get("benefit", ""),
                        "slug": EV.slugify(r["name"]) + "-" + r["start"].replace("-", ""),
                        "dday": (sd - _today).days, "month": r["start"][:7]})
            _added += 1
        print("  cpaad 병합: %d건 추가" % _added)
        CP.DIAG.append("cpaad 병합 결과: %d건 추가" % _added)
    except StopIteration:
        pass
    except Exception as _e:
        print("  cpaad 병합 생략:", type(_e).__name__, _e)
        try: CP.DIAG.append("cpaad 병합 예외: %s: %s" % (type(_e).__name__, _e))
        except Exception: pass

    # 진단 결과를 사이트에 파일로 남긴다 (robots 로 수집 차단)
    try:
        _diag = "\n".join(getattr(CP, "DIAG", []) or ["(진단 기록 없음)"])
        w("_cpaad-status.txt",
          "weddingnote cpaad 수집 진단\n빌드 시각(UTC): %s\n대상 URL: %s\n%s\n%s\n"
          % (datetime.datetime.utcnow().isoformat(timespec="seconds"),
             CP.CPAAD_URL, "-" * 50, _diag))
    except Exception as _e2:
        print("  진단 파일 기록 실패:", _e2)

    EVS.sort(key=lambda x: (x["start"], x["city"]))
    TOTAL_EV = len(EVS)
    print("  진행/예정 행사: %d건" % len(EVS))

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
        loc_page(loc, region, path, evs_for(loc))

    # 개별 행사 페이지
    for e in EVS: event_page(e, by_city.get(e["city"], []))
    # 행사장 페이지
    vmap = {}
    for e in EVS:
        v = EV.venue_of(e)
        if v: vmap.setdefault(v, []).append(e)
    vmap = {k:v for k,v in vmap.items() if len(v) >= 2}
    VENUE_ALL[:] = sorted(vmap.keys())
    venue_index(vmap)
    for v, es in vmap.items(): venue_page(v, es)
    # 이번주 / 월별
    week_page(EVS)
    mmap = {}
    for e in EVS:
        if e.get("month"): mmap.setdefault(e["month"], []).append(e)
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
    w("robots.txt", "User-agent: *\nAllow: /\nDisallow: /_cpaad-status.txt\n\nSitemap: %s/sitemap.xml\n" % DOMAIN)
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
