"""Re:COM exe 색인 (kh1/tools/re/build_index.py 를 그대로 쓰고 대상만 바꾼다. KH1 도구는 고치지 않는다).

사용: openkh_venv python -I -X utf8 recom/tools/recom_re_index.py
출력: D:\\Projects\\openkh\\re_index_recom\\  (functions/calls/refs/strings/ptrs/imports .tsv)
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
# tools/re 를 sys.path 에 넣으면 그 안의 dis.py 가 표준 라이브러리 dis 를 가린다 -> 파일로 직접 불러온다
_spec = importlib.util.spec_from_file_location("build_index", HERE.parents[1] / "kh1" / "tools" / "re" / "build_index.py")
bi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bi)

bi.EXE = Path(r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS Re_Chain of Memories.exe")
bi.OUT = Path(r"D:\Projects\openkh\re_index_recom")
if __name__ == "__main__":
    bi.main()
