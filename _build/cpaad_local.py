# -*- coding: utf-8 -*-
"""cpaad 로컬 수집기 — 사장님 PC(한국 IP)에서 실행합니다.

넷리파이·구글 Apps Script 서버에서 cpaad 접속이 막히는 경우를 위한 수동 경로입니다.
결과를 구글시트 '수동추가' 탭에 그대로 붙여넣으면 다음 빌드에 반영됩니다.

사용법 (명령 프롬프트):
    cd C:\\Users\\hs\\Claude\\Projects\\웹사이트제작\\사이트\\웨딩노트\\_build
    python cpaad_local.py

같은 폴더에 cpaad.py 가 있어야 합니다.
결과 파일: cpaad_수동추가.tsv  (엑셀/시트에 붙여넣기용)
"""
import io, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    import cpaad as CP
except ImportError:
    print("cpaad.py 를 같은 폴더에서 찾을 수 없습니다."); sys.exit(1)

OUT = os.path.join(HERE, "cpaad_수동추가.tsv")
HEADER = ["지역", "행사명", "시작일", "종료일", "장소", "상태", "이미지", "신청링크", "혜택"]


def main():
    print("cpaad 수집 시작:", CP.CPAAD_URL)
    html = CP.fetch_html()
    if not html:
        print()
        print("접속 실패했습니다. 아래를 확인해 주세요.")
        print("  1) 브라우저에서 위 주소가 열리는지")
        print("  2) 회사 방화벽/백신이 파이썬 통신을 막고 있지 않은지")
        print("  3) 열린다면, 그 페이지를 Ctrl+S 로 저장한 뒤")
        print("     python cpaad_local.py 저장한파일.html  로 다시 실행")
        sys.exit(2)
    _write(CP.parse(html))


def from_file(path):
    print("저장된 HTML 사용:", path)
    html = io.open(path, encoding="utf-8", errors="ignore").read()
    _write(CP.parse(html))


def _write(rows):
    today = datetime.date.today().isoformat()
    live = [r for r in rows if (r["end"] or r["start"]) >= today]
    lines = ["\t".join(HEADER)]
    for r in live:
        lines.append("\t".join([
            r["city"], r["name"], r["start"], r["end"], r["place"],
            "모집중", r["img"], r["link"], r.get("benefit", "") or ""]))
    io.open(OUT, "w", encoding="utf-8-sig").write("\n".join(lines) + "\n")
    print()
    print("파싱 %d건 / 진행·예정 %d건" % (len(rows), len(live)))
    print("저장: %s" % OUT)
    print()
    print("다음 순서로 시트에 넣으시면 됩니다.")
    print("  1) cpaad_수동추가.tsv 를 엑셀이나 메모장으로 엽니다")
    print("  2) 머리글 줄을 빼고 데이터만 복사합니다")
    print("  3) 구글시트 '수동추가' 탭 맨 아래에 붙여넣습니다")
    print("  4) 넷리파이가 다음 빌드에서 자동 반영합니다")
    for r in live[:10]:
        print("   -", r["city"], r["name"][:26], r["start"], "~", r["end"])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        from_file(sys.argv[1])
    else:
        main()
