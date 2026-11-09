"""Re:COM 글꼴 폭·매핑 표 `FFMW` (*_sysfont.binl, *_evtfont.binl) 분석.

사용: python recom_ffmw.py <binl> [dump]
"""
import struct, sys


def parse(b):
    assert b[:4] == b"FFMW"
    ver, a, mofs, z, wofs = struct.unpack_from("<HHHHI", b, 4)
    n_map = (len(b) - mofs) // 2
    m = list(struct.unpack_from(f"<{n_map}H", b, mofs))
    return dict(ver=ver, a=a, mofs=mofs, wofs=wofs, widths=b[wofs:a], extra=b[a:mofs], map=m)


if __name__ == "__main__":
    b = open(sys.argv[1], "rb").read()
    d = parse(b)
    m = d["map"]
    print(f"ver {d['ver']} widths@{d['wofs']:#x}..{d['a']:#x} ({d['a'] - d['wofs']}) extra {d['extra'].hex()} map@{d['mofs']:#x} n={len(m)}")
    nz = [(i, v) for i, v in enumerate(m) if v]
    print("nonzero", len(nz), "max glyph", max(v for _, v in nz))
    # 연속 구간 요약
    runs, s = [], None
    for i, v in nz:
        if s and i == s[1] + 1:
            s[1] = i
        else:
            if s:
                runs.append(tuple(s))
            s = [i, i]
    runs.append(tuple(s))
    for a, e in runs:
        print(f"  idx {a:5d}-{e:5d} (n={e - a + 1})  glyph {m[a]}..{m[e]}")
