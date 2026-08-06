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

def aeo_block(loc, region):
    """AEO 답변 블록: 요약 → 확인방법(ol) → 주의사항"""
    return f"""<div class="aeo">
  <h2>{loc} 웨딩박람회, 언제 어디서 열리나요?</h2>
  <p class="ans">{loc}에서는 {VENUE.get(loc,'주요 컨벤션센터와 백화점 특별행사장')}을 중심으로
  <b>거의 매주 주말</b> 웨딩박람회가 열립니다. 개최 주최와 규모에 따라 참여 업체가 달라지므로
  실제 일정과 혜택은 아래 최신 목록에서 확인하는 것이 정확합니다.</p>
  <p class="ans-sub"><b>무료 초대권 신청 방법</b></p>
  <ol>
    <li>아래 {loc} 일정 목록에서 방문할 박람회를 고릅니다.</li>
    <li>초대권 신청 버튼을 눌러 이름과 연락처를 남깁니다.</li>
    <li>예산 상한과 희망 예식 날짜를 정리해 커플이 함께 방문합니다.</li>
  </ol>
  <p class="pnote">※ 일정과 혜택은 주최 측 사정에 따라 변경될 수 있으며, 실제 견적은 상담 조건에 따라 달라집니다.</p>
</div>"""

def compare_table(loc):
    return f"""<div class="tablewrap"><table>
<caption>{loc} 웨딩박람회 유형별 비교</caption>
<thead><tr><th>유형</th><th>규모</th><th>특징</th><th>이런 분께</th></tr></thead>
<tbody>
<tr><td>컨벤션센터형</td><td>대형</td><td>참여 업체가 많아 한 번에 비교 가능</td><td>처음 준비를 시작한 예비부부</td></tr>
<tr><td>백화점·몰형</td><td>중형</td><td>접근성이 좋고 브랜드 중심 상담</td><td>퇴근 후·주말 짧게 둘러볼 분</td></tr>
<tr><td>업체 사옥형</td><td>소형</td><td>대기가 짧고 상담이 밀착형</td><td>구체적 견적을 원하는 분</td></tr>
<tr><td>허니문·혼수 특화</td><td>중형</td><td>신혼여행·가전 중심 구성</td><td>예식장은 정한 분</td></tr>
</tbody></table></div>"""
