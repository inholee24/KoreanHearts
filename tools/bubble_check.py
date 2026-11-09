"""말풍선 넘침 전체 검사 (57차). fixwin_check.py(54차) 를 대신한다.

exe 규칙 (docs/exe-analysis.md 3절, 5절):
- 폭 측정 = msg_layout(0x1767B0) 측정 모드 (msg_get_size 0x174FE0 가 플래그 2 -> 글자·공백 폭 x 0.8333, 글자마다 정수로 자름).
  [0B 00 lo hi] 상대 / [0B 01 lo hi] 절대 / [0B 10 lo hi] 부호 있는 상대 x 이동은 배율 없이 더한다 (0x176C34).
  [07 ..] 는 y 이동 (r15), x 와 무관. 2바이트 첫 바이트 0x1A 는 공백으로 처리된다.
- 창 크기: op4(tpl, w, h) 즉값 (0x1B97D0), op365/op695 는 메시지·이름을 재서 w = 측정 폭 // 24 + 1 (0x1B7C80, 0x175320),
  op179 는 템플릿 둘을 10x2 로. op5(tpl, 종류). op0(tpl) 이 창을 열며 템플릿을 슬롯에 복사 (tpl_apply_b 0x1B942C),
  op1(tpl, msg) 이 그 창에 메시지를 띄운다. 스크립트를 위치 순서로 읽으며 따라간다 (분기는 무시: 근사).
- 스크립트 UK_<월드>_ard<n>.evdl 의 메시지 번호 = UK_<월드>_ard<0x3e8+n>.binl.
- 고정 크기 창: 글이 테두리에 닿는 폭 = cap_of(w) (화면에서 잼). 번역 측정 폭 > max(원문, cap) 이면 넘침. 줄 수 > max(원문, h) 도.
  원문이 cap 보다 넓은 연결은 분기 무시로 생긴 잘못된 연결로 보고 건너뛴다. 자동 크기 창은 내용에 맞춰지므로 검사하지 않는다.
- 측정은 실제 빌드 결과(mod 의 .binl 바이트, mod 의 UK_kanji.knj 폭 표)로 한다. 약 2분 반.

사용: openkh_venv python -I -X utf8 tools/bubble_check.py [-v]
"""
import glob, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evmsg, evmsg_export as ex

