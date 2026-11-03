"""KH1 FM exe 전체 색인을 만든다 (exe 읽기 전용).

사용:  D:\\Projects\\openkh_venv\\Scripts\\python -I tools/re/build_index.py
출력:  D:\\Projects\\openkh\\re_index\\
    meta.txt        exe 해시, 섹션, 생성 시각
    functions.tsv   rva  end  size  n_ins  callees  callers  strings(앞 몇 개)
    calls.tsv       caller_func  site  callee   (직접 call/jmp 만. 간접 호출은 빠짐)
    refs.tsv        func  site  target  kind(r/w/lea/imm/disp)  size  mnemonic
                    RIP 상대 참조, [베이스+인덱스+RVA] 변위(disp), .rdata/.data 를 가리키는 즉값
    strings.tsv     rva  section  enc  text   (ASCII 4자 이상, UTF-16LE 4자 이상)
    ptrs.tsv        where  target  target_section   (데이터 영역 8바이트 정렬 포인터)
    tunables.tsv    entry  value_rva  name  init_i32  init_f32   (이름 붙은 조정 변수 표)
    imports.tsv     iat_rva  dll  name

모든 주소는 RVA (ImageBase 0x140000000 기준). exe 가 바뀌면(sha256 다름) 다시 만든다.
"""
import hashlib, re, struct, sys, time
from collections import defaultdict
from pathlib import Path

import capstone
from capstone import x86
import pefile

EXE = Path(r"D:\SteamLibrary\steamapps\common\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-\KINGDOM HEARTS FINAL MIX.exe")
OUT = Path(__file__).resolve().parents[2] / "re_index"


