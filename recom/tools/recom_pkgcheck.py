"""kh1/tools/pkgextract.py 가 Re:COM 패키지(Image/dt/Recom.hed/.pkg)에서도 쓰이는지 확인 (읽기 전용).

샘플 파일(원본 + 리마스터 자산 포함)을 임시 폴더로 꺼내 OpenKH 추출본(D:/Projects/openkh/data/Recom)과 바이트 비교.
사용: python -I recom_pkgcheck.py <게임 폴더> <임시 출력 폴더> [이름 ...]
"""
import hashlib, importlib.util, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pkgextract", HERE.parents[1] / "kh1" / "tools" / "pkgextract.py")
pk = importlib.util.module_from_spec(spec); spec.loader.exec_module(pk)

REF = Path(r"D:\Projects\openkh\data\Recom")
NAMES = ["FORM/0111/FO0111.CTD", "SYS/0001/SY0001.BIN", "SYS/0001/SY0001.VTM", "FORM/5000/FO5000.BIN", "WORLD04/1050/US/WO041050.CTD"]

if __name__ == "__main__":
    game, out = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or NAMES
    p = pk.Pkgs(game, ("Image/dt/Recom.hed",))
    print("hed 항목", len(p.idx))
    for n in names:
        print(" ", n, "리마스터", pk.extract(p, n, out))
    same = diff = missing = 0
    for dp, dns, fns in os.walk(out):
        for f in fns:
            q = Path(dp) / f
            rel = q.relative_to(out)
            r = REF / rel
            if not r.exists():
                missing += 1; print("  기준에 없음", rel); continue
            if hashlib.sha256(q.read_bytes()).digest() == hashlib.sha256(r.read_bytes()).digest():
                same += 1
            else:
                diff += 1; print("  다름", rel, q.stat().st_size, r.stat().st_size)
    print(f"같음 {same}, 다름 {diff}, 기준에 없음 {missing}")
