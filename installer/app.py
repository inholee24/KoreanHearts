"""킹덤 하츠 1 (HD 1.5+2.5 ReMIX, PC) 한글 패치 설치·실행 프로그램.

설치: 사용자의 게임 파일에서 필요한 원본을 꺼내 한글 파일을 이 PC 에서 만든다 (배포 파일에 원본 데이터 없음).
      결과는 <게임 폴더>/KH1Korean/mod/kh1, Panacea(OpenKH, DBGHELP.dll) 가 실행 중 원본 대신 읽는다.
실행: 게임을 켜고, 이 창이 열려 있는 동안 메모리 패치(대화창 글꼴 배치·시스템 글꼴 표 확장)를 붙인다.
"""
import ctypes, json, os, queue, re, shutil, subprocess, sys, threading, time, traceback
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

VERSION = "0.1.0"
APP_ID = "2552430"
GAME_DIR_NAME = "KINGDOM HEARTS -HD 1.5+2.5 ReMIX-"
WORK_NAME = "KH1Korean"
BASE = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
TOOLS = os.path.join(BASE, "tools")
sys.path[:0] = [TOOLS, os.path.join(TOOLS, "re")]     # 개발 실행용. 실행 파일에서는 도구가 이미 묶여 있다
FONTS = [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf"]
NOTICE_KO = """[사용 전 확인]
- 이 프로그램은 패치일 뿐이며 게임을 포함하거나 배포하지 않습니다. 정품 게임(Steam 판)이 필요합니다.
- 비공식 팬 번역입니다. Square Enix, Disney 와 관계가 없고 공식 지원 대상이 아닙니다.
- 한글 파일은 이 PC 의 게임 파일로 만들어집니다. 만들어진 파일(KH1Korean 폴더)은 게임 데이터를 바탕으로 하므로 다른 사람에게 공유하거나 재배포하지 마세요.
- 게임 원본 파일은 바꾸지 않지만, 모드 로더(Panacea)를 설치하고 게임 실행 중 메모리를 고칩니다. 이용약관 관련 판단과 사용에 따른 책임은 사용자에게 있습니다.
- 아무런 보증 없이 제공됩니다 (Apache License 2.0). 세이브 데이터는 미리 백업하세요.
- 이 프로그램은 인터넷으로 정보를 보내지 않습니다.
"""


# ---------------------------------------------------------------- 게임 폴더 찾기
def steam_libraries():
    libs = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            libs.append(winreg.QueryValueEx(k, name)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    out = []
    for steam in libs:
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        out.append(steam)
        if os.path.exists(vdf):
            out += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="ignore").read())]
    return list(dict.fromkeys(os.path.normpath(p) for p in out))


def is_game_dir(p):
    return bool(p) and os.path.exists(os.path.join(p, "KINGDOM HEARTS FINAL MIX.exe")) and os.path.isdir(os.path.join(p, "Image", "dt"))


def find_game():
    for lib in steam_libraries():
        p = os.path.join(lib, "steamapps", "common", GAME_DIR_NAME)
        if is_game_dir(p):
            return p
    return ""


# ---------------------------------------------------------------- 설치 / 제거
def work_dir(game):
    return os.path.join(game, WORK_NAME)


def state_path(game):
    return os.path.join(work_dir(game), "install.json")


