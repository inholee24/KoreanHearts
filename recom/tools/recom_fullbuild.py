"""Re:COM 한글 파일 전체 빌드 (설치기 진입점, 처음부터 빌드 확인용).

  root (= RECOMKO_ROOT) 에 tools/ 와 translation/src/ 가 있어야 한다. 결과: root/mod/recom.
  1 원본 꺼내기 (recom_extract)  2 번역 표 펼치기 (recom_table expand)  3 대사·메뉴·자막·글꼴 (recom_build)
  4 설정 메뉴 (recom_settingmenu)  5 그림 (recom_helpstock, recom_imgtext)  6 검증 (recom_verify)
  KH1 도구 위치는 RECOMKO_KH1 (pkgextract, settingmenu, ctd + translation/src/settingmenu.tsv 를 읽기만 함).
사용: python -I -X utf8 recom_fullbuild.py <게임 폴더> <root> [--keep-data]
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(game, root, log=print, keep_data=False):
    root = os.path.abspath(root)
    os.environ["RECOMKO_ROOT"] = root
    os.environ.pop("RECOMKO_DATA", None)
    os.environ.pop("RECOMKO_SETTINGMENU", None)
    sys.path.insert(0, os.path.join(root, "tools"))
    import recom_extract
    log("1/6 게임 파일에서 필요한 원본 꺼내기")
    log(f"    {recom_extract.extract_all(game, root, log)}개 꺼냄")
    import recom_table
    log("2/6 번역 표 준비")
    recom_table.main("expand")
    import recom_build
    log("3/6 대사·메뉴·자막·글꼴 (몇 분 걸립니다)")
    recom_build.main(True)
    import recom_settingmenu, recom_helpstock, recom_imgtext
    log("4/6 설정 메뉴")
    recom_settingmenu.main(True)
    log("5/6 그림 글자")
    recom_helpstock.main(["apply"])
    recom_imgtext.main(["apply"])
    import recom_verify
    log("6/6 검증")
    if recom_verify.main() != 0:
        raise RuntimeError("검증 실패 (로그 확인)")
    if not keep_data:
        shutil.rmtree(os.path.join(root, "data"), ignore_errors=True)       # 꺼낸 원본은 지운다
    return os.path.join(root, "mod", "recom")


if __name__ == "__main__":
    print(main(sys.argv[1], sys.argv[2], keep_data="--keep-data" in sys.argv))
