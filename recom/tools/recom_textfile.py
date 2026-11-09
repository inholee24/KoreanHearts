"""번역 대상 텍스트 파일 종류별 읽기·쓰기 (CTD .ctdl / 영상 자막 MVS).

kind(rel)  -> "ctd" | "mvs"
parse(rel, b) -> {"msgs": [...], ...}   build(rel, b, d, msgs) -> bytes
글꼴 (file-formats.md): MVS 자막은 evtfont 로만 그려진다 (exe 0x2995A0 -> 0x2B1420 플래그 0x300B 비트 12, 확정).
CTD 는 창 스타일/호출부에 따라 sys 또는 evt -> 두 글꼴 모두에 있어야 한다.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd, recom_mvs


def kind(rel):
    return "mvs" if os.path.basename(rel).startswith("UK_MVS") else "ctd"


def parse(rel, b):
    return recom_mvs.parse(b) if kind(rel) == "mvs" else recom_ctd.parse(b)


def build(rel, b, d, msgs):
    return recom_mvs.build(b, d, msgs) if kind(rel) == "mvs" else recom_ctd.build(b, d, msgs)


def fonts_of(rel):
    """이 파일의 글이 그려질 수 있는 글꼴."""
    return ("evt",) if kind(rel) == "mvs" else ("sys", "evt")
