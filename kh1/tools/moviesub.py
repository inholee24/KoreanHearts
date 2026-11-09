"""영상(KH1Movie/*.mp4) 한국어 자막.

게임에는 영상 자막 기능이 있다 (exe 분석 2026-11-03, docs/exe-analysis.md 7절):
  표 movie_sub_tbl 0x4e5c80 = 포인터 [영상 5 x 언어 7] (영상 OPN END ENX LOP EXM, 언어 0 일본 1 US 2 UK 3 독 4 불 5 서 6 이)
  항목 0x20B: u32 종류, f32 시작, f32 끝 (1/60 초), u32 0, u64 글자열 포인터, u32 길이(끝 00 포함), u32 줄 수. 끝 = (0, -1, -1)
  영상 열기 0x18eb20 이 [영상*7 + 언어] 를 0x234e600 에 두고, 0x18f25a 가 시각이 되면 0x18f380 이 메시지를 만들어
  대화창 글꼴로 그린다 (글자 코드는 대사와 같다). 영어 칸은 END 만 있고 OPN(소라 독백)·EXM·LOP 는 비어 있다.
번역 표 translation/src/movie_sub.tsv (키, 종류, 시작, 끝, 한글; 시각은 exe 의 다른 언어 칸 값). 원문 없음.
build_ko 가 글자를 대화창 글꼴에 배정하고 translation/build/movie_sub.json 을 쓴다.
tools/re/mem.py (tex2x jp) 가 게임 안에 표를 만들어 영어 칸(1, 2)에 연결한다.
"""
import json, os
import evmsg

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "translation", "src", "movie_sub.tsv")
OUT = os.path.join(ROOT, "translation", "build", "movie_sub.json")
MOVIES = ["OPN", "END", "ENX", "LOP", "EXM"]


def read_tsv(path=SRC):
    rows = []
    with open(path, encoding="utf-8") as f:
        head = f.readline().rstrip("\n").split("\t")
        for line in f:
            r = dict(zip(head, line.rstrip("\n").split("\t")))
            name, i = r["key"].split(":")
            rows.append({"movie": name, "i": int(i), "kind": int(r["kind"]),
                         "start": float(r["start"]), "end": float(r["end"]), "ko": r["ko"]})
    return rows


def texts(rows=None):
    return [r["ko"] for r in (rows or read_tsv())]


def build(gbytes, rows=None):
    """gbytes: {글자: 코드 bytes}. -> {영상: [{kind, start, end, text(hex, 끝 00 포함), lines}]}"""
    out = {}
    for r in sorted(rows or read_tsv(), key=lambda r: (MOVIES.index(r["movie"]), r["i"])):
        b = evmsg.encode(r["ko"], gbytes) + b"\x00"
        out.setdefault(r["movie"], []).append({"kind": r["kind"], "start": r["start"], "end": r["end"],
                                               "text": b.hex(), "lines": r["ko"].count("\\n") + 1})
    return out


def write(data, path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
