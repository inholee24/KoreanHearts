"""GitHub 저장소의 최신 번역·도구 받기.

설치 프로그램을 다시 받지 않아도, 저장소 main 에 올린 타이틀별 번역 표(<타이틀>/translation/src)와
빌드 도구(<타이틀>/tools)를 받아 이 PC 에서 한글 파일을 다시 만든다.
- 최신 커밋: GitHub API (커밋 sha 만), 받기: codeload zip, 저장: %LOCALAPPDATA%\\KoreanHearts\\src\\<sha>
- 타이틀별로 새 번역인지는 커밋 sha 가 아니라 그 타이틀 파일 내용(content_id)으로 판단한다.
- 받은 커밋의 installer/update.json 의 min_app 보다 이 프로그램 버전이 낮으면 받은 것을 쓰지 않고
  새 설치 프로그램을 안내한다. app.py·update.py·묶인 라이브러리가 바뀌어야 하는 변경은 min_app 을 올린다.
  update.json 이 없는 커밋(이 기능 이전)은 쓰지 않는다.
- 인터넷이 안 되면 마지막으로 받은 것, 그것도 없으면 실행 파일에 묶인 것을 쓴다.
"""
import hashlib, importlib.machinery, io, json, os, re, shutil, sys, urllib.request, zipfile

REPO = "inholee24/KoreanHearts"
BRANCH = "main"
RELEASES = f"https://github.com/{REPO}/releases/latest"
API = os.environ.get("KH1KO_UPDATE_API") or f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"   # 환경 변수는 시험용
ZIP = os.environ.get("KH1KO_UPDATE_ZIP") or f"https://codeload.github.com/{REPO}/zip/{{sha}}"
CACHE = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "KoreanHearts", "src")
HEADERS = {"User-Agent": "KoreanHearts-updater"}
KEEP = re.compile(r"^(installer/update\.json$|[a-z0-9]+/(tools|translation/src)/)")   # <타이틀>/tools/, <타이틀>/translation/src/


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


class Source:
    """번역·도구를 읽을 곳. root 아래에 <타이틀>/tools/, <타이틀>/translation/src/ 가 있다."""
    def __init__(self, root, sha, latest):
        self.root, self.sha, self.latest = root, sha, latest   # latest: GitHub 최신으로 확인됨

    @property
    def short(self):
        return self.sha[:7]


def bundled_sha(base):
    try:
        return open(os.path.join(base, "source.txt"), encoding="utf-8").read().strip() or "bundled"
    except OSError:
        return "bundled"


def min_app(root):
    """없으면 None (이 기능 이전의 커밋)."""
    try:
        return json.load(open(os.path.join(root, "installer", "update.json"), encoding="utf-8"))["min_app"]
    except (OSError, ValueError, KeyError):
        return None


def usable(root, app_version):
    m = min_app(root)
    return (m is not None and vtuple(app_version) >= vtuple(m)
            and os.path.exists(os.path.join(root, "kh1", "tools", "build_ko.py"))
            and os.path.exists(os.path.join(root, "kh1", "translation", "src", "kh1_evmsg.tsv")))


def content_id(root, title):
    """타이틀의 도구·번역 표 내용 해시. 없으면 None. 같은 커밋이면 묶인 것과 받은 것이 같은 값이다."""
    h, n = hashlib.sha1(), 0
    for sub in ("tools", os.path.join("translation", "src")):
        base = os.path.join(root, title, sub)
        for dp, dns, fns in os.walk(base):
            dns[:] = sorted(d for d in dns if d != "__pycache__")
            for f in sorted(fns):
                if f.endswith(".pyc"):
                    continue
                p = os.path.join(dp, f)
                h.update((sub + "/" + os.path.relpath(p, base)).replace("\\", "/").encode() + b"\0")
                h.update(open(p, "rb").read() + b"\0")
                n += 1
    return h.hexdigest()[:12] if n else None


def fetch_sha(timeout=8):
    req = urllib.request.Request(API, headers={**HEADERS, "Accept": "application/vnd.github.sha"})
    sha = urllib.request.urlopen(req, timeout=timeout).read().decode("ascii", "replace").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError(f"예상과 다른 응답: {sha[:60]!r}")
    return sha


