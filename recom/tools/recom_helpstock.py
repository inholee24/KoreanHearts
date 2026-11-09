"""슬라이트 도움말 그림 (UK_help_stock.imz, 1024x1024, 고유 100 장) 의 글 영역 검출·다시 그리기.

틀 (2026-11-06 측정, 모든 장 공통 색):
  제목 막대  y 18~72, 흰 테두리 안 검정 (0,0,0) 위 흰 글자. 오른쪽 "PAGE 1/1" 상자는 그대로 둔다.
  파란 패널  배경 단색 (18,32,105,a128). 글줄: 이름(하늘색 기울임 + 아래 그라데이션 밑줄), 설명(흰색),
             "Activation"(노랑), 조건(흰색 + 노란 숫자) 또는 검정 알약 칸(흰 글자)과 "+".
  Example 상자, TIPS 제목(노랑 + 밑줄).
검출: 패널·상자 배경색과 다른 픽셀의 행 묶음 = 글줄. 높이 4px 이하이고 넓은 묶음 = 밑줄 (건드리지 않음).
      검정 알약은 패널 안 (0,0,0) 덩어리.
사용: python -I recom_helpstock.py detect <목록 번호...>   -> translation/build/helpstock/det_<번호>.png (상자 표시)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import recom_imz as I, recom_paths as P

BG = (18, 32, 105)
BLACK = (0, 0, 0)
OUT = os.path.join(P.TR, "build", "helpstock")


def close(c, ref, tol=6):
    return all(abs(a - b) <= tol for a, b in zip(c[:3], ref))


def bg_run(px, W, y, bg=BG):
    """행 y 에서 가장 긴 bg 구간 (x0, x1) 또는 None."""
    best, start = None, None
    for x in range(W + 1):
        on = x < W and close(px[x, y], bg)
        if on and start is None:
            start = x
        elif not on and start is not None:
            if best is None or x - 1 - start > best[1] - best[0]:
                best = (start, x - 1)
            start = None
    return best


def panel_rect(px, W, H, yrow=90, ymax=None, bg=BG):
    """파란 패널의 (x0, y0, x1, y1). yrow 행(이름 글자보다 위)에서 가장 긴 bg 구간 = 패널 폭,
    그 양쪽 안쪽 세로줄 중 하나라도 bg 인 동안 = 패널 높이. 보통 틀·High Jump·다크 모드 설명 모두 같은 방법."""
    run = bg_run(px, W, yrow, bg)
    if run is None or run[1] - run[0] < 300:
        return None
    x0, x1 = run
    ca, cb = x0 + 6, x1 - 6
    y0 = yrow
    while y0 - 1 > 0 and (close(px[ca, y0 - 1], bg) or close(px[cb, y0 - 1], bg)):
        y0 -= 1
    y1 = yrow
    while y1 + 1 < (ymax or H) and (close(px[ca, y1 + 1], bg) or close(px[cb, y1 + 1], bg)):
        y1 += 1
    return x0, y0, x1, y1


def rows_groups(mask_rows, gap=2):
    groups, cur = [], None
    for y in sorted(mask_rows):
        if cur and y - cur[1] <= gap + 1:
            cur[1] = y
        else:
            if cur:
                groups.append(cur)
            cur = [y, y]
    if cur:
        groups.append(cur)
    return groups


def detect(im):
    """-> dict(title=(bbox), panel=(rect), items=[(kind, bbox)], example=bbox|None, tips=bbox|None)."""
    W, H = im.size
    px = im.load()
    # 패널 배경색: y=90 행의 파란 계열 색 중 가장 많은 것 (보통 (18,32,105), 다크 모드 설명은 (14,23,88))
    import collections
    blues = collections.Counter(px[x, 90][:3] for x in range(W) if px[x, 90][2] > 60 and px[x, 90][2] > px[x, 90][0] + 40)
    bg = blues.most_common(1)[0][0] if blues else BG
    # 제목 막대: y 20~70, x 40~700 의 밝은 픽셀
    tb = [(x, y) for y in range(27, 64) for x in range(50, 705) if sum(px[x, y][:3]) > 300]   # 막대 테두리(y~20, ~70) 제외
    title = (min(x for x, _ in tb), min(y for _, y in tb), max(x for x, _ in tb), max(y for _, y in tb)) if tb else None
    pr = panel_rect(px, W, H, bg=bg)
    if pr is None:
        return None
    x0, y0, x1, y1 = pr
    items = []
    # 알약: 패널 안 검정 덩어리 (행에 검정이 60px 이상)
    pill_rows = [y for y in range(y0, y1) if sum(close(px[x, y], BLACK, 3) for x in range(x0 + 5, x1 - 5, 3)) > 20]
    for a, b in rows_groups(pill_rows):
        if b - a < 20:
            continue
        y = a + 4                             # 알약 윗부분 (글자 없음) 에서 검정 구간 = 알약 폭
        runs, start = [], None
        for x in range(x0 + 2, x1 - 2):
            on = close(px[x, y], BLACK, 3)
            if on and start is None:
                start = x
            elif not on and start is not None:
                if x - start > 60:
                    runs.append((start, x - 1))
                start = None
        for s, e in runs:
            items.append(("pill", (s, a, e, b)))
    pill_band = {y for k, (bx0, by0, bx1, by1) in items if k == "pill" for y in range(by0 - 4, by1 + 5)}
    # 이름 밑줄: 패널 위쪽 70px 안에서 x 300~500 이 모두 bg 가 아닌 얇은 행들 (그라데이션 선)
    # (흰 글자 줄과 구별: 해당 행 x 150~550 이 전부 bg 가 아니고 흰색(R>180)이 없어야 함)
    ul = [y for y in range(y0 + 30, y0 + 64)
          if all(not close(px[x, y], bg, 10) and px[x, y][0] < 180 for x in range(x0 + 40, x0 + 301, 26))]   # 밑줄은 왼쪽이 진하다
    if ul:                                    # 긴 이름 글자 행이 섞일 수 있어 맨 아래 얇은 묶음만 밑줄로
        a_, b_ = rows_groups(ul, gap=0)[-1]
        ul = list(range(a_, b_ + 1)) if b_ - a_ <= 8 else []
    if ul:
        items.append(("underline", (x0 + 10, min(ul), x1 - 10, max(ul))))
    skip = pill_band | set(ul)
    text_rows = {}
    for y in range(y0 + 4, y1 - 4):          # 패널 테두리(약 4px) 안쪽만
        if y in skip:
            continue
        xs = [x for x in range(x0 + 10, x1 - 10) if not close(px[x, y], bg, 10)]
        if xs:
            text_rows[y] = xs
    for a, b in rows_groups(text_rows):
        xs = [x for y in range(a, b + 1) for x in text_rows.get(y, [])]
        bb = (min(xs), a, max(xs), b)
        if b - a <= 4 and bb[2] - bb[0] > 200:
            items.append(("underline", bb)); continue
        if b - a < 6:
            continue
        # 색: 노랑(R,G 높고 B 낮음) / 하늘색(B 높음, R 낮음) / 흰색
        cols = [px[x, y] for y in range(a, b + 1) for x in text_rows.get(y, []) if sum(px[x, y][:3]) > 450]
        yel = sum(1 for c in cols if c[0] > 200 and c[1] > 180 and c[2] < 120)
        cya = sum(1 for c in cols if c[2] > 200 and c[0] < 170)
        kind = "yellow" if yel > len(cols) * 0.6 else "cyan" if cya > len(cols) * 0.5 else "white"
        if kind == "white" and yel > 10:
            kind = "white+yellow"
        items.append((kind, bb))
    items.sort(key=lambda it: (it[1][1], it[1][0]))
    # Example 상자: 패널 아래 x 70~320 의 bg 덩어리 안 흰 글자
    def white_in(xa, ya, xb, yb):
        pts = [(x, y) for y in range(ya, yb) for x in range(xa, xb) if sum(px[x, y][:3]) > 600]
        return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None
    # Example: x=100 이 bg 인 행들 (파란 상자) 안의 흰 글자
    eys = [y for y in range(y1 + 5, min(H, y1 + 320)) if close(px[100, y], bg, 10)]
    example = white_in(80, min(eys), 320, max(eys)) if eys else None
    tips = None
    # TIPS: x=950 이 bg 인 행들 (오른쪽 파란 상자) 안의 노란 글자
    tys = {y for y in range(y1 + 5, min(H, y1 + 450)) if close(px[950, y], bg, 10)}
    ys = [y for y in sorted(tys) for x in range(500, 800, 3) if px[x, y][0] > 200 and px[x, y][1] > 180 and px[x, y][2] < 100]
    if ys:
        ya, yb = min(ys), max(ys)
        xs = [x for y in range(ya, yb + 1) for x in range(300, 1000) if px[x, y][0] > 200 and px[x, y][1] > 180 and px[x, y][2] < 100]
        tips = (min(xs), ya, max(xs), yb)
    return dict(title=title, panel=(x0, y0, x1, y1), items=items, example=example, tips=tips, bg=bg)


# ---------------------------------------------------------------- 다시 그리기
SPEC = os.path.join(P.TR, "src", "helpstock.tsv")
TTF = r"C:\Windows\Fonts\malgunbd.ttf"
WHITE, CYAN, YELLOW = (238, 238, 238), (96, 190, 240), (255, 232, 0)
SHADOW = (8, 8, 36)
FIXED = {"act": "발동 조건", "example": "예시", "tips": "팁"}
_fonts = {}


def font(px):
    from PIL import ImageFont
    if px not in _fonts:
        _fonts[px] = ImageFont.truetype(TTF, px)
    return _fonts[px]


def read_spec():
    out = {}
    lines = open(SPEC, encoding="utf-8").read().split("\n")
    for ln in lines[1:]:
        if ln.strip():
            f = (ln.split("\t") + [""] * 5)[:5]
            out[f[0]] = dict(title=f[1], desc=[s for s in f[2].split("\\n") if s], cond=[s for s in f[3].split("\\n") if s],
                             pills=[s for s in f[4].split("|") if s])
    return out


def segments(s, base):
    """'abc [[12]] d' -> [(abc, base), (12, YELLOW), ( d, base)]"""
    out, rest = [], s
    while "[[" in rest:
        a, b = rest.split("[[", 1)
        y, rest = b.split("]]", 1)
        if a:
            out.append((a, base))
        out.append((y, YELLOW))
    if rest:
        out.append((rest, base))
    return out


def text_w(segs, f):
    return sum(f.getlength(t) for t, _ in segs)


def draw_line(layer, x, cy, segs, px, maxw, shadow=True, italic=False, center=False):
    """한 줄 그리기. (x, cy) = 왼쪽(또는 가운데) x, 세로 가운데. 폭이 넘치면 글자 크기를 줄인다. -> 경고 문자열|None"""
    from PIL import ImageDraw
    warn = None
    while px > 20 and text_w(segs, font(px)) > maxw:
        px -= 1
    if text_w(segs, font(px)) > maxw:
        warn = f"폭 넘침 {text_w(segs, font(px)):.0f}>{maxw}"
    f = font(px)
    w = int(text_w(segs, f)) + 8
    h = px + 16
    tl = Image.new("RGBA", (w + h // 3 + 6, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tl)
    for off, use_shadow in (((3, 3), True), ((0, 0), False)):
        if use_shadow and not shadow:
            continue
        xx = 2 + off[0]
        for t, col in segs:
            dr.text((xx, h // 2 + off[1]), t, font=f, fill=(SHADOW if use_shadow else col) + (255,), anchor="lm")
            xx += f.getlength(t)
    if italic:
        s = 0.2
        tl = tl.transform(tl.size, Image.AFFINE, (1, s, -s * h, 0, 1, 0), resample=Image.BICUBIC)
    left = int(x - (w / 2 if center else 0)) - 2
    layer.alpha_composite(tl, (left, int(cy - h // 2)))
    return warn


def fill(img, bb, color):
    from PIL import ImageDraw
    ImageDraw.Draw(img).rectangle(bb, fill=tuple(color[:3]) + (255,))


def render(im, spec):
    """원본 RGBA(알파 0~128) -> 한글로 다시 그린 RGBA, 경고 목록."""
    d = detect(im)
    if d is None:
        raise ValueError("틀이 달라 자동 처리 불가")
    W, H = im.size
    # 알파 0~128 -> 0~255 로 펴서 작업 (되돌릴 때 (a+1)//2: 원본 값 그대로 돌아옴)
    a = im.getchannel("A").point(lambda v: min(255, v * 2))
    img = im.copy(); img.putalpha(a)
    px = img.load()
    warns = []
    x0, y0, x1, y1 = d["panel"]
    ul = [bb for k, bb in d["items"] if k == "underline"]
    ul_top = min(bb[1] for bb in ul) if ul else y0
    texts = [(k, bb) for k, bb in d["items"] if k in ("cyan", "white", "yellow", "white+yellow")]
    pills = [bb for k, bb in d["items"] if k == "pill"]
    # 지우기
    if d["title"]:
        tx0, ty0, tx1, ty1 = d["title"]
        fill(img, (tx0 - 3, ty0 - 3, tx1 + 3, ty1 + 3), BLACK)
    for k, (a0, b0, a1, b1) in texts:
        top, bot = b0 - 2, b1 + 4
        if b1 < ul_top:
            bot = min(bot, ul_top - 1)
        fill(img, (max(x0 + 6, a0 - 3), top, min(x1 - 6, a1 + 4), bot), d["bg"])
    for (a0, b0, a1, b1) in pills:
        # 알약 안 글자(흰~회색, r≈b)만 검정으로. 파란 BG 가장자리(b >> r)는 건드리지 않는다
        for y in range(b0, b1 + 1):
            for x in range(a0, a1 + 1):
                r, g, b_, al = px[x, y]
                if r > 25 and abs(r - b_) < 45:
                    px[x, y] = (0, 0, 0, al)
    if d["example"]:
        ex = d["example"]; c = px[ex[0] - 8, (ex[1] + ex[3]) // 2]
        fill(img, (ex[0] - 3, ex[1] - 3, ex[2] + 5, ex[3] + 4), c)
    if d["tips"] and d["example"]:    # TIPS 는 Example 이 있는 보통 틀에만
        tp = d["tips"]; c = px[tp[0] - 10, tp[1] + 3]
        # 밑줄: 글자보다 왼쪽(x = tp[0]-25)에서도 색이 있는 첫 행 -> 그 위까지만 지운다
        ulx = tp[0] - 25
        uly = next((y for y in range(tp[1], tp[3] + 12) if not close(px[ulx, y], c, 12)), tp[3] + 2)
        fill(img, (tp[0] - 3, tp[1] - 2, tp[2] + 5, uly - 1), c)
        # 밑줄 행에 남은 글자 그림자: 글자 폭 양쪽 바깥 색을 이어 메운다
        xa, xb = tp[0] - 6, tp[2] + 8
        for y in range(uly, min(H, uly + 6)):
            la, ra = px[xa, y], px[xb, y]
            for x in range(xa + 1, xb):
                t = (x - xa) / (xb - xa)
                px[x, y] = tuple(int(la[i] * (1 - t) + ra[i] * t) for i in range(4))
    # 그리기
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ctr = lambda bb: (bb[1] + bb[3] - 3) / 2          # 그림자(약 3px) 뺀 세로 가운데
    if d["title"]:
        tb = d["title"]
        w_ = draw_line(layer, (tb[0] + tb[2]) / 2, ctr(tb) + 1, [(spec["title"], (255, 255, 255))], 32, 640, shadow=False, center=True)
        w_ and warns.append("제목 " + w_)
    if not texts:
        warns.append("글줄 없음")
    name = texts[0] if texts and texts[0][0] == "cyan" else None
    if name:
        warns += [w for w in [draw_line(layer, name[1][0], ctr(name[1]), [(spec["title"], CYAN)], 30, x1 - 30 - name[1][0], italic=True)] if w]
    # "Activation" = 이름과 같은 들여쓰기(왼쪽 끝)의 노란 줄. 들여 쓴 노란 줄은 설명의 강조 (다크 모드 설명)
    nx = name[1][0] if name else x0 + 20
    act_i = next((i for i, (k, bb) in enumerate(texts) if k == "yellow" and bb[0] < nx + 15), None)
    desc_boxes = [bb for k, bb in texts[1:act_i if act_i is not None else len(texts)]]
    cond_boxes = [bb for k, bb in texts[act_i + 1:]] if act_i is not None else []
    act_top = texts[act_i][1][1] if act_i is not None else y1

    def lines_at(boxes, lines, base_x, limit, color=WHITE, size=28):
        if not lines:
            return
        if boxes:
            c0 = ctr(boxes[0])
            pitch = (ctr(boxes[-1]) - c0) / (len(boxes) - 1) if len(boxes) > 1 else 38
        else:
            return warns.append("자리 없는 줄")
        pitch = max(pitch, 36)
        if c0 + pitch * (len(lines) - 1) + 14 > limit:
            pitch = max(30, (limit - 14 - c0) / max(1, len(lines) - 1))
            size = min(size, int(pitch * 0.8))
            if c0 + pitch * (len(lines) - 1) + 14 > limit:
                warns.append(f"줄 수 넘침 {len(lines)}")
        for i, s in enumerate(lines):
            w_ = draw_line(layer, base_x, c0 + pitch * i, segments(s, color), size, x1 - 16 - base_x)
            w_ and warns.append(w_ + " | " + s)

    if desc_boxes or spec["desc"]:
        if not desc_boxes and spec["desc"]:
            warns.append("설명 자리 없음")
        lines_at(desc_boxes, spec["desc"], desc_boxes[0][0] if desc_boxes else 86, act_top)
    if act_i is not None:
        ab = texts[act_i][1]
        draw_line(layer, ab[0], ctr(ab), [(FIXED["act"], YELLOW)], 30, 400, italic=True)
    if act_i is None and spec["cond"]:
        # 발동 조건이 없는 틀 (다크 모드 설명): cond = 아래 두 번째 상자의 줄 (첫 줄 하늘색 기울임, 나머지 흰색)
        bg = d["bg"]
        yr = next((y for y in range(y1 + 10, H - 5) if (bg_run(px, W, y, bg) or (0, 0))[1] - (bg_run(px, W, y, bg) or (0, 0))[0] > 300), None)
        p2 = panel_rect(px, W, H, yrow=yr, bg=bg) if yr else None
        if not p2:
            warns.append("두 번째 상자 없음")
        else:
            qx0, qy0, qx1, qy1 = p2
            rows2 = {y: [x for x in range(qx0 + 10, qx1 - 10) if not close(px[x, y], bg, 10)] for y in range(qy0 + 4, qy1 - 4)}
            # 밑줄 행 (넓게 이어지고 흰색 없음) 은 글줄에서 뺀다 -> 지우지 않음
            for y, v in list(rows2.items()):
                if v and v[-1] - v[0] > 300 and len(v) > 0.9 * (v[-1] - v[0]) and max(px[x, y][0] for x in v) < 180:
                    rows2[y] = []
            grp = [(a_, b_) for a_, b_ in rows_groups([y for y, v in rows2.items() if v]) if b_ - a_ >= 6]
            boxes2 = []
            for a_, b_ in grp:
                xs = [x for y in range(a_, b_ + 1) for x in rows2[y]]
                boxes2.append((min(xs), a_, max(xs), b_))
                fill(img, (max(qx0 + 6, min(xs) - 3), a_ - 2, min(qx1 - 6, max(xs) + 4), b_ + 4), bg)
            for i, (bb, s) in enumerate(zip(boxes2, spec["cond"])):
                if i == 0:
                    w_ = draw_line(layer, bb[0], ctr(bb), [(s, CYAN)], 28, qx1 - 16 - bb[0], italic=True)
                else:
                    w_ = draw_line(layer, (qx0 + qx1) / 2, ctr(bb), segments(s, WHITE), 26, qx1 - qx0 - 30, center=True)
                w_ and warns.append(w_)
            if len(boxes2) != len(spec["cond"]):
                warns.append(f"두 번째 상자 줄 수 {len(spec['cond'])} != {len(boxes2)}")
    elif cond_boxes or spec["cond"]:
        lines_at(cond_boxes, spec["cond"], cond_boxes[0][0] if cond_boxes else 86, y1)
    if len(spec["pills"]) != len(pills):
        warns.append(f"알약 수 {len(spec['pills'])} != {len(pills)}")
    for bb, s in zip(pills, spec["pills"]):
        w_ = draw_line(layer, (bb[0] + bb[2]) / 2, ctr(bb) + 2, [(s, WHITE)], 28, bb[2] - bb[0] - 30, shadow=False, center=True)
        w_ and warns.append(w_)
    if d["example"]:
        ex = d["example"]
        draw_line(layer, (ex[0] + ex[2]) / 2, ctr(ex), [(FIXED["example"], WHITE)], 30, 200, center=True)
    if d["tips"] and d["example"]:
        tp = d["tips"]
        draw_line(layer, (tp[0] + tp[2]) / 2, ctr(tp), [(FIXED["tips"], YELLOW)], 34, 200, italic=True, center=True)
    img.alpha_composite(layer)
    img.putalpha(img.getchannel("A").point(lambda v: (v + 1) // 2))
    return img, warns


def main(a):
    lst = os.path.join(P.TR, "build", "imz_sheets", "list.tsv")      # 개발용 목록 (preview/detect 만 씀, apply 는 필요 없음)
    rows = [l.rstrip("\n").split("\t") for l in open(lst, encoding="utf-8")] if a[0] != "apply" else []
    os.makedirs(OUT, exist_ok=True)
    if a[0] == "apply":
        # 모든 UK imz 중 명세에 있는 그림(픽셀 sha1 앞 10자리)을 다시 그려 mod/recom 같은 경로에 쓴다
        import hashlib
        spec = read_spec()
        done, files, warn_n, cache = 0, 0, 0, {}
        for dp, dns, fns in os.walk(os.path.join(P.DATA, "remastered")):
            for fn in fns:
                if not (fn.startswith("UK_") and fn.endswith(".imz")):
                    continue
                src = os.path.join(dp, fn)
                raw, ims = I.load(src)
                new, hit = [], False
                for w, h, im in ims:
                    k = hashlib.sha1(im.tobytes()).hexdigest()[:10]
                    if k in spec:
                        if k not in cache:
                            cache[k] = render(im, spec[k])
                            if cache[k][1]:
                                print("경고", k, cache[k][1]); warn_n += 1
                        new.append(cache[k][0]); hit = True; done += 1
                    else:
                        new.append(im)
                if hit:
                    rel = os.path.relpath(src, P.DATA)
                    out = os.path.join(P.MOD, rel)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    open(out, "wb").write(I.save(raw, new))
                    files += 1
        print(f"다시 그린 그림 {done} (고유 {len(cache)} / 명세 {len(spec)}), 쓴 파일 {files}, 경고 {warn_n}")
    if a[0] == "preview":
        spec = read_spec()
        want = set(map(int, a[1:])) if len(a) > 1 else None
        for r in rows:
            if "help_stock" not in r[2] or (want and int(r[0]) not in want) or r[1] not in spec:
                continue
            im = I.load(os.path.join(P.DATA, r[2]))[1][int(r[3])][2]
            try:
                new, warns = render(im, spec[r[1]])
            except ValueError as e:
                print(r[0], "건너뜀:", e); continue
            both = Image.new("RGB", (2048, 1024))
            both.paste(I.preview(im), (0, 0)); both.paste(I.preview(new), (1024, 0))
            both.crop((0, 0, 2048, 780)).save(os.path.join(OUT, f"pv_{r[0]}.png"))
            if warns:
                print(r[0], r[1], warns)
    if a[0] == "detect":
        for n in map(int, a[1:]):
            r = rows[n]
            _, ims = I.load(os.path.join(P.DATA, r[2]))
            im = ims[int(r[3])][2]
            d = detect(im)
            v = I.preview(im); dr = ImageDraw.Draw(v)
            for k in ("title", "example", "tips"):
                if d[k]:
                    dr.rectangle(d[k], outline=(255, 0, 255))
            dr.rectangle(d["panel"], outline=(0, 255, 0))
            for kind, bb in d["items"]:
                dr.rectangle(bb, outline={"pill": (255, 128, 0), "underline": (128, 128, 128)}.get(kind, (255, 0, 0)))
                dr.text((bb[2] + 3, bb[1]), kind, fill=(0, 255, 0))
            v.save(os.path.join(OUT, f"det_{n}.png"))
            print(n, d["panel"], [(k, bb) for k, bb in d["items"]])


if __name__ == "__main__":
    main(sys.argv[1:])
