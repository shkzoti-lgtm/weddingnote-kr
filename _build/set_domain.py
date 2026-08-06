# -*- coding: utf-8 -*-
"""도메인 교체 + 전체 재빌드 (한 번에)
사용법:  python3 set_domain.py 웨딩페어노트.kr
        python3 set_domain.py https://mywedding.co.kr
        python3 set_domain.py --naver 소유확인코드 --google 소유확인코드
"""
import sys, re, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.py")

def patch(key, value):
    s = open(DATA, encoding="utf-8").read()
    s2 = re.sub(r'^(%s\s*=\s*)"[^"]*"' % key, lambda m: m.group(1)+'"%s"'%value, s, count=1, flags=re.M)
    if s2 == s:
        print("  경고: %s 를 찾지 못했습니다" % key); return False
    open(DATA, "w", encoding="utf-8").write(s2)
    print("  %s → %s" % (key, value)); return True

args = sys.argv[1:]
if not args:
    print(__doc__); sys.exit(0)

i = 0
while i < len(args):
    a = args[i]
    if a == "--naver":   patch("NAVER_VERIFY", args[i+1]); i += 2
    elif a == "--google": patch("GOOGLE_VERIFY", args[i+1]); i += 2
    elif a == "--ga4":    patch("GA4_ID", args[i+1]); i += 2
    elif a == "--site":   patch("SITE", args[i+1]); i += 2
    else:
        d = a.strip().rstrip("/")
        if not d.startswith("http"): d = "https://" + d
        patch("DOMAIN", d); i += 1

print("\n재빌드 중…")
subprocess.run([sys.executable, os.path.join(HERE, "gen.py")], check=True)
print("\n완료. site 폴더를 넷리파이에 드래그하세요.")
print("배포 후:  python3 indexnow.py   (색인 즉시 요청)")