def download(sha, timeout=60):
    data = urllib.request.urlopen(urllib.request.Request(ZIP.format(sha=sha), headers=HEADERS), timeout=timeout).read()
    dst = os.path.join(CACHE, sha)
    tmp = dst + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""   # 맨 위 "KoreanHearts-<sha>/" 제거
            if info.is_dir() or not KEEP.match(rel) or ".." in rel.split("/"):
                continue
            out = os.path.join(tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as fp:
                fp.write(z.read(info))
    shutil.rmtree(dst, ignore_errors=True)
    os.replace(tmp, dst)
    return dst


def cached(app_version, exclude=()):
    """받아 둔 것 중 쓸 수 있는 가장 최근 것."""
    try:
        names = [n for n in os.listdir(CACHE) if re.fullmatch(r"[0-9a-f]{40}", n) and n not in exclude]
    except OSError:
        return None
    names.sort(key=lambda n: os.path.getmtime(os.path.join(CACHE, n)), reverse=True)
    for n in names:
        if usable(os.path.join(CACHE, n), app_version):
            return Source(os.path.join(CACHE, n), n, False)
    return None


def prune(keep):
    try:
        for n in os.listdir(CACHE):
            if n != keep and re.fullmatch(r"[0-9a-f]{40}(\.tmp)?", n):
                shutil.rmtree(os.path.join(CACHE, n), ignore_errors=True)
    except OSError:
        pass


def resolve(base, app_version, log):
    """쓸 번역·도구를 정한다. 실행 파일이 아니면(개발 실행) 저장소 그대로 쓴다."""
    bsha = bundled_sha(base)
    own = Source(base, bsha, False)
    if not getattr(sys, "frozen", False) or os.environ.get("KH1KO_NO_UPDATE"):
        return own
    try:
        sha = fetch_sha()
    except Exception as e:
        log(f"최신 번역 확인 실패 (인터넷 연결 확인): {e}")
        return cached(app_version) or own
    if sha == bsha:
        own.latest = True
        return own
    root = os.path.join(CACHE, sha)
    if not os.path.isdir(root):                 # 받은 폴더는 다 받은 뒤에 이름을 바꾸므로 있으면 완전하다
        try:
            log(f"최신 번역 받는 중 ({sha[:7]})")
            root = download(sha)
        except Exception as e:
            log(f"최신 번역 받기 실패: {e}")
            return cached(app_version) or own
    if not usable(root, app_version):
        m = min_app(root)
        if m is None or vtuple(app_version) >= vtuple(m):      # update.json 이 없거나 폴더 구성이 다른 (옛) 커밋
            log("저장소 최신 커밋이 이 프로그램과 맞지 않아 묶여 있는 번역을 씁니다.")
        else:
            log(f"최신 번역은 설치 프로그램 {m} 이상이 필요합니다. 새 판이 릴리스되면 실행할 때 자동으로 바뀝니다. "
                f"직접 받으려면: {RELEASES}")
        return cached(app_version, exclude=(sha,)) or own
    prune(sha)
    return Source(root, sha, True)


# ---------------------------------------------------------------- 도구 모듈을 받은 것에서 불러오기
class _ToolFinder:
    """실행 파일에 묶인 도구 모듈보다 받은 도구(tools/*.py, tools/re/mem.py)를 먼저 찾는다."""
    def __init__(self):
        self.dirs, self.names = [], set()

    def find_spec(self, name, path=None, target=None):
        if name in self.names:
            return importlib.machinery.PathFinder.find_spec(name, self.dirs)
        return None


_finder = _ToolFinder()


def use_tools(tools):
    """tools 폴더의 모듈을 쓰게 한다. 표준 라이브러리와 이름이 겹치는 분석용 스크립트(tools/re/dis.py 등)는 제외."""
    tools = os.path.abspath(tools)
    names = {f[:-3] for f in os.listdir(tools) if f.endswith(".py")} | {"mem"}
    names -= set(sys.stdlib_module_names)
    if _finder not in sys.meta_path:
        sys.meta_path.insert(0, _finder)
    _finder.dirs, _finder.names = [tools, os.path.join(tools, "re")], names
    for n in names:                              # 다른 곳에서 이미 불러온 것은 버린다
        m = sys.modules.get(n)
        f = getattr(m, "__file__", None) or ""
        if m is not None and not os.path.abspath(f).startswith(tools + os.sep):
            del sys.modules[n]
