"""설정 메뉴 (Image/SettingMenu.pkg, 1.5 공용) 를 Re:COM 용 mod 에 적용.

KH1 도구 kh1/tools/settingmenu.py 를 고치지 않고 불러 쓴다 (KH1 content hash 보호).
  번역 = KH1 설정 메뉴 번역 (kh1/translation/src/settingmenu.tsv, key+ko)
       + Re:COM 키 설정 (recom/translation/src/settingmenu_recom.tsv, 0036:8000~8018)
  원문은 원본 ct00100.ctd 에서 채워 임시 전체 표(key, en, ko)를 만든 뒤 KH1 도구의 main 에 넘긴다.
  결과: mod/recom/ctd/ct00100.ctd, mod/recom/font/menufont.{inf,cod,tm2}  ("uk/" 없음! 게임 확인 2026-11-09)
  (KH1 은 mod/kh1/uk/... 이지만 Re:COM 은 Panacea 의 경로 계산이 달라 uk/ 가 떨어진다. 아래 main 주석)
원본: 환경 변수 RECOMKO_SETTINGMENU (IdxImg hed extract 결과의 original 폴더), 없으면 recom/data/settingmenu.
사용: python -I -X utf8 recom_settingmenu.py [--apply]
"""
import importlib.util, os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_paths as P

# KH1 도구·설정 메뉴 표 위치: 환경 변수 RECOMKO_KH1 (설치기: 번역 받은 곳의 kh1 폴더), 없으면 저장소의 kh1/
KH1 = os.environ.get("RECOMKO_KH1") or os.path.abspath(os.path.join(P.ROOT, "..", "kh1"))
KH1_TOOLS = os.path.join(KH1, "tools")
KH1_SRC = os.path.join(KH1, "translation", "src", "settingmenu.tsv")
RECOM_SRC = os.path.join(P.TR, "src", "settingmenu_recom.tsv")
SRC = os.environ.get("RECOMKO_SETTINGMENU") or os.path.join(P.ROOT, "data", "settingmenu")
TMP = os.path.join(P.TR, "build", "settingmenu_full.tsv")


def read_ko(path):
    rows = {}
    for ln in open(path, encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            k, ko = ln.split("\t")[:2]
            rows[k] = ko
    return rows


def main(apply):
    sys.path.insert(0, KH1_TOOLS)
    spec = importlib.util.spec_from_file_location("kh1_settingmenu", os.path.join(KH1_TOOLS, "settingmenu.py"))
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    ctd = sm.ctd
    d = ctd.parse(open(os.path.join(SRC, sm.CTD_REL), "rb").read())
    en = {f"{m['flags']:04x}:{m['id']:04x}": ctd.show(m["text"]) for m in d["msgs"]}
    ko = read_ko(KH1_SRC)
    rc = read_ko(RECOM_SRC)
    dup = set(ko) & set(rc)
    if dup:
        sys.exit(f"KH1 표와 겹치는 키: {sorted(dup)}")
    ko.update(rc)
    miss = sorted(set(ko) - set(en))
    if miss:
        sys.exit(f"원본에 없는 키: {miss}")
    os.makedirs(os.path.dirname(TMP), exist_ok=True)
    with open(TMP, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("key\ten\tko\n")
        for k in sorted(ko):
            fp.write(f"{k}\t{en[k]}\t{ko[k]}\n")
    stage = os.path.join(P.TR, "build", "settingmenu_mod")      # KH1 도구는 여기에 uk/... 로 쓴다
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    sm.SRC, sm.MOD, sm.TSV = SRC, stage, TMP
    print(f"KH1 {len(ko) - len(rc)}줄 + Re:COM {len(rc)}줄 -> {P.MOD}")
    sm.main(apply)
    if apply:
        # Re:COM 은 SettingMenu 파일을 "C:/hd28/STEAM/SettingMenu/WIN/uk/ctd/ct00100.ctd" 로 요청하고,
        # Panacea 는 요청 이름에서 게임 기본 경로("C:/hd28/STEAM/dt/KHCReSource/BIN", 32자)+1 자를 떼어
        # mod/recom/ 뒤에 붙인다 -> "ctd/ct00100.ctd", "font/menufont.*" (게임 확인 2026-11-09, file-formats.md)
        src_uk = os.path.join(stage, "uk")
        for dp, _, fns in os.walk(src_uk):
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), src_uk)
                out = os.path.join(P.MOD, rel)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                shutil.copyfile(os.path.join(dp, fn), out)
                print("  ->", os.path.relpath(out, P.MOD).replace("\\", "/"))
        old = os.path.join(P.MOD, "uk")                       # 예전 빌드가 쓴 자리 (게임이 읽지 않음)
        if os.path.isdir(old):
            shutil.rmtree(old)


if __name__ == "__main__":
    main("--apply" in sys.argv)
