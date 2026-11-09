"""그림 속 글자 다시 그리기 (도움말 100 장 외 나머지: 미니게임 규칙, 메뉴·전투 제목, HUD, 타이틀 등).

명세: recom/translation/src/imgtext.json  { "<그림 해시>": {"name": "...", "jobs": [작업, ...]}, ... }
  그림 해시 = 픽셀 sha1 앞 10자리 (imz_sheets/list.tsv 2열, recom_helpstock 과 같음). 원문은 넣지 않는다.
  작업 = {
    "r":  [x0, y0, x1, y1]   대략의 영역 (안의 글자만 있어야 함. 장식·그림이 들어가면 같이 지워진다)
    "lines": ["줄", ...]     한국어 줄 ([[...]] = 노랑 강조). 비우면 지우기만
    "c":  "white|yellow|cyan|black|#rrggbb|auto"  글자색 (기본 white, auto = 원래 글자의 가장 밝은 색, grad = 원래 글자 행별 색 그라데이션)
    "it": 1                  기울임
    "al": "l|c|r"            정렬 (기본 l: 원래 첫 줄 왼쪽 / c: 원래 글자 가운데 / r: 오른쪽)
    "sh": 0|1                그림자 (기본 1, 색 "shc", 오프셋 "sho")
    "sz": 0                  글자 크기 px (0 = 원래 줄 높이에서)
    "tol": 24                배경과 다르다고 볼 색 차이
    "ref": "l|r|lr"          행마다 배경색을 영역 왼쪽(l)/오른쪽(r) 끝에서 잰다 (줄무늬·세로 그라데이션도 그대로), lr = 좌우 보간
    "scale": 1.0, "bold": 0  글자 크기 배율 (원래 줄 높이 기준), 굵게 (같은 색 외곽선 px)
    "font": "bold|regular"
    "ol": 0                  외곽선 두께 (장식 글꼴 제목용), "olc" 색
    "dy": 0                  세로 위치 보정 (밑줄 위 제목 등)
    "box": [x0, y0, x1, y1]  게임이 실제로 잘라 그리는 스프라이트 사각형 (같은 이름 .lad 의 SEQD 표, x1/y1 미포함).
                             그린 글자(그림자 포함)가 밖으로 나가면 안으로 옮기고, 그래도 크면 줄인다.
                             (게임 확인 2026-11-09: 일시 정지 제목이 글자 칸마다 잘려 보임 -> image-text.md)
  }
검출: 영역 안에서 그 행의 배경색과 다른 픽셀의 행 묶음 = 원래 글줄. 지우기 = 그 줄의 행들을 배경색으로.
사용: python -I -X utf8 recom_imgtext.py preview [해시...] | apply
"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
import recom_imz as I, recom_paths as P

SPEC = os.path.join(P.TR, "src", "imgtext.json")
OUT = os.path.join(P.TR, "build", "imgtext")
TTF = {"bold": r"C:\Windows\Fonts\malgunbd.ttf", "regular": r"C:\Windows\Fonts\malgun.ttf"}
COL = {"white": (238, 238, 238), "yellow": (255, 232, 0), "cyan": (96, 190, 240), "black": (0, 0, 0)}
YELLOW = COL["yellow"]
_f = {}


def font(px, kind="bold"):
    k = (px, kind)
    if k not in _f:
        _f[k] = ImageFont.truetype(TTF[kind], px)
    return _f[k]


def color(c):
    if isinstance(c, (list, tuple)):
        return tuple(c)
    if c.startswith("#"):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return COL[c]


def segments(s, base):
    out, rest = [], s
    while "[[" in rest:
        a, b = rest.split("[[", 1)
        y, rest = b.split("]]", 1)
        a and out.append((a, base))
        out.append((y, YELLOW))
    rest and out.append((rest, base))
    return out


def diff(a, b):
    return max(abs(a[i] - b[i]) for i in range(3)) + abs(a[3] - b[3]) // 2


def groups(rows, gap=2):
    out = []
    for y in sorted(rows):
        if out and y - out[-1][1] <= gap + 1:
            out[-1][1] = y
        else:
            out.append([y, y])
    return out


def run_job(img, layer, job, warns):
    px = img.load()
    x0, y0, x1, y1 = job["r"]
    tol = job.get("tol", 24)
    mode = job.get("ref", "l")
    refx = x0 if mode in ("l", "lr") else x1
    ref = {y: px[refx, y] for y in range(y0, y1 + 1)}
    refr = {y: px[x1, y] for y in range(y0, y1 + 1)} if mode == "lr" else None
    hit = {}
    for y in range(y0, y1 + 1):
        if refr:
            xs = [x for x in range(x0, x1 + 1)
                  if diff(px[x, y], tuple(int(ref[y][i] + (refr[y][i] - ref[y][i]) * (x - x0) / max(1, x1 - x0)) for i in range(4))) > tol]
        else:
            xs = [x for x in range(x0, x1 + 1) if diff(px[x, y], ref[y]) > tol]
        if xs:
            hit[y] = xs
    boxes = []
    for a, b in groups(hit, job.get("gap", 2)):
        if b - a < job.get("minh", 5):
            continue
        xs = [x for y in range(a, b + 1) for x in hit.get(y, [])]
        boxes.append((min(xs), a, max(xs), b))
    if not boxes:
        warns.append(f"글자 못 찾음 {job['r']}")
        return
    if job.get("c") == "grad":                        # 원래 글자 행별 가장 밝은 색 = 위->아래 그라데이션
        bx = boxes[0]
        g = []
        for y in range(bx[1], bx[3] + 1):
            row = [px[x, y] for x in range(bx[0], bx[2] + 1) if px[x, y][3] > 200]
            if row:
                g.append(max(row, key=lambda c: sum(c[:3]))[:3])
        job = dict(job, c="white", _grad=g or [(238, 238, 238)])
    if job.get("c") == "auto":                        # 원래 글자의 가장 밝은 색 (지우기 전에 잰다)
        cand = [px[x, y] for (a0, b0, a1, b1) in boxes for y in range(b0, b1 + 1) for x in range(a0, a1 + 1)]
        best = max(cand, key=lambda c: (c[3] > 200, sum(c[:3])))
        job = dict(job, c=list(best[:3]))
    # 지우기: 줄 영역 행마다 배경색 (영역 안으로 제한)
    for (a0, b0, a1, b1) in boxes:
        for y in range(max(y0, b0 - 2), min(y1, b1 + 3) + 1):
            for x in range(max(x0, a0 - 3), min(x1, a1 + 4) + 1):
                if refr:                                  # 좌우 배경색 보간 (가로 그라데이션 띠)
                    t = (x - x0) / max(1, x1 - x0)
                    px[x, y] = tuple(int(ref[y][i] * (1 - t) + refr[y][i] * t) for i in range(4))
                else:
                    px[x, y] = ref[y]
    lines = job.get("lines", [])
    if not lines:
        return
    col = color(job.get("c", "white"))
    h0 = boxes[0][3] - boxes[0][1]
    sh = job.get("sh", 1)
    size = job.get("sz") or max(14, round((h0 - (3 if sh else 0)) * job.get("scale", 1.0)))
    c0 = (boxes[0][1] + boxes[0][3] - (3 if sh else 0)) / 2
    pitch = ((boxes[-1][1] + boxes[-1][3]) / 2 - (boxes[0][1] + boxes[0][3]) / 2) / (len(boxes) - 1) if len(boxes) > 1 else size * 1.35
    pitch = job.get("pitch", pitch)
    al = job.get("al", "l")
    for i, s in enumerate(lines):
        segs = segments(s, col)
        cy = c0 + pitch * i
        if job.get("each", 0) and i < len(boxes):          # 줄마다 원래 줄 자리에
            bb = boxes[i]; cy = (bb[1] + bb[3] - (3 if sh else 0)) / 2
        else:
            bb = boxes[min(i, len(boxes) - 1)]
        maxw = job.get("maxw", (x1 - x0) - 6)
        px_ = size
        f = font(px_, job.get("font", "bold"))
        while px_ > 12 and sum(f.getlength(t) for t, _ in segs) > maxw:
            px_ -= 1; f = font(px_, job.get("font", "bold"))
        w = sum(f.getlength(t) for t, _ in segs)
        if w > maxw:
            warns.append(f"폭 넘침 {w:.0f}>{maxw} {s}")
        if al == "c":
            cx = job.get("cx", (bb[0] + bb[2]) / 2)
            left = cx - w / 2
        elif al == "r":
            left = bb[2] - w
        else:
            left = job.get("x", boxes[0][0])
        draw_segs(layer, left + job.get("_dx", 0), cy + job.get("dy", 0), segs, f, sh, job)


def draw_segs(layer, left, cy, segs, f, sh, job):
    w = int(sum(f.getlength(t) for t, _ in segs)) + 12
    h = f.size + 20
    tl = Image.new("RGBA", (w + h // 3 + 8, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tl)
    ol = job.get("ol", 0)
    olc = color(job.get("olc", "black")) + (255,)
    shc = color(job.get("shc", [8, 8, 36])) + (255,)
    so = job.get("sho", 3)
    passes = ([("sh", so)] if sh else []) + [("fg", 0)]
    for kind, off in passes:
        xx = 4 + off
        for t, c in segs:
            fill = shc if kind == "sh" else c + (255,)
            if job.get("bold") and f.size >= 26 and kind == "fg" and not ol:   # 작은 글자는 굵게 하면 획이 뭉개짐
                dr.text((xx, h // 2), t, font=f, fill=fill, anchor="lm", stroke_width=job["bold"], stroke_fill=fill)
            elif ol and kind == "fg":
                dr.text((xx, h // 2), t, font=f, fill=fill, anchor="lm", stroke_width=ol, stroke_fill=olc)
            else:
                dr.text((xx, h // 2 + off), t, font=f, fill=fill, anchor="lm",
                        stroke_width=ol if kind == "sh" else 0, stroke_fill=shc)
            xx += f.getlength(t)
    if job.get("_grad"):                              # 글자 모양만 남기고 그라데이션으로 칠한다 (외곽선은 그 뒤에 따로)
        g = job["_grad"]
        if ol:
            fillm = Image.new("L", tl.size, 0)
            dm = ImageDraw.Draw(fillm)
            xx = 4
            for t, c in segs:
                dm.text((xx, h // 2), t, font=f, fill=255, anchor="lm")
                xx += f.getlength(t)
            a = fillm
        else:
            a = tl.getchannel("A")
        bb = a.getbbox() or (0, 0, tl.width, tl.height)
        grad = Image.new("RGB", tl.size)
        gp = grad.load()
        for y in range(tl.height):
            t = min(1, max(0, (y - bb[1]) / max(1, bb[3] - bb[1] - 1)))
            c = g[min(len(g) - 1, int(t * (len(g) - 1)))]
            for x in range(tl.width):
                gp[x, y] = c
        grad.putalpha(a)
        if ol:                                        # 외곽선(tl, olc 로 칠해짐) 위에 그라데이션 글자
            base = Image.new("RGBA", tl.size, olc[:3] + (0,))
            base.putalpha(tl.getchannel("A"))
            base.alpha_composite(grad)
            grad = base
        tl = grad
    if job.get("it"):
        s = 0.2
        tl = tl.transform(tl.size, Image.AFFINE, (1, s, -s * h, 0, 1, 0), resample=Image.BICUBIC)
    layer.alpha_composite(tl, (int(left) - 4, int(cy - h // 2)))


def fit_box(img, job, warns):
    """job 을 시험 삼아 복사본에 그려 보고, 글자 픽셀이 box 안에 들도록 dx/dy 를 더하고 필요하면 크기를 줄인 job 을 돌려준다."""
    x0, y0, x1, y1 = job["box"]
    j = dict(job)
    for _ in range(12):
        lj = Image.new("RGBA", img.size, (0, 0, 0, 0))
        run_job(img.copy(), lj, j, [])
        bb = lj.getchannel("A").point(lambda v: 255 if v >= 16 else 0).getbbox()
        if not bb:
            return j
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        if w <= x1 - x0 and h <= y1 - y0:
            dx = max(0, x0 - bb[0]) - max(0, bb[2] - x1)
            dy = max(0, y0 - bb[1]) - max(0, bb[3] - y1)
            if not (dx or dy):
                return j
            # 그리는 위치는 정수로 반올림되므로 옮긴 뒤 다시 잰다
            j = dict(j, dy=j.get("dy", 0) + (dy or 0), _dx=j.get("_dx", 0) + (dx or 0))
            continue
        # 크다: 글자 크기를 줄인다 (sz 가 있으면 sz, 없으면 scale)
        if j.get("sz"):
            j = dict(j, sz=max(10, int(j["sz"] * 0.93)))
        else:
            j = dict(j, scale=j.get("scale", 1.0) * 0.93)
    warns.append(f"box 에 못 맞춤 {job['box']}")
    return j


def run_jobs(img, spec):
    """작업을 차례로. 작업마다 따로 그린 층을 남겨 둔다 ("ring_of" 가 앞 작업의 글자 모양을 쓴다).
    "ring_of": i  -> i 번째 작업이 그린 글자를 (dx, dy) 만큼 옮겨 바깥으로 "ring" px 넓힌 고리만 흰색(c)으로.
                     속은 투명. 타이틀 메뉴 선택 줄처럼 게임이 회색 글자 위에 겹쳐 그리는 속 빈 테두리 글자용
                     (원본 측정: 고리 = 글자 + 4px, 회색 줄에서 (0,+264), 왼쪽 아래 BACK 은 (-512,+198))."""
    from PIL import ImageChops, ImageFilter
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    warns, made = [], []
    for job in spec["jobs"]:
        if job.get("box") and job.get("lines"):
            job = fit_box(img, job, warns)
        lj = Image.new("RGBA", img.size, (0, 0, 0, 0))
        run_job(img, lj, job, warns)           # ring 작업은 lines 가 비어 있어 원래 글자 지우기만 한다
        if job.get("box") and job.get("lines"):
            bb = lj.getchannel("A").point(lambda v: 255 if v >= 16 else 0).getbbox()
            x0, y0, x1, y1 = job["box"]
            if bb and (bb[0] < x0 or bb[1] < y0 or bb[2] > x1 or bb[3] > y1):
                warns.append(f"box 밖 {bb} > {job['box']}")
        if "ring_of" in job:
            src = made[job["ring_of"]].getchannel("A")
            m = Image.new("L", img.size, 0)
            m.paste(src, (job.get("dx", 0), job.get("dy", 0)))
            r = job.get("ring", 4)
            ring = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(2 * r + 1)), m)
            col = color(job.get("c", "white"))
            lj = Image.new("RGBA", img.size, col + (0,))
            lj.putalpha(ring)
        made.append(lj)
        layer.alpha_composite(lj)
    img.alpha_composite(layer)
    return warns


def render(im, spec):
    a = im.getchannel("A").point(lambda v: min(255, v * 2))
    img = im.copy(); img.putalpha(a)
    warns = run_jobs(img, spec)
    img.putalpha(img.getchannel("A").point(lambda v: (v + 1) // 2))
    return img, warns


def render_png(png, spec):
    """PC 판이 .imz 대신 그리는 조작 장치별 PNG (<이름>_other/_ps/_xbox.png, 알파 0~255) 에 같은 작업."""
    img = png.copy()
    warns = run_jobs(img, spec)
    return img, warns


def mismatch(im, png, box, step=2):
    """imz 그림(알파 0~128)과 PNG 의 box 안 불투명 픽셀 중 색이 다른 비율 (비교할 픽셀이 적으면 None)."""
    a, b = im.load(), png.load()
    x0, y0, x1, y1 = box
    n = bad = 0
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            p, q = a[x, y], b[x, y]
            pa = min(255, p[3] * 2)
            if pa >= 128 or q[3] >= 128:
                n += 1
                # 가장자리 알파·색은 두 그림이 조금씩 달라 넉넉히 본다 (글자가 다르면 크게 어긋난다)
                bad += abs(pa - q[3]) > 128 or (pa >= 128 and q[3] >= 128 and diff(p[:3] + (0,), q[:3] + (0,)) > 64)
    return bad / n if n >= 20 else None


def png_twin(png, ims, spec):
    """PNG 와 같은 배치·같은 글자인 .imz 그림 번호. 전체가 거의 같고, 명세의 작업 영역(글자)마다 5% 미만만 달라야 한다.
    (UK_camp_*.png 는 이름만 UK 이고 글자는 스페인어라 여기서 걸러진다.)"""
    best = None
    for i, (w, h, im) in enumerate(ims):
        if im.size != png.size:
            continue
        k = hashlib.sha1(im.tobytes()).hexdigest()[:10]
        if k not in spec:
            continue
        regions = [mismatch(im, png, (j["r"][0], j["r"][1], j["r"][2] + 1, j["r"][3] + 1), 1) for j in spec[k]["jobs"]]
        if any(r is not None and r >= 0.05 for r in regions):
            continue
        a, b = im.load(), png.load()
        n = bad = 0
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                p, q = a[x, y], b[x, y]
                if p[3] >= 64 and q[3] >= 128:
                    n += 1
                    bad += diff(p[:3] + (0,), q[:3] + (0,)) > 24
        if n > 1000 and bad / n < 0.05 and (best is None or bad / n < best[1]):
            best = (i, bad / n)
    return best[0] if best else None


PNG_VARIANTS = ("other", "ps", "xbox")


def read_spec():
    return json.load(open(SPEC, encoding="utf-8")) if os.path.exists(SPEC) else {}


def all_images():
    for dp, dns, fns in os.walk(os.path.join(P.DATA, "remastered")):
        for fn in fns:
            if fn.startswith("UK_") and fn.endswith(".imz"):
                yield os.path.join(dp, fn)


def main(a):
    spec = read_spec()
    os.makedirs(OUT, exist_ok=True)
    want = set(a[1:])
    done, files, cache = 0, 0, {}
    for src in all_images():
        raw, ims = I.load(src)
        new, hit = [], False
        for w, h, im in ims:
            k = hashlib.sha1(im.tobytes()).hexdigest()[:10]
            if k in spec and (not want or k in want):
                if k not in cache:
                    cache[k] = render(im, spec[k])
                    if cache[k][1]:
                        print("경고", k, spec[k].get("name"), cache[k][1])
                    if a[0] == "preview":
                        both = Image.new("RGB", (w * 2, h))
                        both.paste(I.preview(im), (0, 0)); both.paste(I.preview(cache[k][0]), (w, 0))
                        both.save(os.path.join(OUT, f"{k}_{spec[k].get('name', '')}.png"))
                new.append(cache[k][0]); hit = True; done += 1
            else:
                new.append(im)
        if hit and a[0] == "apply":
            out = os.path.join(P.MOD, os.path.relpath(src, P.DATA))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "wb").write(I.save(raw, new))
            files += 1
        if hit:     # 같은 폴더의 장치별 PNG (게임 확인 2026-11-09: 타이틀 메뉴는 .imz 가 아니라 이것을 그린다)
            stem = src[:-4]
            for v in PNG_VARIANTS:
                pp = f"{stem}_{v}.png"
                if not os.path.exists(pp):
                    continue
                png = Image.open(pp).convert("RGBA")
                i = png_twin(png, ims, spec)
                k = hashlib.sha1(ims[i][2].tobytes()).hexdigest()[:10] if i is not None else None
                if k not in cache:
                    print("PNG 짝 없음 (그대로 둠)", os.path.relpath(pp, P.DATA))
                    continue
                img, warns = render_png(png, spec[k])
                if warns:
                    print("경고", os.path.basename(pp), warns)
                if a[0] == "preview":
                    both = Image.new("RGB", (png.width * 2, png.height))
                    both.paste(I.preview(png), (0, 0)); both.paste(I.preview(img), (png.width, 0))
                    both.save(os.path.join(OUT, f"{k}_{spec[k].get('name', '')}_{v}.png"))
                else:
                    out = os.path.join(P.MOD, os.path.relpath(pp, P.DATA))
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    img.save(out)
                    files += 1
                done += 1
    print(f"그림 {done} (고유 {len(cache)} / 명세 {len(spec)}), 쓴 파일 {files}")


if __name__ == "__main__":
    main(sys.argv[1:])
