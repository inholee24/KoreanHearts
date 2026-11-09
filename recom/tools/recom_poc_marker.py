"""PoC 1: 게임이 어느 CTD 를 읽는지 가르는 표식 (같은 길이 바이트 치환, 구조 변경 없음).

FO0111 (New Game 설정 화면) 메시지 #29 "Please select a game mode." 의 "Please" 를
  원본 CTD      -> "BASECT"
  UK .ctdl      -> "UKCTDL"
로 바꿔 mod 폴더에 쓴다. 화면에 나온 표식으로 읽는 파일을 안다.

사용: python recom_poc_marker.py <추출 원본 Recom 폴더> <mod\\recom 폴더> [--remove]
--remove: 이 스크립트가 만든 파일만 지운다 (내용이 표식본과 같을 때만).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_ctd

FILES = [("FORM/0111/FO0111.CTD", b"BASECT"),
         ("remastered/FORM/0111/FO0111.CTD/UK_CT0005.ctdl", b"UKCTDL")]
MSG = 29


def marked(src, tag):
    b = bytearray(open(src, "rb").read())
    d = recom_ctd.parse(bytes(b))
    m = d["msgs"][MSG]
    assert m.startswith(b"Please select a game mode."), m
    o = b.find(m)
    assert b.count(m) == 1
    b[o:o + 6] = tag
    d2 = recom_ctd.parse(bytes(b))
    assert d2["msgs"][MSG].startswith(tag) and len(b) == os.path.getsize(src)
    assert [x for i, x in enumerate(d2["msgs"]) if i != MSG] == [x for i, x in enumerate(d["msgs"]) if i != MSG]
    return bytes(b)


if __name__ == "__main__":
    data, mod = sys.argv[1], sys.argv[2]
    for rel, tag in FILES:
        out = os.path.join(mod, *rel.split("/"))
        want = marked(os.path.join(data, *rel.split("/")), tag)
        if "--remove" in sys.argv:
            if os.path.exists(out) and open(out, "rb").read() == want:
                os.remove(out)
                print("지움", out)
            continue
        if os.path.exists(out) and open(out, "rb").read() != want:
            raise SystemExit(f"이미 다른 파일이 있음 (덮어쓰지 않음): {out}")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(want)
        print("씀", out, tag.decode())
