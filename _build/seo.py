# -*- coding: utf-8 -*-
"""head / JSON-LD / AEO 블록 — SEO 문서 규격 그대로"""
import json, html
from data import *

def esc(s): return html.escape(str(s), quote=True)

def head(title, desc, keywords, url, extra_ld=None):
    v=[]
    if NAVER_VERIFY: v.append('<meta name="naver-site-verification" content="%s">'%NAVER_VERIFY)
    if GOOGLE_VERIFY: v.append('<meta name="google-site-verification" content="%s">'%GOOGLE_VERIFY)
    ga=""
    if GA4_ID:
        ga=('<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>'
            '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
            'gtag("js",new Date());gtag("config","%s",{"send_page_view":true});</script>'%(GA4_ID,GA4_ID))
    ld = "".join('<script type="application/ld+json">%s</script>'%x for x in (extra_ld or []))
    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{''.join(v)}
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(keywords)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="author" content="{SITE}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMAIN}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/favicon.ico">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#12233d">
<link rel="alternate" type="application/rss+xml" title="{SITE} RSS" href="/rss.xml">
<link rel="stylesheet" href="/assets/style.css">
{ga}{ld}
</head><body>"""

def ld_faq(faqs):
    return json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faqs]},
        ensure_ascii=False)

def ld_breadcrumb(items):
    return json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":n,"item":u} for i,(n,u) in enumerate(items)]},
        ensure_ascii=False)

def ld_howto(loc):
    return json.dumps({"@context":"https://schema.org","@type":"HowTo",
      "name":"%s 웨딩박람회 무료 초대권 신청 방법"%loc,
      "totalTime":"PT5M",
      "step":[
        {"@type":"HowToStep","position":1,"name":"일정 확인",
         "text":"%s에서 열리는 웨딩박람회 일정과 장소를 확인합니다."%loc},
        {"@type":"HowToStep","position":2,"name":"초대권 신청",
         "text":"원하는 박람회의 무료 초대권 신청 버튼을 눌러 이름과 연락처를 남깁니다."},
        {"@type":"HowToStep","position":3,"name":"방문 준비",
         "text":"예산 상한과 희망 예식 날짜를 정리해 커플이 함께 방문합니다."}]},
        ensure_ascii=False)

def ld_website():
    return json.dumps({"@context":"https://schema.org","@type":"WebSite","name":SITE,
      "url":DOMAIN+"/","inLanguage":"ko-KR",
      "publisher":{"@type":"Organization","name":"에이치에스컴퍼니"}}, ensure_ascii=False)

def ld_itemlist(loc, rows):
    return json.dumps({"@context":"https://schema.org","@type":"ItemList",
      "name":"%s 웨딩박람회 일정"%loc,
      "itemListElement":[{"@type":"ListItem","position":i+1,"name":n} for i,n in enumerate(rows)]},
      ensure_ascii=False)

import evdata as ED

def aeo_block(loc, region):
    """AEO 답변 블록 — 지역 해시로 문항·답변·절차를 다르게 배정한다."""
    v = VENUE.get(loc, "주요 컨벤션센터와 백화점 특별행사장")
    q     = ED.pick(ED.AEO_Q,      loc, "aq").format(loc=loc)
    ans   = ED.pick(ED.AEO_ANS,    loc, "aa").format(loc=loc, v=v)
    sh    = ED.pick(ED.AEO_STEP_H, loc, "ah")
    steps = ED.pick(ED.AEO_STEPS,  loc, "as")
    note  = ED.pick(ED.AEO_NOTE,   loc, "an")
    li = "".join("<li>%s</li>" % s.format(loc=loc) for s in steps)
    return f"""<div class="aeo">
  <h2>{q}</h2>
  <p class="ans">{ans}</p>
  <p class="ans-sub"><b>{sh}</b></p>
  <ol>{li}</ol>
  <p class="pnote">{note}</p>
</div>"""

def compare_table(loc):
    cap = ED.pick(ED.CMP_CAP, loc, "cc").format(loc=loc)
    hd  = ED.pick(ED.CMP_HEAD, loc, "ch")
    order = ED.sample(list(range(len(ED.CMP_ROWS))), loc, len(ED.CMP_ROWS), "cr")
    rows = ""
    for i in order:
        name, size, feats, fors = ED.CMP_ROWS[i]
        rows += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            name, size, ED.pick(feats, loc, "cf%d" % i), ED.pick(fors, loc, "ct%d" % i))
    return f"""<div class="tablewrap"><table>
<caption>{cap}</caption>
<thead><tr><th>{hd[0]}</th><th>{hd[1]}</th><th>{hd[2]}</th><th>{hd[3]}</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""
