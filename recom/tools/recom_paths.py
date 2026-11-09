"""Re:COM 도구 공통 경로.

ROOT  = recom/ (도구 폴더의 상위). 설치기는 환경 변수 RECOMKO_ROOT 로 작업 폴더를 준다.
DATA  = 원본 데이터 (OpenKH 추출 형식: <경로>, remastered/<경로>/<언어>_*). 환경 변수 RECOMKO_DATA, 없으면 ROOT/data/recom.
MOD   = 결과물 ROOT/mod/recom (Panacea mod_path 아래 recom/ 과 같은 구성).
TR    = 번역 표 폴더 ROOT/translation (src/ = 저장소용 key+ko, *.tsv = 원문 포함 전체 표, build/ = 빌드 산출 확인용).
"""
import os

ROOT = os.environ.get("RECOMKO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.environ.get("RECOMKO_DATA") or os.path.join(ROOT, "data", "recom")
MOD = os.path.join(ROOT, "mod", "recom")
TR = os.path.join(ROOT, "translation")
SYS = "remastered/SYS/0001"


def _uk(data, pred):
    data = data or DATA
    out = []
    for dp, dns, fns in os.walk(os.path.join(data, "remastered")):
        for f in fns:
            if f.startswith("UK_") and pred(f):
                out.append(os.path.relpath(os.path.join(dp, f), data).replace(os.sep, "/"))
    return sorted(out)


def uk_ctdl(data=None):
    """원본의 UK .ctdl 상대 경로 목록 (정렬, '/' 구분)."""
    return _uk(data, lambda f: f.endswith(".ctdl"))


def uk_mvs(data=None):
    """원본의 UK 영상 자막 UK_MVS*.binl 상대 경로 목록 (recom_mvs.py, 97개)."""
    return _uk(data, lambda f: f.startswith("UK_MVS") and f.endswith(".binl"))


def uk_text(data=None):
    """번역 대상 텍스트 파일 전부 (.ctdl + MVS)."""
    return sorted(uk_ctdl(data) + uk_mvs(data))


def is_text_file(name):
    return name.startswith("UK_") and (name.endswith(".ctdl") or (name.startswith("UK_MVS") and name.endswith(".binl")))