ROOT = os.environ.get("KH1KO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOD = os.path.join(ROOT, "mod", "kh1")
DATA = os.path.join(ROOT, "data", "kh1")
SCALE = 0.8333333                     # 0x3E2D84
SPACE = 8                             # 0x4DE838
# 네이티브 번호 -> 인자 수: op0 창 열기(템플릿을 슬롯에 복사), op1 메시지, op4 고정 크기, op179 템플릿 둘 기본(10x2),
# op365 메시지로 크기, op695 이름으로 크기 (vm_opcodes, names.tsv)
CALL = {0: 1, 1: 2, 4: 3, 5: 2, 179: 2, 365: 4, 695: 4}


def width_table(path):
    b = open(path, "rb").read()
    return b[0x40080:0x40080 + 2016]


def sw(W, idx):
    """폭 표 값 (부호 있는 바이트, movsx)."""
    v = W[idx] if idx < len(W) else 0
    return v - 256 if v >= 128 else v


def measure(m, W):
    """측정 모드 줄 폭 목록."""
    lines, x, i = [], 0, 0
    while i < len(m):
        c = m[i]
        if c in (0x00, 0x04):
            break
        if c == 0x02:
            lines.append(x); x = 0; i += 1; continue
        if c == 0x01 or (0x19 <= c <= 0x1F and c == evmsg.BAD_LEAD):
            x += int(SPACE * SCALE); i += 1 if c == 0x01 else 2; continue
        if c >= 0x20:
            x += int(sw(W, c - 0x20) * SCALE); i += 1; continue
        if 0x19 <= c <= 0x1F:
            idx = ((c << 8) | m[i + 1]) - 0x1820
            x += int(sw(W, idx) * SCALE); i += 2; continue
        if c == 0x0B:
            mode, v = m[i + 1], int.from_bytes(m[i + 2:i + 4], "little", signed=True)
            if mode == 0x01:
                x = v
            elif mode in (0x00, 0x10):
                x += v
            i += 4; continue
        i += evmsg.code_len(m, i)
    lines.append(x)
    return lines


# push 즉값 = [v 24bit][09 또는 15], 네이티브 호출 = [n 24bit][18]


def calls(b):
    """(위치, 호출 번호, 인자 목록). 4바이트 정렬이 아닐 수 있어 0~3 바이트 어긋남을 모두 본다."""
    out = {}
    for sh in range(4):
        stack = []
        for p in range(sh, len(b) - 3, 4):
            w = b[p:p + 4]
            if w[3] in (0x09, 0x15):
                stack.append(int.from_bytes(w[:3], "little", signed=True))
            elif w[3] == 0x18:
                n = int.from_bytes(w[:3], "little")
                if n in CALL:
                    need = CALL[n]
                    if len(stack) >= need and all(0 <= a < 0x10000 for a in stack[-need:][:2]):
                        out[p] = (n, stack[-need:])
                stack = []
            else:
                stack = []
    return sorted((p, n, a) for p, (n, a) in out.items())


def main(verbose=False):
    W = width_table(os.path.join(MOD, "exchange", "UK_kanji.knj"))
    W_en = width_table(os.path.join(DATA, "exchange", "UK_kanji.knj"))
    src = dict(ex.source_files())
    shown = defaultdict(set)          # (dir, msg) -> {("fix", w, h) | ("auto",)}
    for ev in sorted(glob.glob(os.path.join(DATA, "remastered", "*.ard", "UK_*.evdl"))):
        d = os.path.basename(os.path.dirname(ev))
        mp = os.path.join(MOD, "remastered", d, os.path.basename(ev))
        b = open(mp if os.path.exists(mp) else ev, "rb").read()
        # 스크립트 UK_<월드>_ard<n>.evdl 의 메시지 번호는 UK_<월드>_ard<0x3e8+n>.binl (모든 .ard 에서 짝이 맞음, 57차)
        n_ev = int(re.search(r"_ard([0-9a-f]+)\.evdl$", ev).group(1), 16)
        rel = f"remastered/{d}/" + re.sub(r"_ard[0-9a-f]+\.evdl$", f"_ard{0x3e8 + n_ev:x}.binl", os.path.basename(ev))
        # 템플릿 크기, 종류(op5), 열린 창(op0 때 복사한 크기·종류). 분기 무시, 위치 순서대로
        tpl, typ, slot = {}, {}, {}
        for p, n, a in calls(b):
            if n == 4:
                tpl[a[0]] = ("fix", a[1], a[2])
            elif n in (365, 695):
                tpl[a[0]] = ("auto", 0, 0)
            elif n == 179:
                tpl[a[0]] = tpl[a[1]] = ("fix", 10, 2)
            elif n == 5:
                typ[a[0]] = a[1]
            elif n == 0 and a[0] in tpl:
                slot[a[0]] = tpl[a[0]] + (typ.get(a[0], -1),)
            elif n == 1:
                k = slot.get(a[0]) or (tpl[a[0]] + (typ.get(a[0], -1),) if a[0] in tpl else None)
                if k:
                    shown[(rel, a[1])].add(k)
    rows = []
    for (rel, msg), kinds in shown.items():
        if rel in src:
            mp = os.path.join(MOD, *rel.split("/"))
            if not os.path.exists(mp):
                continue
            en_msgs = ex.messages(rel, src[rel])[0]
            ko_msgs = ex.messages(rel, open(mp, "rb").read(), root=MOD)[0]
            if msg >= len(en_msgs) or msg >= len(ko_msgs):
                continue
            ew, kw = measure(en_msgs[msg], W_en), measure(ko_msgs[msg], W)
            for k in kinds:
                rows.append((rel.split("/")[1], msg, rel, k, max(ew), max(kw), len(ew), len(kw), en_msgs[msg], ko_msgs[msg]))
    if verbose:
        import pickle
        pickle.dump(rows, open(os.path.join(ROOT, "translation", "build", "bubble_rows.pkl"), "wb"))
    bad, unsure = {}, 0
    for r in rows:
        d, msg, rel, k, ew, kw, el, kl = r[:8]
        if k[0] != "fix" or k[1] == 0 or r[8] == r[9]:
            continue
        key = ex.key_of(r[8])
        if key in KNOWN:
            continue
        cap = cap_of(k[1] + BONUS.get(re.sub(r"^.*/UK_|\.binl$", "", rel), 0))
        if ew > cap + 4:
            # 원문도 안 들어가는 연결: 분기·다른 스크립트에서 정한 크기를 위치 순서로 못 따라간 것으로 본다.
            # 실제 창 크기를 모르므로 원문 폭 + 4 를 한도로 (원문이 들어가는 창이면 번역도 들어간다)
            unsure += 1
            cap = ew + 4
        over = kw - max(ew, cap)
        if over > 0 or kl > max(el, k[2]):
            if key not in bad or over > bad[key][0]:
                bad[key] = (over, r)
    print(f"크기 연결이 불확실해 원문 폭을 한도로 쓴 것 {unsure}, 넘침 {len(bad)} (0 이어야 함)")
    for key, (over, r) in sorted(bad.items(), key=lambda t: -t[1][0]):
        print(f"{over:+4d} {key} {r[2]} #{r[1]} w={r[3][1]} h={r[3][2]} t={r[3][3]} en={r[4]} ko={r[5]} 줄 {r[6]}->{r[7]}  {evmsg.show(r[9])[:70]}")
    return len(bad)


def cap_of(w):
    """폭 w 칸 고정 창에서 글이 테두리에 닿기 전 측정 폭. 사용자 화면(dh06 #27, w=7)에서 잼:
    창 안쪽 약 24(w+2), 글 시작은 안쪽 왼쪽에서 약 24 -> 24(w+1). 여유 4."""
    return 24 * (w + 1) - 4


# 메시지 은행별 영어(UK) 창 폭 추가 칸: exe 표 0x4E5EB0 (0x30B: 은행 이름 포인터, 플래그, 언어별 float[7]).
# 은행을 불러올 때(vm_run_b 0x1A3E85) 이 값을 0x22EC1C4 에 두고, win_open(0x173470) 이 창을 열 때 폭에 더한다
# (tpl_apply_b 의 al 은 기본 1, 몇 장면만 0). 표에 없는 은행은 0 (0x1A58A7).
BONUS = {"di03_ard3e8": 4, "pc12_ard3eb": 4, "tw02_ard3e8": 3, "tw23_ard3eb": 3, "tw26_ard3e8": 3, "tw26_ard3eb": 3,
         "ew31_ard3e8": 0, "ew33_ard3e8": 0, "ew33_ard3ea": 0, "he01_ard3eb": 1, "tw12_ard3e8": 1}

# 검사에서 뺀 것: key -> 이유
KNOWN = {"02d404f4f08d": "al02 #64 '하지만…' 폭 1칸 창 연결 (원문 'But…' 도 안 들어감) -> 연결 오류로 봄"}


if __name__ == "__main__":
    main("-v" in sys.argv)
