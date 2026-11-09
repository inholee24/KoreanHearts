"""킹덤 하츠 한글 패치 (HD 1.5+2.5 ReMIX, PC) 설치·실행 프로그램. 타이틀별로 설치·제거를 고른다.

설치: 사용자의 게임 파일에서 필요한 원본을 꺼내 한글 파일을 이 PC 에서 만든다 (배포 파일에 원본 데이터 없음).
      결과는 <게임 폴더>/KoreanHearts/mod/<타이틀>, Panacea(OpenKH, DBGHELP.dll) 가 실행 중 원본 대신 읽는다.
      Panacea 와 panacea_settings.txt 는 모든 타이틀이 함께 쓴다. 마지막 타이틀을 제거할 때 설치 전으로 되돌린다.
실행: 게임을 켜고, 이 창이 열려 있는 동안 KH1 메모리 패치(대화창 글꼴 배치·시스템 글꼴 표 확장)를 붙인다.

작업 폴더 <게임 폴더>/KoreanHearts:
  install.json                  {"version", "shared": {dll_installed_by_us, settings_backup}, "titles": {id: {...}}}
  panacea_settings.backup.txt   설치 전 panacea_settings.txt (있었을 때만)
  mod/<id>/                     Panacea 가 읽는 결과물 (mod_path = 이 mod 폴더)
  <id>/                         타이틀별 번역 표·도구 사본, 빌드 중간물 (KH1 메모리 패치가 쓴다)
0.3.x 가 만든 <게임 폴더>/KH1Korean 설치본은 처음 볼 때 이 구조로 옮긴다 (migrate_legacy).
"""
import ctypes, json, os, queue, re, shutil, subprocess, sys, threading, time, traceback
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import selfupdate, update

VERSION = "0.5.0"
APP_ID = "2552430"
GAME_DIR_NAME = "KINGDOM HEARTS -HD 1.5+2.5 ReMIX-"
WORK_NAME = "KoreanHearts"
LEGACY_NAME = "KH1Korean"           # 0.3.x 의 작업 폴더
BASE = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
FONTS = [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf"]
NOTICE_KO = """[사용 전 확인]
- 이 프로그램은 패치일 뿐이며 게임을 포함하거나 배포하지 않습니다. 정품 게임(Steam 판)이 필요합니다.
- 비공식 팬 번역입니다. Square Enix, Disney 와 관계가 없고 공식 지원 대상이 아닙니다.
- 한글 파일은 이 PC 의 게임 파일로 만들어집니다. 만들어진 파일(KoreanHearts 폴더)은 게임 데이터를 바탕으로 하므로 다른 사람에게 공유하거나 재배포하지 마세요.
- 게임 원본 파일은 바꾸지 않지만, 모드 로더(Panacea)를 설치하고 게임 실행 중 메모리를 고칩니다. 이용약관 관련 판단과 사용에 따른 책임은 사용자에게 있습니다.
- 아무런 보증 없이 제공됩니다 (Apache License 2.0). 세이브 데이터는 미리 백업하세요.
- 실행할 때 GitHub(github.com)에서 이 프로그램의 새 판과 최신 번역이 있는지 확인하고 받습니다. 그 밖의 정보는 보내지 않습니다.
"""


# ---------------------------------------------------------------- 타이틀
class Title:
    def __init__(self, id, name, exe, ready, patcher=False):
        self.id, self.name, self.exe, self.ready, self.patcher = id, name, exe, ready, patcher


TITLES = [
    Title("kh1", "킹덤 하츠 1 (FINAL MIX)", "KINGDOM HEARTS FINAL MIX.exe", True, patcher=True),
    Title("recom", "킹덤 하츠 Re:Chain of Memories", "KINGDOM HEARTS Re_Chain of Memories.exe", True),
]
TITLE = {t.id: t for t in TITLES}


def parse_ids(s, default):
    if not s:
        return list(default)
    ids = [x.strip() for x in s.split(",") if x.strip()]
    for i in ids:
        if i not in TITLE:
            raise RuntimeError(f"모르는 타이틀: {i} (가능: {', '.join(TITLE)})")
    return ids


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
    return (bool(p) and os.path.isdir(os.path.join(p, "Image", "dt"))
            and any(os.path.exists(os.path.join(p, t.exe)) for t in TITLES))


def find_game():
    for lib in steam_libraries():
        p = os.path.join(lib, "steamapps", "common", GAME_DIR_NAME)
        if is_game_dir(p):
            return p
    return ""


def running_titles():
    """켜져 있는 타이틀 실행 파일 이름 (tasklist). 확인 실패면 빈 목록."""
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="ignore",
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=15).stdout.lower()
    except Exception:
        return []
    return [t.exe for t in TITLES if f'"{t.exe.lower()}"' in out]


