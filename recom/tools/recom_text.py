"""Re:COM 메시지 바이트 <-> 번역 표 표기.

표기 (show / encode, 왕복 일치):
  \\n        줄바꿈 0x0A
  [F9 59]   2바이트 제어 코드 (F5/F6 아이콘, F9 색). 번역에서 그대로 보존
  {81A1}    2바이트 글자 (Shift-JIS 계열 코드)
  {5B}      표기 기호와 겹치는 1바이트 문자 ([ { < \\) 와 0x7F
  <0B>      그 밖의 0x20 미만 바이트
  그 외     1바이트 ASCII 글자. 한글(가~힣)은 encode 때 charmap 의 2바이트 코드로
디코더 규칙 (exe 0x258F20): 0x80 이상 바이트는 항상 2바이트.
"""
import re

CTRL2 = (0xF5, 0xF6, 0xF9)
ESC1 = set(b"[{<\\") | {0x7F}
TOKEN = re.compile(r"\[[0-9A-F]{2} [0-9A-F]{2}\]|\{[0-9A-F]{4}\}|\{[0-9A-F]{2}\}|<[0-9A-F]{2}>|\\n|.", re.S)


def show(m, rev=None):
    """rev: {코드: 글자} (빌드된 한글 해독용)."""
    out, i = [], 0
    while i < len(m):
        c = m[i]
        if c >= 0x80:
            t = m[i + 1] if i + 1 < len(m) else 0
            code = (c << 8) | t
            if c in CTRL2:
                out.append(f"[{c:02X} {t:02X}]")
            elif rev and code in rev:
                out.append(rev[code])
            else:
                out.append(f"{{{code:04X}}}")
            i += 2
            continue
        if c == 0x0A:
            out.append("\\n")
        elif c < 0x20:
            out.append(f"<{c:02X}>")
        elif c in ESC1:
            out.append(f"{{{c:02X}}}")
        else:
            out.append(chr(c))
        i += 1
    return "".join(out)


def tokens(s):
    return TOKEN.findall(s)


def encode(s, charmap=None):
    """표기 -> 바이트. charmap: {한글 글자: 2바이트 코드}. 모르는 글자는 ValueError."""
    out = bytearray()
    for t in tokens(s):
        if t == "\\n":
            out.append(0x0A)
        elif len(t) == 7 and t[0] == "[":
            out += bytes([int(t[1:3], 16), int(t[4:6], 16)])
        elif len(t) == 6 and t[0] == "{":
            out += int(t[1:5], 16).to_bytes(2, "big")
        elif len(t) == 4 and t[0] == "{":
            out.append(int(t[1:3], 16))
        elif len(t) == 4 and t[0] == "<":
            out.append(int(t[1:3], 16))
        elif len(t) == 1 and 0x20 <= ord(t) < 0x7F and ord(t) not in ESC1:
            out.append(ord(t))
        elif charmap is not None and t in charmap:
            out += charmap[t].to_bytes(2, "big")
        else:
            raise ValueError(f"표기할 수 없는 글자: {t!r} (U+{ord(t[0]):04X})")
    return bytes(out)


def structure(s):
    """구조 토큰(제어 코드, %s 류 자리표시)만의 순서 (번역 검사용). 줄바꿈은 제외."""
    return re.findall(r"\[[0-9A-F]{2} [0-9A-F]{2}\]|%[0-9]*[sd]|<[0-9A-F]{2}>", s)


def is_hangul(ch):
    return "가" <= ch <= "힣"
