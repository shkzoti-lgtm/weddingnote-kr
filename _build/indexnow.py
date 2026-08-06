# -*- coding: utf-8 -*-
"""배포 후 실행: 색인 즉시 요청(IndexNow · 네이버/빙 지원)
   python3 indexnow.py"""
import json, urllib.request, os, re
from data import DOMAIN, INDEXNOW_KEY

host = re.sub(r'^https?://', '', DOMAIN).strip('/')
urls = [u.strip() for u in open(os.path.join(os.path.dirname(__file__),"..","site","_urls.txt"),
        encoding="utf-8") if u.strip()]

def submit(batch):
    body = json.dumps({"host":host,"key":INDEXNOW_KEY,
        "keyLocation":"https://%s/%s.txt"%(host,INDEXNOW_KEY),"urlList":batch}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
        headers={"Content-Type":"application/json; charset=utf-8"})
    try:
        print("HTTP", urllib.request.urlopen(req, timeout=20).status, "| %d URL 제출"%len(batch))
    except Exception as e:
        print("실패:", e, "\n→ 403이면 키 파일이 아직 라이브 반영 안 된 것. 1~2분 후 재시도.")

if __name__ == "__main__":
    print("host:", host, "| 총 URL:", len(urls))
    for i in range(0, len(urls), 100):
        submit(urls[i:i+100])
