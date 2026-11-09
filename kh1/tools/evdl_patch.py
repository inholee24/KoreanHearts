"""이벤트 스크립트(.evdl) 즉값 고치기 (24차 상점 선택지 창 폭).

트래버스 타운 상점 선택지 창은 스크립트 op4(창 2, 폭, 높이) 의 즉값으로 폭이 정해진다 (docs/exe-analysis.md 3절).
원문 영어 폭 7칸이면 한글 선택지 '아무것도 아니에요.' 가 넘쳐서 9칸으로 넓힌다 (24차 확인). 파일당 1바이트, 길이 불변.

  python tools/evdl_patch.py          확인만
  python tools/evdl_patch.py --apply  mod/kh1 에 쓴다
"""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import evmsg_export as ex

MOD = os.path.join(ex.ROOT, "mod", "kh1")
# (파일, 원본 바이트 열, 바꿀 바이트 열): 원본에서 정확히 한 번 나와야 한다
OP4_7 = bytes.fromhex("02000009 07000009 03000009 04000018".replace(" ", ""))
OP4_9 = bytes.fromhex("02000009 09000009 03000009 04000018".replace(" ", ""))
PATCHES = [(f"remastered/tw11.ard/{lang}_tw11_ard{n}.evdl", OP4_7, OP4_9) for lang in ("UK", "US") for n in (0, 2)]


def main(apply):
    for rel, old, new in PATCHES:
        b = open(os.path.join(ex.DATA, rel), "rb").read()
        if b.count(old) != 1:
            sys.exit(f"{rel}: 바꿀 자리 {b.count(old)}곳 (1곳이어야 함)")
        out = b.replace(old, new)
        if apply:
            p = os.path.join(MOD, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(out)
        print(("썼음 " if apply else "확인 ") + rel)


if __name__ == "__main__":
    main("--apply" in sys.argv)