def main():
    raw = EXE.read_bytes()
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    OUT.mkdir(exist_ok=True)

    secs = [(s.Name.rstrip(b"\0").decode(), s.VirtualAddress, s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData)) for s in pe.sections]

    def sec_of(rva):
        for n, a, b in secs:
            if a <= rva < b:
                return n
        return None

    with (OUT / "meta.txt").open("w", encoding="utf-8") as f:
        f.write(f"exe\t{EXE}\nsha256\t{hashlib.sha256(raw).hexdigest()}\nimagebase\t{base:#x}\n")
        f.write(f"built\t{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        for n, a, b in secs:
            f.write(f"section\t{n}\t{a:#x}\t{b:#x}\n")

    # imports
    iat = {}
    with (OUT / "imports.tsv").open("w", encoding="utf-8") as f:
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            for imp in e.imports:
                rva = imp.address - base
                name = imp.name.decode() if imp.name else f"#{imp.ordinal}"
                iat[rva] = f"{e.dll.decode()}!{name}"
                f.write(f"{rva:#x}\t{e.dll.decode()}\t{name}\n")

    # strings (.rdata, .data, _RDATA)
    strings = {}
    with (OUT / "strings.tsv").open("w", encoding="utf-8") as f:
        for s in pe.sections:
            name = s.Name.rstrip(b"\0").decode()
            if name not in (".rdata", ".data", "_RDATA"):
                continue
            data = s.get_data()
            for m in re.finditer(rb"[\x20-\x7e]{4,}", data):
                rva = s.VirtualAddress + m.start()
                txt = m.group().decode("ascii")
                strings[rva] = txt
                f.write(f"{rva:#x}\t{name}\ta\t{txt}\n")
            for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,}", data):
                rva = s.VirtualAddress + m.start()
                txt = m.group().decode("utf-16le")
                strings.setdefault(rva, txt)
                f.write(f"{rva:#x}\t{name}\tw\t{txt}\n")

    # 데이터 안의 포인터 (8바이트 정렬 값이 이미지 안을 가리키면 기록). 문자열 표, 함수 표, vtable 추적용
    img_hi = max(b for n, a, b in secs)
    with (OUT / "ptrs.tsv").open("w", encoding="utf-8") as f:
        for s in pe.sections:
            name = s.Name.rstrip(b"\0").decode()
            if name not in (".rdata", ".data", "_RDATA"):
                continue
            data = s.get_data()
            for off in range(0, len(data) - 7, 8):
                v = int.from_bytes(data[off:off + 8], "little") - base
                if 0x1000 <= v < img_hi:
                    f.write(f"{s.VirtualAddress + off:#x}\t{v:#x}\t{sec_of(v)}\n")

    # 이름 붙은 조정 변수 표: [값 포인터(.data), 이름 포인터(식별자 문자열)] 16바이트 쌍
    ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{2,}$")
    with (OUT / "tunables.tsv").open("w", encoding="utf-8") as f:
        for s in pe.sections:
            if s.Name.rstrip(b"\0").decode() not in (".data", ".rdata"):
                continue
            data = s.get_data()
            for off in range(0, len(data) - 15, 8):
                v = int.from_bytes(data[off:off + 8], "little") - base
                nm = int.from_bytes(data[off + 8:off + 16], "little") - base
                if sec_of(v) == ".data" and nm in strings and ident.match(strings[nm]):
                    val = pe.get_data(v, 4) if v < s.VirtualAddress + len(data) else b""
                    i32 = int.from_bytes(val, "little", signed=True) if len(val) == 4 else ""
                    f32 = struct.unpack("<f", val)[0] if len(val) == 4 else ""
                    f.write(f"{s.VirtualAddress + off:#x}\t{v:#x}\t{strings[nm]}\t{i32}\t{f32:.4g}\n" if val else
                            f"{s.VirtualAddress + off:#x}\t{v:#x}\t{strings[nm]}\t\t\n")

    # functions from .pdata
    funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    data_lo = min(a for n, a, b in secs if n == ".rdata")
    data_hi = max(b for n, a, b in secs if n in (".data", "_RDATA", ".shared"))

    callees = defaultdict(set)
    callers = defaultdict(set)
    fstrings = defaultdict(list)
    nins = {}
    with (OUT / "calls.tsv").open("w", encoding="utf-8") as fc, (OUT / "refs.tsv").open("w", encoding="utf-8") as fr:
        for i, (a, b) in enumerate(funcs):
            code = pe.get_data(a, b - a)
            n = 0
            for ins in md.disasm(code, a):
                n += 1
                mn = ins.mnemonic
                if (mn == "call" or mn.startswith("j")) and ins.operands and ins.operands[0].type == x86.X86_OP_IMM:
                    t = ins.operands[0].imm
                    if mn == "call" or not (a <= t < b):  # 함수 밖으로 가는 jmp = 꼬리 호출
                        fc.write(f"{a:#x}\t{ins.address:#x}\t{t:#x}\t{mn}\n")
                        callees[a].add(t)
                        callers[t].add(a)
                for k, op in enumerate(ins.operands):
                    tgt = kind = None
                    if op.type == x86.X86_OP_MEM and op.mem.base == x86.X86_REG_RIP:
                        tgt = ins.address + ins.size + op.mem.disp
                        if mn == "lea":
                            kind = "lea"
                        else:
                            kind = "w" if (k == 0 and mn.startswith(("mov", "add", "sub", "inc", "dec", "or", "and", "xor"))
                                           and len(ins.operands) > 1) else "r"
                        if mn == "call" and tgt in iat:
                            fc.write(f"{a:#x}\t{ins.address:#x}\t{tgt:#x}\tcall [{iat[tgt]}]\n")
                    elif op.type == x86.X86_OP_MEM and op.mem.base != x86.X86_REG_RIP and data_lo <= op.mem.disp < data_hi:
                        # [이미지베이스 레지스터 + 인덱스 + RVA] 형태 (MSVC x64 표 접근)
                        tgt, kind = op.mem.disp, "disp"
                    elif op.type == x86.X86_OP_IMM and data_lo <= (op.imm - base) < data_hi:
                        tgt, kind = op.imm - base, "imm"
                    if tgt is not None:
                        fr.write(f"{a:#x}\t{ins.address:#x}\t{tgt:#x}\t{kind}\t{op.size}\t{mn} {ins.op_str}\n")
                        if tgt in strings and len(fstrings[a]) < 6:
                            fstrings[a].append(strings[tgt][:60].replace("\t", " "))
            nins[a] = n
            if i % 2000 == 0:
                print(f"  {i}/{len(funcs)}", file=sys.stderr)

    with (OUT / "functions.tsv").open("w", encoding="utf-8") as f:
        f.write("rva\tend\tsize\tn_ins\tcallees\tcallers\tstrings\n")
        for a, b in funcs:
            f.write(f"{a:#x}\t{b:#x}\t{b - a}\t{nins[a]}\t{len(callees[a])}\t{len(callers[a])}\t{' | '.join(fstrings[a])}\n")
    print(f"functions {len(funcs)}, strings {len(strings)} -> {OUT}")


if __name__ == "__main__":
    main()