def require_not_running():
    r = running_titles()
    if r:
        raise RuntimeError(f"게임이 켜져 있습니다 ({', '.join(r)}). 게임을 끈 뒤 다시 하세요.")


# ---------------------------------------------------------------- 설치 기록
def work_dir(game):
    return os.path.join(game, WORK_NAME)


def state_path(game):
    return os.path.join(work_dir(game), "install.json")


def read_state(game):
    """설치 기록 (없으면 빈 기록)."""
    try:
        st = json.load(open(state_path(game), encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    st.setdefault("shared", {})
    st.setdefault("titles", {})
    return st


def load_state(game):
    """설치 기록. 설치된 타이틀이 없으면 None."""
    st = read_state(game)
    return st if st["titles"] else None


def save_state(game, st):
    st["version"] = VERSION
    with open(state_path(game), "w", encoding="utf-8") as fp:
        json.dump(st, fp, ensure_ascii=False, indent=1)


def write_settings(game):
    with open(os.path.join(game, "panacea_settings.txt"), "w", encoding="utf-8", newline="\r\n") as fp:
        fp.write(f"mod_path={os.path.join(work_dir(game), 'mod')}\nenable_cache=true\n")


def migrate_legacy(game, log):
    """0.3.x 의 <게임 폴더>/KH1Korean 설치본을 KoreanHearts 구조로 옮긴다. 옮겼으면 True."""
    game = os.path.normpath(game)
    old = os.path.join(game, LEGACY_NAME)
    try:
        ost = json.load(open(os.path.join(old, "install.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if os.path.exists(state_path(game)):
        log(f"{LEGACY_NAME} 폴더와 {WORK_NAME} 폴더가 둘 다 있습니다. {LEGACY_NAME} 는 쓰지 않습니다 (지워도 됩니다).")
        return False
    require_not_running()
    work = work_dir(game)
    os.makedirs(work, exist_ok=True)
    moves = [(os.path.join(old, "mod", "kh1"), os.path.join(work, "mod", "kh1")),
             (os.path.join(old, "translation"), os.path.join(work, "kh1", "translation")),
             (os.path.join(old, "tools"), os.path.join(work, "kh1", "tools"))]
    bk_old, bk_new = ost.get("settings_backup"), None
    if bk_old and os.path.exists(bk_old):
        bk_new = os.path.join(work, "panacea_settings.backup.txt")
        moves.append((bk_old, bk_new))
    done = []
    try:
        for a, b in moves:
            if os.path.exists(a):
                os.makedirs(os.path.dirname(b), exist_ok=True)
                os.replace(a, b)
                done.append((a, b))
        st = {"shared": {"dll_installed_by_us": bool(ost.get("dll_installed_by_us")), "settings_backup": bk_new},
              "titles": {"kh1": {"version": ost.get("version", "?"), "source": ost.get("source", "?"),
                                 "content": None, "time": ost.get("time", "?")}}}
        save_state(game, st)
        write_settings(game)
    except BaseException:
        for a, b in reversed(done):                       # 되돌리기
            os.replace(b, a)
        try:
            os.remove(state_path(game))
        except OSError:
            pass
        raise
    shutil.rmtree(old, ignore_errors=True)
    log(f"이전 설치본({LEGACY_NAME})을 새 구조({WORK_NAME})로 옮겼습니다. 킹덤 하츠 1 한글 패치는 그대로 설치되어 있습니다.")
    return True


# ---------------------------------------------------------------- 설치 / 제거
def setup_shared(game, st, log):
    """Panacea(DBGHELP.dll)와 panacea_settings.txt. 설치 전 상태는 처음 한 번만 기록한다."""
    sh = st["shared"]
    dll = os.path.join(game, "DBGHELP.dll")
    if not os.path.exists(dll):
        shutil.copy(os.path.join(BASE, "third_party", "OpenKH.Panacea.dll"), dll)
        sh["dll_installed_by_us"] = True
        log("    Panacea(DBGHELP.dll) 설치")
    else:
        sh.setdefault("dll_installed_by_us", False)
        log("    기존 DBGHELP.dll(Panacea) 사용")
    sett = os.path.join(game, "panacea_settings.txt")
    if "settings_backup" not in sh:
        sh["settings_backup"] = None
        if os.path.exists(sett):
            bk = os.path.join(work_dir(game), "panacea_settings.backup.txt")
            shutil.copy(sett, bk)
            sh["settings_backup"] = bk
            log("    기존 panacea_settings.txt 백업")
    write_settings(game)


def build_kh1(game, root, src, log):
    """root(<작업 폴더>/kh1)에 KH1 한글 파일을 만들고 검증한다. 결과: root/mod/kh1."""
    for d in ("translation", "tools", "data", "mod"):
        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    # 번역 표 (원문 없음) 와 도구를 작업 폴더로. 도구는 게임 실행 때 메모리 패치(mem)가 같은 판을 쓰게 하려고 둔다
    shutil.copytree(os.path.join(src.root, "kh1", "translation", "src"), os.path.join(root, "translation", "src"))
    shutil.copytree(os.path.join(src.root, "kh1", "tools"), os.path.join(root, "tools"), ignore=shutil.ignore_patterns("__pycache__"))
    os.environ["KH1KO_ROOT"] = root
    update.use_tools(os.path.join(src.root, "kh1", "tools"))
    import pkgextract
    log(f"    도구: {os.path.dirname(pkgextract.__file__)}")
    log("1/6 게임 파일에서 필요한 원본 꺼내기 (약 2GB, 1분 안팎)")
    n = pkgextract.extract_all(game, root, log)
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
    shutil.rmtree(os.path.join(root, "data"), ignore_errors=True)      # 꺼낸 원본은 지운다


def build_recom(game, root, src, log):
    """root(<작업 폴더>/recom)에 Re:COM 한글 파일을 만들고 검증한다. 결과: root/mod/recom.
    KH1 의 pkgextract·settingmenu 도구와 설정 메뉴 번역 표를 읽기만 한다 (RECOMKO_KH1 = 받은 번역의 kh1 폴더)."""
    for d in ("translation", "tools", "data", "mod"):
        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    shutil.copytree(os.path.join(src.root, "recom", "translation", "src"), os.path.join(root, "translation", "src"))
    shutil.copytree(os.path.join(src.root, "recom", "tools"), os.path.join(root, "tools"), ignore=shutil.ignore_patterns("__pycache__"))
    os.environ["RECOMKO_ROOT"] = root
    os.environ["RECOMKO_KH1"] = os.path.join(src.root, "kh1")
    update.use_tools(os.path.join(root, "tools"))
    import recom_fullbuild
    log(f"    도구: {os.path.dirname(recom_fullbuild.__file__)}")
    recom_fullbuild.main(game, root, log)


BUILDERS = {"kh1": build_kh1, "recom": build_recom}


def install(game, log, src, ids):
    """src: update.Source (번역 표·도구를 읽을 곳). ids: 설치할 타이틀."""
    game = os.path.normpath(game)
    for tid in ids:
        if not TITLE[tid].ready or tid not in BUILDERS:
            raise RuntimeError(f"{TITLE[tid].name}: 아직 준비 중입니다.")
    for f in FONTS:
        if not os.path.exists(f):
            raise RuntimeError(f"글꼴이 없습니다: {f} (Windows 기본 글꼴 '맑은 고딕')")
    migrate_legacy(game, log)
    require_not_running()
    work = work_dir(game)
    os.makedirs(os.path.join(work, "mod"), exist_ok=True)
    st = read_state(game)
    log(f"번역 {src.short}")
    for tid in ids:
        t = TITLE[tid]
        log(f"== {t.name}")
        root = os.path.join(work, tid)
        BUILDERS[tid](game, root, src, log)
        log("6/6 결과 옮기기")
        dst = os.path.join(work, "mod", tid)
        shutil.rmtree(dst, ignore_errors=True)
        if os.path.exists(dst):
            raise RuntimeError(f"이전 결과를 지우지 못했습니다: {dst} (열려 있는 파일이 있으면 닫고 다시)")
        os.replace(os.path.join(root, "mod", tid), dst)
        shutil.rmtree(os.path.join(root, "mod"), ignore_errors=True)
        st["titles"][tid] = {"version": VERSION, "source": src.sha, "content": update.content_id(src.root, tid),
                             "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(game, st)
        log(f"    {t.name} 완료")
    log("Panacea 설정")
    setup_shared(game, st, log)
    save_state(game, st)
    log("설치 완료. '게임 실행' 으로 켜세요.")


def restore_shared(game, st, log):
    sh = st["shared"]
    sett = os.path.join(game, "panacea_settings.txt")
    if sh.get("settings_backup") and os.path.exists(sh["settings_backup"]):
        shutil.copy(sh["settings_backup"], sett)
        log("panacea_settings.txt 를 설치 전으로 되돌림")
    elif os.path.exists(sett):
        os.remove(sett)
        log("panacea_settings.txt 삭제 (설치 전에는 없었음)")
    if sh.get("dll_installed_by_us"):
        try:
            os.remove(os.path.join(game, "DBGHELP.dll"))
            log("DBGHELP.dll 삭제")
        except OSError as e:
            log(f"DBGHELP.dll 삭제 실패 (게임이 켜져 있으면 끄고 다시): {e}")


def uninstall(game, log, ids=None):
    """ids 타이틀만 제거 (None 이면 전부). 남은 타이틀이 없으면 Panacea 설정·DLL 도 되돌리고 작업 폴더를 지운다."""
    game = os.path.normpath(game)
    migrate_legacy(game, log)
    st = load_state(game)
    if not st:
        raise RuntimeError("설치 기록이 없습니다.")
    require_not_running()
    work = work_dir(game)
    for tid in (ids if ids is not None else list(st["titles"])):
        name = TITLE[tid].name if tid in TITLE else tid
        if tid not in st["titles"]:
            log(f"{name}: 설치되어 있지 않음")
            continue
        for d in (os.path.join(work, "mod", tid), os.path.join(work, tid)):
            shutil.rmtree(d, ignore_errors=True)
            if os.path.exists(d):
                raise RuntimeError(f"지우지 못했습니다: {d} (열려 있는 파일이 있으면 닫고 다시)")
        del st["titles"][tid]
        save_state(game, st)
        log(f"{name} 한글 패치 제거")
    if not st["titles"]:
        restore_shared(game, st, log)
        shutil.rmtree(work, ignore_errors=True)
        log("남은 타이틀이 없어 Panacea 설정을 설치 전으로 되돌리고 작업 폴더를 지웠습니다.")
    log("제거 완료.")


# ---------------------------------------------------------------- 메모리 패치 (KH1)
_patcher = None


def start_patcher(game, log):
    global _patcher
    if _patcher and _patcher.is_alive():
        return
    root = os.path.join(work_dir(game), "kh1")
    os.environ["KH1KO_ROOT"] = root
    t = os.path.join(root, "tools")
    update.use_tools(t if os.path.exists(os.path.join(t, "re", "mem.py")) else os.path.join(BASE, "kh1", "tools"))
    import mem
    log(f"    도구: {os.path.dirname(mem.__file__)}")

    def run():
        while True:
            try:
                mem.tex2x_main(10 ** 9, False, True)
            except BaseException as e:
                log(f"메모리 패치 오류: {e!r}. 다시 시도")
                time.sleep(2)
    _patcher = threading.Thread(target=run, daemon=True)
    _patcher.start()
    log("KH1 메모리 패치 대기 중 (게임을 켜면 자동으로 붙습니다. 이 창을 닫지 마세요)")


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
    def __init__(self, root, updated_from=None):
        self.root = root
        self.q = queue.Queue()
        sys.stdout = sys.stderr = Out(self.q)
        root.title(f"킹덤 하츠 한글 패치 {VERSION}")
        root.geometry("760x560")
        top = tk.Frame(root); top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text="게임 폴더").pack(side="left")
        self.game = tk.StringVar(value=find_game())
        tk.Entry(top, textvariable=self.game).pack(side="left", fill="x", expand=True, padx=6)
        tk.Button(top, text="찾아보기", command=self.browse).pack(side="left")
        box = tk.LabelFrame(root, text="타이틀 (설치·제거할 타이틀을 고르세요)"); box.pack(fill="x", padx=10, pady=(0, 6))
        self.sel, self.checks, self.labels = {}, {}, {}
        for i, t in enumerate(TITLES):
            v = tk.BooleanVar(value=t.ready)
            c = tk.Checkbutton(box, text=t.name, variable=v, anchor="w", width=34)
            c.grid(row=i, column=0, sticky="w", padx=4)
            lb = tk.Label(box, anchor="w"); lb.grid(row=i, column=1, sticky="w")
            self.sel[t.id], self.checks[t.id], self.labels[t.id] = v, c, lb
        btn = tk.Frame(root); btn.pack(fill="x", padx=10)
        self.b_inst = tk.Button(btn, text="선택한 타이틀 설치·업데이트", width=24, command=self.install)
        self.b_un = tk.Button(btn, text="선택한 타이틀 제거", width=18, command=self.remove)
        self.b_play = tk.Button(btn, text="게임 실행", width=12, command=self.play)
        for b in (self.b_inst, self.b_un, self.b_play):
            b.pack(side="left", padx=4)
        self.status = tk.Label(root, anchor="w"); self.status.pack(fill="x", padx=12, pady=4)
        self.log = scrolledtext.ScrolledText(root, height=18, state="disabled", wrap="word"); self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.src, self.content, self.migrated = None, {}, set()
        self.say(NOTICE_KO)
        if updated_from:
            self.say(f"프로그램을 {updated_from} 에서 {VERSION} 로 업데이트했습니다.")
        selfupdate.cleanup()
        self.busy(True)
        self.refresh()
        root.after(100, self.pump)
        threading.Thread(target=self.check_update, daemon=True).start()

    def check_update(self):
        if selfupdate.enabled():                 # 프로그램 새 판이 먼저 (새 판이 번역을 다시 확인한다)
            self.root.after(0, lambda: self.status.config(text="프로그램 새 판 확인 중..."))
            try:
                ver = selfupdate.run(VERSION, self.say)
            except BaseException as e:
                self.say(f"프로그램 새 판 확인 오류: {e!r}")
                ver = None
            if ver:
                self.root.after(0, self.restart)
                return
        try:
            src = update.resolve(BASE, VERSION, self.say)
        except BaseException as e:
            self.say(f"최신 번역 확인 오류: {e!r}")
            src = update.Source(BASE, update.bundled_sha(BASE), False)
        self.say(f"번역 {src.short}" + (" (최신)" if src.latest else ""))
        self.content = {t.id: update.content_id(src.root, t.id) for t in TITLES}
        self.src = src
        self.root.after(0, self.done)

    def restart(self):
        try:
            selfupdate.restart(VERSION)
        except BaseException as e:
            self.say(f"새 판을 띄우지 못했습니다. 이 창을 닫고 KoreanHearts.exe 를 다시 실행하세요: {e!r}")
            return
        self.root.destroy()

    def outdated(self, st, tid):
        """설치된 타이틀의 번역·도구가 최신(GitHub)과 다른지. 다른 타이틀만 바뀐 커밋이면 False."""
        rec = (st or {}).get("titles", {}).get(tid)
        if not (rec and self.src and self.src.latest):
            return False
        return rec.get("source") != self.src.sha and rec.get("content") != self.content.get(tid)

    def selected(self):
        return [t.id for t in TITLES if self.sel[t.id].get()]

    def install(self):
        ids = [i for i in self.selected() if TITLE[i].ready]
        if not ids:
            messagebox.showinfo("설치", "설치할 타이틀을 고르세요. ('준비 중' 타이틀은 아직 설치할 수 없습니다)"); return
        if load_state(self.game.get()) or messagebox.askyesno("설치 전 확인", NOTICE_KO + "\n위 내용을 확인했고 동의합니까?"):
            self.task(lambda g, log: install(g, log, self.src, ids))

    def remove(self):
        st = load_state(self.game.get())
        ids = [i for i in self.selected() if st and i in st["titles"]]
        if not ids:
            messagebox.showinfo("제거", "제거할 타이틀을 고르세요. (설치된 타이틀만 제거할 수 있습니다)"); return
        names = ", ".join(TITLE[i].name for i in ids)
        if messagebox.askyesno("제거", f"다음 타이틀의 한글 패치를 제거할까요?\n\n{names}"):
            self.task(lambda g, log: uninstall(g, log, ids))

    def say(self, s):
        self.q.put(s)
        if os.environ.get("KH1KO_GUI_LOG"):          # 시험용: 창 로그를 파일에도
            try:
                with open(os.environ["KH1KO_GUI_LOG"], "a", encoding="utf-8") as fp:
                    fp.write(f"[{VERSION} {os.getpid()}] {s}\n")
            except OSError:
                pass

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
            for t in TITLES:
                self.labels[t.id].config(text="")
            return
        if g not in self.migrated:
            self.migrated.add(g)
            try:
                migrate_legacy(g, self.say)
            except BaseException as e:
                self.say(f"이전 설치본 옮기기 실패: {e}")
        st = load_state(g)
        n_new = 0
        for t in TITLES:
            rec = (st or {}).get("titles", {}).get(t.id)
            if not t.ready:
                text = "준비 중"
            elif not rec:
                text = "설치 안 됨"
            else:
                text = f"설치됨 (번역 {str(rec.get('source', '?'))[:7]}, {rec.get('time', '?')})"
                if self.outdated(st, t.id):
                    text += " - 새 번역 있음"
                    n_new += 1
            self.labels[t.id].config(text=text)
        if self.src is None:
            self.status.config(text="최신 번역 확인 중...")
        elif n_new:
            self.status.config(text=f"새 번역({self.src.short})이 있습니다. 해당 타이틀을 골라 '설치·업데이트' 를 누르세요.")
        else:
            self.status.config(text="")

    def busy(self, on):
        for b in (self.b_inst, self.b_play, self.b_un):
            b.config(state="disabled" if on else "normal")
        for t in TITLES:
            self.checks[t.id].config(state="disabled" if on or not t.ready else "normal")

    def task(self, fn, after=None):
        g = self.game.get()
        if not is_game_dir(g):
            messagebox.showerror("게임 폴더", "게임 폴더가 올바르지 않습니다."); return
        self.busy(True)

        def run():
            ok = False
            try:
                fn(g, self.say)
                ok = True
            except BaseException as e:
                self.say("오류: " + "".join(traceback.format_exception_only(type(e), e)).strip())
                self.say(traceback.format_exc())
            finally:
                self.root.after(0, self.done)
                if ok and after:
                    self.root.after(0, after)
        threading.Thread(target=run, daemon=True).start()

    def done(self):
        self.busy(self.src is None)
        self.refresh()

    def play(self):
        g = self.game.get()
        st = load_state(g)
        if not st:
            messagebox.showinfo("게임 실행", "먼저 타이틀을 골라 '설치·업데이트' 를 하세요."); return
        old = [i for i in st["titles"] if i in TITLE and TITLE[i].ready and self.outdated(st, i)]
        if old:
            names = ", ".join(TITLE[i].name for i in old)
            a = messagebox.askyesnocancel("새 번역", f"새 번역({self.src.short})이 있습니다: {names}\n업데이트한 뒤 게임을 켤까요?\n"
                                         "(몇 분 걸립니다. '아니요' 는 지금 설치된 번역으로 켭니다)")
            if a is None:
                return
            if a:
                self.task(lambda g, log: install(g, log, self.src, old), after=self.play)
                return
        if "kh1" in st["titles"]:
            start_patcher(g, self.say)
        os.startfile(f"steam://rungameid/{APP_ID}")
        names = ", ".join(TITLE[i].name for i in st["titles"] if i in TITLE)
        self.say(f"게임을 켭니다. 런처에서 한글 패치를 설치한 타이틀({names})을 고르세요.")


def main():
    # 자기 업데이트가 받은 실행 파일을 확인할 때: --selftest <파일> -> VERSION 을 쓰고 끝
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        with open(sys.argv[2], "w", encoding="utf-8") as fp:
            fp.write(VERSION)
        return
    # 화면 없이 (시험·자동화용):
    #   --install|--uninstall|--play|--status <게임 폴더> <로그 파일> [타이틀,타이틀]
    #   타이틀 생략: 설치 = 준비된 타이틀 전부, 제거 = 설치된 타이틀 전부
    if len(sys.argv) >= 4 and sys.argv[1] in ("--install", "--uninstall", "--play", "--status"):
        cmd, game, arg = sys.argv[1], os.path.normpath(sys.argv[2]), (sys.argv[4] if len(sys.argv) > 4 else "")
        with open(sys.argv[3], "w", encoding="utf-8") as fp:
            sys.stdout = sys.stderr = fp

            def log(s):
                fp.write(s + "\n"); fp.flush()
            try:
                if cmd == "--install":
                    ids = parse_ids(arg, [t.id for t in TITLES if t.ready])
                    src = update.resolve(BASE, VERSION, log)
                    log(f"번역 {src.short}" + (" (최신)" if src.latest else ""))
                    install(game, log, src, ids)
                elif cmd == "--uninstall":
                    uninstall(game, log, parse_ids(arg, []) or None)
                elif cmd == "--status":
                    migrate_legacy(game, log)
                    log(json.dumps(load_state(game), ensure_ascii=False, indent=1))
                else:                    # 게임을 켜고, 게임이 꺼질 때까지 (KH1 이 설치되어 있으면 메모리 패치)
                    st = load_state(game)
                    if not st:
                        raise RuntimeError("설치 기록이 없습니다.")
                    if "kh1" in st["titles"]:
                        start_patcher(game, log)
                    os.startfile(f"steam://rungameid/{APP_ID}")
                    seen = False
                    while True:
                        time.sleep(2)
                        alive = bool(running_titles())
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
    updated_from = sys.argv[2] if len(sys.argv) >= 3 and sys.argv[1] == "--updated-from" else None
    root = tk.Tk()
    App(root, updated_from)
    root.mainloop()


if __name__ == "__main__":
    main()
