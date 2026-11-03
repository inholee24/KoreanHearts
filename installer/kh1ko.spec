# PyInstaller 설정: 한 개의 실행 파일 (KH1Korean.exe)
# 빌드: .venv-build\Scripts\pyinstaller installer\kh1ko.spec --distpath dist --workpath build\pyi
# 필요: third_party\OpenKH.Panacea.dll (OpenKH 릴리스의 같은 이름 파일), translation\src\*.tsv (tools/tables.py strip)
import glob, os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
tools = [os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, "tools", "*.py"))]
datas = [(os.path.join(ROOT, "translation", "src", "*.tsv"), "translation/src"),
         (os.path.join(ROOT, "tools", "needed_*.txt"), "."),          # pkgextract 는 자기 위치(번들 루트)에서 찾는다
         (os.path.join(ROOT, "tools", "needed_*.txt"), "tools"),
         (os.path.join(ROOT, "third_party", "OpenKH.Panacea.dll"), "third_party"),
         (os.path.join(ROOT, "third_party", "LICENSE-OpenKH.txt"), "third_party"),
         (os.path.join(ROOT, "third_party", "NOTICE-OpenKH.txt"), "third_party")]

a = Analysis([os.path.join(ROOT, "installer", "app.py")],
             pathex=[os.path.join(ROOT, "tools"), os.path.join(ROOT, "tools", "re")],
             hiddenimports=tools + ["mem", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageFilter"],
             datas=datas, excludes=["numpy", "matplotlib", "pefile", "capstone"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="KH1Korean", console=False, upx=False)
