# weddingnote.kr

전국 웨딩박람회 일정 사이트. 구글시트를 원본으로 정적 사이트를 생성합니다.

## 구조
- `_build/gen.py` — 사이트 생성기 (배포 시 넷리파이가 실행)
- `_build/data.py` — 도메인·지역·사이트 설정
- `_build/events.py` — 구글시트에서 행사 데이터 로드 (실패 시 캐시 사용)
- `_build/events_cache.psv` — 백업 캐시
- `_build/static/` — CSS·JS·파비콘 (그대로 복사됨)
- `site/` — 생성 결과물 (git에 올리지 않음, 넷리파이가 빌드 시 생성)

## 배포
넷리파이가 push 또는 빌드훅 호출 시 `python3 _build/gen.py` 를 실행하고
생성된 `site/` 를 배포합니다. 매 빌드마다 시트 최신 데이터 반영 + sitemap lastmod 갱신.

## 로컬 실행
```
python3 _build/gen.py
```
