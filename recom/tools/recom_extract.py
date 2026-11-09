"""사용자 게임 파일에서 Re:COM 빌드에 필요한 원본만 꺼낸다 (설치기·처음부터 빌드용, 읽기 전용).

kh1/tools/pkgextract.py 를 고치지 않고 불러 쓴다 (KH1 content hash 보호).
  Image/dt/Recom.hed/.pkg  -> <root>/data/recom        목록 recom/tools/needed_recom.txt (560 개: UK 텍스트·자막·그림·글꼴이 든 원본)
  Image/SettingMenu.hed    -> <root>/data/settingmenu  목록 kh1/tools/needed_settingmenu.txt (KH1 과 같음)
배치는 OpenKH 추출과 같다 (<root>/data/recom/remastered/<원본 이름>/<자산>). 표본 42 개 바이트 동일 확인 (2026-11-06).
사용: python -I -X utf8 recom_extract.py <게임 폴더> [root=recom 폴더]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KH1_TOOLS = os.path.join(os.environ.get("RECOMKO_KH1") or os.path.abspath(os.path.join(HERE, "..", "..", "kh1")), "tools")


def extract_all(game, root, log=print, kh1_tools=KH1_TOOLS):
    sys.path.insert(0, kh1_tools)
    import pkgextract as PX
    total = 0
    for pat, lst, sub in (("Image/dt/Recom.hed", os.path.join(HERE, "needed_recom.txt"), ("data", "recom")),
                          ("Image/SettingMenu.hed", os.path.join(kh1_tools, "needed_settingmenu.txt"), ("data", "settingmenu"))):
        names = [l.strip() for l in open(lst, encoding="utf-8") if l.strip()]
        pk = PX.Pkgs(game, (pat,))
        miss = [n for n in names if not pk.has(n)]
        if miss:
            raise FileNotFoundError(f"게임 파일에서 찾지 못함 ({len(miss)}개): {miss[:5]}")
        out = os.path.join(root, *sub)
        for i, n in enumerate(names):
            PX.extract(pk, n, out)
            if log and (i + 1) % 100 == 0:
                log(f"  원본 꺼내는 중 {i + 1}/{len(names)}")
        total += len(names)
    return total


if __name__ == "__main__":
    root = sys.argv[2] if len(sys.argv) > 2 else os.path.abspath(os.path.join(HERE, ".."))
    print("꺼냄", extract_all(sys.argv[1], root))
