# PyInstaller 설정: 한 개의 실행 파일 (KoreanHearts.exe)
# 빌드: .venv-build\Scripts\pyinstaller installer\koreanhearts.spec --distpath dist --workpath build\pyi
# 필요: third_party\OpenKH.Panacea.dll (OpenKH 릴리스의 같은 이름 파일), <타이틀>\translation\src\*.tsv (kh1/tools/tables.py strip)
import glob, os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
TITLE_DIRS = ["kh1", "recom"]          # 설치기가 빌드하는 타이틀 (app.py 의 BUILDERS 와 맞춘다)
# 실행 파일 모듈로 묶을 도구 (None = tools/*.py 전부). Re:COM 의 분석용 스크립트(capstone·pefile 사용)는 빼고 빌드에 쓰는 것만.
# 도구 파일 자체는 모두 데이터로 묶는다 (content_id 가 받은 것과 같아야 함). 받은 도구는 update.use_tools 로 먼저 쓰인다.
MODULES = {"kh1": None,
           "recom": ["recom_fullbuild", "recom_extract", "recom_paths", "recom_table", "recom_text", "recom_textfile",
                     "recom_ctd", "recom_mvs", "recom_build", "recom_capacity", "recom_font", "recom_fontgrid", "recom_ffmw",
                     "recom_layoutfix", "recom_verify", "recom_settingmenu", "recom_imz", "recom_helpstock", "recom_imgtext"]}

tools, datas, pathex = [], [], []
for t in TITLE_DIRS:
    td = os.path.join(ROOT, t, "tools")
    pathex += [td, os.path.join(td, "re")]
    for p in glob.glob(os.path.join(td, "*.py")):
        m = os.path.splitext(os.path.basename(p))[0]
        if MODULES[t] is not None and m not in MODULES[t]:
            continue
        if not os.path.exists(p):
            raise SystemExit(f"도구 없음: {p}")
        if m in tools:        # 모든 타이틀의 도구가 최상위 모듈로 묶이므로 이름이 겹치면 안 된다
            raise SystemExit(f"도구 모듈 이름 중복: {m} ({t})")
        tools.append(m)
    # 도구 파일 자체도 <타이틀>/tools 로 묶는다. GitHub 에서 받은 것과 같은 구성이라 내용 해시(update.content_id)가 같다
    for dp, dns, fns in os.walk(td):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for f in fns:
            if not f.endswith(".pyc"):
                datas.append((os.path.join(dp, f), os.path.relpath(dp, ROOT).replace("\\", "/")))
    # 번역 표 폴더의 파일 전부 (*.tsv 만이 아님: Re:COM 그림 명세 imgtext.json). content_id 가 폴더 전체를 해시한다
    datas.append((os.path.join(ROOT, t, "translation", "src", "*"), f"{t}/translation/src"))
datas += [(os.path.join(ROOT, "kh1", "tools", "needed_*.txt"), "."),          # 묶인 pkgextract 는 자기 위치(번들 루트)에서 찾는다
          (os.path.join(ROOT, "third_party", "OpenKH.Panacea.dll"), "third_party"),
          (os.path.join(ROOT, "third_party", "licenses", "*.txt"), "licenses"),
          (os.path.join(ROOT, "LICENSE"), "."),
          (os.path.join(ROOT, "NOTICE"), "."),
          (os.path.join(ROOT, "installer", "update.json"), "installer")]
if os.path.exists(os.path.join(ROOT, "build", "source.txt")):   # 묶은 번역의 커밋 (build_release.ps1 이 기록)
    datas.append((os.path.join(ROOT, "build", "source.txt"), "."))

a = Analysis([os.path.join(ROOT, "installer", "app.py")],
             pathex=pathex,
             hiddenimports=tools + ["mem", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageFilter"],
             datas=datas, excludes=["numpy", "matplotlib", "pefile", "capstone"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="KoreanHearts", console=False, upx=False)
