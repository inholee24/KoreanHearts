"""설치 프로그램(KoreanHearts.exe) 자기 업데이트.

실행할 때 GitHub 저장소의 최신 릴리스(초안·시험판 제외)를 확인해서, 이 프로그램 VERSION 보다 높은 판이면
릴리스 zip 을 받아 실행 파일을 바꾸고 새 판으로 다시 시작한다. 번역·도구 업데이트(update.py)보다 먼저 한다.
- 릴리스 규칙: 태그 = "v" + app.py 의 VERSION, 자산 = build_release.ps1 이 만든 KoreanHearts-<버전>.zip
  (zip 안에 KoreanHearts.exe). 다른 이름의 자산(옛 KH1Korean-*.zip)은 보지 않는다.
- 받은 파일 확인: 크기, GitHub 가 알려 주는 sha256(digest), zip 안 실행 파일 1개, 그리고 받은 실행 파일을
  --selftest 로 한 번 실행해 보고한 VERSION 이 릴리스 태그와 같아야 바꾼다 (VERSION 을 안 올린 릴리스면
  실행할 때마다 다시 받는 일이 없도록).
- 바꾸기: 실행 중인 exe 는 지울 수 없지만 이름은 바꿀 수 있다 -> <exe>.old 로 옮기고 새 파일을 <exe> 로.
  새 판이 시작하면 cleanup() 이 <exe>.old 를 지운다. 바꾸지 못하면(폴더 쓰기 권한 없음 등) 지금 판으로 계속한다.
- 화면 없는 실행(--install 등), 개발 실행(비 frozen), KH1KO_NO_SELFUPDATE 는 하지 않는다.
  KH1KO_RELEASE_API 는 시험용 (릴리스 JSON 주소).
"""
import hashlib, io, json, os, re, subprocess, sys, threading, time, urllib.request, zipfile

from update import HEADERS, REPO, RELEASES, vtuple

API = os.environ.get("KH1KO_RELEASE_API") or f"https://api.github.com/repos/{REPO}/releases/latest"
EXE_NAME = "KoreanHearts.exe"
ASSET = re.compile(r"^KoreanHearts-(\d+(?:\.\d+)*)\.zip$", re.I)


def enabled():
    return bool(getattr(sys, "frozen", False)) and not os.environ.get("KH1KO_NO_SELFUPDATE")


def exe_path():
    return os.path.abspath(sys.executable)


def child_env():
    """새로 띄우는 exe 가 이 프로그램(PyInstaller 단일 파일)의 임시 폴더·환경을 물려받지 않게 한다."""
    env = dict(os.environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def latest(timeout=8):
    """최신 릴리스 (버전, 자산). 쓸 수 있는 자산이 없으면 (버전, None)."""
    req = urllib.request.Request(API, headers={**HEADERS, "Accept": "application/vnd.github+json"})
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    ver = str(r.get("tag_name") or "").lstrip("vV")
    if not re.fullmatch(r"\d+(\.\d+)*", ver) or r.get("draft") or r.get("prerelease"):
        return None, None
    for a in r.get("assets") or []:
        m = ASSET.match(a.get("name") or "")
        if m and vtuple(m.group(1)) == vtuple(ver) and a.get("browser_download_url"):
            return ver, a
    return ver, None


def fetch_exe(asset, dst, timeout=60):
    """자산 zip 을 받아 안의 KoreanHearts.exe 를 dst 에 쓴다."""
    data = urllib.request.urlopen(urllib.request.Request(asset["browser_download_url"], headers=HEADERS),
                                  timeout=timeout).read()
    if asset.get("size") and len(data) != asset["size"]:
        raise ValueError(f"받은 크기가 다름 ({len(data)} / {asset['size']})")
    dg = asset.get("digest") or ""
    if dg.startswith("sha256:") and hashlib.sha256(data).hexdigest() != dg[7:].lower():
        raise ValueError("받은 파일의 sha256 이 릴리스 정보와 다름")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [i for i in z.infolist() if not i.is_dir() and i.filename.replace("\\", "/").rsplit("/", 1)[-1].lower() == EXE_NAME.lower()]
        if len(names) != 1:
            raise ValueError(f"zip 안에 {EXE_NAME} 가 {len(names)}개")
        body = z.read(names[0])
    if body[:2] != b"MZ":
        raise ValueError("실행 파일이 아님")
    with open(dst, "wb") as fp:
        fp.write(body)


def selftest(exe, timeout=120):
    """exe --selftest <파일> 로 보고한 VERSION."""
    out = exe + ".selftest.txt"
    try:
        os.remove(out)
    except OSError:
        pass
    try:
        subprocess.run([exe, "--selftest", out], env=child_env(), timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return open(out, encoding="utf-8").read().strip()
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        try:
            os.remove(out)
        except OSError:
            pass


def run(version, log):
    """새 판이 있으면 받아서 실행 파일을 바꾼다. 바꿨으면 새 버전 문자열, 아니면 None. 오류는 기록만 한다."""
    exe = exe_path()
    try:
        ver, asset = latest()
    except Exception as e:
        log(f"프로그램 새 판 확인 실패 (인터넷 연결 확인): {e}")
        return None
    if not ver or vtuple(ver) <= vtuple(version):
        return None
    if asset is None:
        log(f"프로그램 새 판 {ver} 이 있지만 받을 파일이 아직 없습니다. 직접 받으려면: {RELEASES}")
        return None
    new, old = exe + ".new", exe + ".old"
    log(f"프로그램 새 판 {ver} 받는 중 (지금 {version})")
    try:
        fetch_exe(asset, new)
        got = selftest(new)
        if got is None or vtuple(got) != vtuple(ver):
            raise ValueError(f"받은 프로그램 시험 실행 결과가 다름 ({got!r}, 릴리스 {ver})")
        try:
            os.remove(old)
        except FileNotFoundError:
            pass
        os.replace(exe, old)                     # 실행 중인 exe 도 이름은 바꿀 수 있다
        try:
            os.replace(new, exe)
        except BaseException:
            os.replace(old, exe)
            raise
    except Exception as e:
        log(f"프로그램 자동 업데이트 실패, 지금 판({version})으로 계속합니다: {e}")
        log(f"    직접 받으려면: {RELEASES}")
        try:
            os.remove(new)
        except OSError:
            pass
        return None
    log(f"프로그램을 {ver} 로 바꿨습니다. 다시 시작합니다.")
    return ver


def restart(version):
    """바꾼 exe 를 새로 띄운다 (이 프로세스는 호출한 쪽이 끝낸다)."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    args = [exe_path(), "--updated-from", version]
    try:
        subprocess.Popen(args, env=child_env(), close_fds=True,
                         creationflags=flags | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0))
    except OSError:                              # 작업 개체가 분리를 허용하지 않으면 그냥 띄운다
        subprocess.Popen(args, env=child_env(), close_fds=True, creationflags=flags)


def cleanup():
    """지난 업데이트가 남긴 <exe>.old / .new 를 지운다. 옛 프로세스가 아직 끝나는 중일 수 있어 잠시 다시 시도한다."""
    if not getattr(sys, "frozen", False):
        return
    exe = exe_path()
    left = [p for p in (exe + ".old", exe + ".new") if os.path.exists(p)]
    if not left:
        return

    def work():
        for _ in range(30):
            for p in list(left):
                try:
                    os.remove(p)
                    left.remove(p)
                except FileNotFoundError:
                    left.remove(p)
                except OSError:
                    pass
            if not left:
                return
            time.sleep(1)
    threading.Thread(target=work, daemon=True).start()