def load_state(game):
    try:
        return json.load(open(state_path(game), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def install(game, log):
    game = os.path.normpath(game)
    for f in FONTS:
        if not os.path.exists(f):
            raise RuntimeError(f"글꼴이 없습니다: {f} (Windows 기본 글꼴 '맑은 고딕')")
    work = work_dir(game)
    os.makedirs(work, exist_ok=True)
    old = load_state(game) or {}
    # 번역 표 (원문 없음) 를 작업 폴더로
    shutil.rmtree(os.path.join(work, "translation"), ignore_errors=True)
    shutil.copytree(os.path.join(BASE, "translation", "src"), os.path.join(work, "translation", "src"))
    for d in ("data", "mod"):
        shutil.rmtree(os.path.join(work, d), ignore_errors=True)
    os.environ["KH1KO_ROOT"] = work
    sys.path.insert(0, TOOLS)
    import pkgextract
    log("1/6 게임 파일에서 필요한 원본 꺼내기 (약 2GB, 1분 안팎)")
    n = pkgextract.extract_all(game, work, log)
    log(f"    {n}개 꺼냄")
    import tables
    log("2/6 번역 표 준비")
    tables.main("expand")
    import build_ko
    log("3/6 대사·메뉴 한글 파일 만들기 (몇 분 걸립니다)")
    build_ko.main(True, "jp")
    import imgtext, settingmenu, evdl_patch
    log("4/6 그림 글자·설정 메뉴·스크립트")
    imgtext.main(True, [])
    settingmenu.main(True)
    evdl_patch.main(True)
    import verify_build
    log("5/6 검증")
    if verify_build.main() != 0:
        raise RuntimeError("검증 실패 (로그 확인)")
    log("6/6 정리 및 Panacea 설정")
    shutil.rmtree(os.path.join(work, "data"), ignore_errors=True)      # 꺼낸 원본은 지운다
    st = {"version": VERSION, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
          "dll_installed_by_us": old.get("dll_installed_by_us", False),
          "settings_backup": old.get("settings_backup")}
    dll = os.path.join(game, "DBGHELP.dll")
    if not os.path.exists(dll):
        shutil.copy(os.path.join(BASE, "third_party", "OpenKH.Panacea.dll"), dll)
        st["dll_installed_by_us"] = True
        log("    Panacea(DBGHELP.dll) 설치")
    else:
        log("    기존 DBGHELP.dll(Panacea) 사용")
    sett = os.path.join(game, "panacea_settings.txt")
    if os.path.exists(sett) and not st["settings_backup"]:
        bk = os.path.join(work, "panacea_settings.backup.txt")
        shutil.copy(sett, bk)
        st["settings_backup"] = bk
        log("    기존 panacea_settings.txt 백업")
    with open(sett, "w", encoding="utf-8", newline="\r\n") as fp:
        fp.write(f"mod_path={os.path.join(work, 'mod')}\nenable_cache=true\n")
    json.dump(st, open(state_path(game), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("설치 완료. '게임 실행' 으로 켜세요.")


def uninstall(game, log):
    st = load_state(game)
    if not st:
        raise RuntimeError("설치 기록이 없습니다.")
    sett = os.path.join(game, "panacea_settings.txt")
    if st.get("settings_backup") and os.path.exists(st["settings_backup"]):
        shutil.copy(st["settings_backup"], sett)
        log("panacea_settings.txt 를 설치 전으로 되돌림")
    elif os.path.exists(sett):
        os.remove(sett)
    if st.get("dll_installed_by_us"):
        try:
            os.remove(os.path.join(game, "DBGHELP.dll"))
            log("DBGHELP.dll 삭제")
        except OSError as e:
            log(f"DBGHELP.dll 삭제 실패 (게임이 켜져 있으면 끄고 다시): {e}")
    shutil.rmtree(work_dir(game), ignore_errors=True)
    log("제거 완료.")


# ---------------------------------------------------------------- 메모리 패치
_patcher = None


def start_patcher(game, log):
    global _patcher
    if _patcher and _patcher.is_alive():
        return
    os.environ["KH1KO_ROOT"] = work_dir(game)
    sys.path.insert(0, os.path.join(TOOLS, "re"))
    import mem

    def run():
        while True:
            try:
                mem.tex2x_main(10 ** 9, False, True)
            except BaseException as e:
                log(f"메모리 패치 오류: {e!r}. 다시 시도")
                time.sleep(2)
    _patcher = threading.Thread(target=run, daemon=True)
    _patcher.start()
    log("메모리 패치 대기 중 (게임을 켜면 자동으로 붙습니다. 이 창을 닫지 마세요)")


# ---------------------------------------------------------------- 화면
class Out:
    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s.strip():
            self.q.put(s.rstrip("\n"))

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        sys.stdout = sys.stderr = Out(self.q)
        root.title(f"킹덤 하츠 1 한글 패치 {VERSION}")
        root.geometry("720x480")
        top = tk.Frame(root); top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text="게임 폴더").pack(side="left")
        self.game = tk.StringVar(value=find_game())
        tk.Entry(top, textvariable=self.game).pack(side="left", fill="x", expand=True, padx=6)
        tk.Button(top, text="찾아보기", command=self.browse).pack(side="left")
        btn = tk.Frame(root); btn.pack(fill="x", padx=10)
        self.b_inst = tk.Button(btn, text="한글 패치 설치", width=16, command=self.install)
        self.b_play = tk.Button(btn, text="게임 실행", width=16, command=self.play)
        self.b_un = tk.Button(btn, text="제거", width=10, command=self.remove)
        for b in (self.b_inst, self.b_play, self.b_un):
            b.pack(side="left", padx=4)
        self.status = tk.Label(root, anchor="w"); self.status.pack(fill="x", padx=12, pady=4)
        self.log = scrolledtext.ScrolledText(root, height=18, state="disabled", wrap="word"); self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.refresh()
        self.say(NOTICE_KO)
        root.after(100, self.pump)

    def install(self):
        if messagebox.askyesno("설치 전 확인", NOTICE_KO + "\n위 내용을 확인했고 동의합니까?"):
            self.task(install)

    def say(self, s):
        self.q.put(s)

    def pump(self):
        while not self.q.empty():
            s = self.q.get()
            self.log.configure(state="normal"); self.log.insert("end", s + "\n"); self.log.see("end"); self.log.configure(state="disabled")
        self.root.after(100, self.pump)

    def browse(self):
        p = filedialog.askdirectory(title="KINGDOM HEARTS -HD 1.5+2.5 ReMIX- 폴더 선택")
        if p:
            self.game.set(os.path.normpath(p)); self.refresh()

    def refresh(self):
        g = self.game.get()
        if not is_game_dir(g):
            self.status.config(text="게임 폴더를 찾지 못했습니다. '찾아보기' 로 지정하세요.")
            return
        st = load_state(g)
        self.status.config(text=f"설치됨 (버전 {st['version']}, {st['time']})" if st else "설치 안 됨")

    def task(self, fn, after=None):
        g = self.game.get()
        if not is_game_dir(g):
            messagebox.showerror("게임 폴더", "게임 폴더가 올바르지 않습니다."); return
        for b in (self.b_inst, self.b_play, self.b_un):
            b.config(state="disabled")

        def run():
            try:
                fn(g, self.say)
            except BaseException as e:
                self.say("오류: " + "".join(traceback.format_exception_only(type(e), e)).strip())
                self.say(traceback.format_exc())
            finally:
                self.root.after(0, self.done)
        threading.Thread(target=run, daemon=True).start()

    def done(self):
        for b in (self.b_inst, self.b_play, self.b_un):
            b.config(state="normal")
        self.refresh()

    def play(self):
        g = self.game.get()
        if not load_state(g):
            messagebox.showinfo("게임 실행", "먼저 '한글 패치 설치' 를 하세요."); return
        start_patcher(g, self.say)
        os.startfile(f"steam://rungameid/{APP_ID}")
        self.say("게임을 켭니다. 런처에서 KINGDOM HEARTS FINAL MIX 를 고르세요.")

    def remove(self):
        if messagebox.askyesno("제거", "한글 패치를 제거할까요?"):
            self.task(uninstall)


def main():
    # 화면 없이 (시험·자동화용): --install|--uninstall|--play <게임 폴더> <로그 파일>
    if len(sys.argv) >= 4 and sys.argv[1] in ("--install", "--uninstall", "--play"):
        with open(sys.argv[3], "w", encoding="utf-8") as fp:
            sys.stdout = sys.stderr = fp

            def log(s):
                fp.write(s + "\n"); fp.flush()
            try:
                if sys.argv[1] == "--install":
                    install(sys.argv[2], log)
                elif sys.argv[1] == "--uninstall":
                    uninstall(sys.argv[2], log)
                else:                    # 게임을 켜고, 게임이 꺼질 때까지 메모리 패치
                    start_patcher(os.path.normpath(sys.argv[2]), log)
                    os.startfile(f"steam://rungameid/{APP_ID}")
                    seen = False
                    while True:
                        time.sleep(2)
                        import mem
                        alive = mem.find_pid() is not None
                        seen = seen or alive
                        if seen and not alive:
                            break
            except BaseException:
                log(traceback.format_exc())
                sys.exit(1)
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
