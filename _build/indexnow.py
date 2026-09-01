# -*- coding: utf-8 -*-
"""IndexNow 색인 통보 — 네이버 · 빙 · 공용

넷리파이 빌드 마지막 단계에서 gen.py 다음에 자동 실행됩니다.
  netlify.toml →  command = "python3 _build/gen.py && python3 _build/indexnow.py"

기본 동작: 이번 빌드에서 '새로 생긴 URL' + 고정 허브 몇 개만 통보합니다.
전체 통보: 넷리파이 환경변수에 INDEXNOW_ALL=1 을 넣고 배포하면 전 페이지를 통보합니다.
           (최초 1회만 쓰고 변수를 지우십시오)

수동 실행도 가능합니다:
  python3 _build/indexnow.py --all
"""
import json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from data import DOMAIN, INDEXNOW_KEY

HOST = re.sub(r"^https?://", "", DOMAIN).strip("/")
SITE = os.path.join(HERE, "..", "site")

ENDPOINTS = [("네이버", "https://searchadvisor.naver.com/indexnow"),
             ("빙",     "https://www.bing.com/indexnow"),
             ("공용",   "https://api.indexnow.org/indexnow")]

# 내용이 매일 바뀌므로 항상 함께 통보하는 페이지
HUBS = ["/", "/이번주-웨딩박람회/", "/일정/", "/행사장/"]

FULL = ("--all" in sys.argv) or (os.environ.get("INDEXNOW_ALL", "") == "1")


def read_local():
    p = os.path.join(SITE, "_urls.txt")
    if not os.path.exists(p):
        raise SystemExit("site/_urls.txt 가 없습니다. gen.py 를 먼저 실행하세요.")
    return [u.strip() for u in open(p, encoding="utf-8") if u.strip()]


def read_live():
    """직전 배포본의 _urls.txt — 이것과 비교해 새로 생긴 URL을 찾는다."""
    try:
        req = urllib.request.Request("%s/_urls.txt" % DOMAIN.rstrip("/"),
                                     headers={"User-Agent": "weddingnote-indexnow"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return [u.strip() for u in r.read().decode("utf-8").splitlines() if u.strip()]
    except Exception as e:
        print("  직전 목록을 못 읽었습니다(%s) → 허브만 통보" % e)
        return None


def abs_url(u):
    if u.startswith("http"):
        return u
    return DOMAIN.rstrip("/") + ("" if u.startswith("/") else "/") + u


def submit(batch):
    body = json.dumps({"host": HOST, "key": INDEXNOW_KEY,
                       "keyLocation": "https://%s/%s.txt" % (HOST, INDEXNOW_KEY),
                       "urlList": batch}, ensure_ascii=False).encode("utf-8")
    for name, ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=body,
                    headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=30) as r:
                print("  %-4s HTTP %s (%d건)" % (name, r.status, len(batch)))
        except urllib.error.HTTPError as e:
            print("  %-4s HTTP %s — %s" % (name, e.code,
                  "키 파일이 아직 라이브 반영 전일 수 있습니다" if e.code == 403 else e.reason))
        except Exception as e:
            print("  %-4s 실패: %s" % (name, e))


def main():
    now = read_local()
    prev = None if FULL else read_live()

    if FULL:
        targets = now
        why = "전체(INDEXNOW_ALL)"
    elif prev is None:
        targets = [h for h in HUBS]
        why = "직전 목록 없음 → 허브만"
    else:
        fresh = [u for u in now if u not in set(prev)]
        targets = list(dict.fromkeys(fresh + HUBS))
        why = "신규 %d건 + 허브 %d건" % (len(fresh), len(HUBS))

    urls = [abs_url(u) for u in targets]
    print("IndexNow: host %s | 전체 %d URL 중 통보 %d건 (%s)"
          % (HOST, len(now), len(urls), why))
    if not urls:
        print("  통보할 URL 없음"); return
    for i in range(0, len(urls), 100):
        submit(urls[i:i + 100])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 색인 통보가 실패해도 배포는 성공해야 합니다
        print("IndexNow 건너뜀:", e)
