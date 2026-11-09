"""mod\\kh1 의 메시지 파일(.binl/.evdl/.ev)에서 바이트 열을 정확히 치환한다.

사용:
    python -I tools/patch_binl_seq.py <glob> <old_hex> <new_hex> [<old_hex> <new_hex> ...]
                                      [--from-data] [--same-length] [--apply]

- <glob>은 kh1 기준 상대 경로 패턴 (예: "remastered/tw*.ard/*_*.binl").
- --apply 없이 실행하면 건수만 보고하고 쓰지 않는다 (dry run).
- --from-data: data\\kh1 에서 glob 하고, 치환 대상이 있는 파일을 원본에서 읽어
  mod\\kh1 의 같은 경로에 쓴다. mod 에 새로 만든 파일은 D:\\Projects\\openkh_backups\\created_by_patch.txt
  에 덧붙여 기록한다 (되돌릴 때 이 목록의 파일만 지운다).
- --same-length: 치환 쌍의 길이가 다르면 거부한다. .evdl 처럼 메시지 블록 뒤에
  다른 구역의 오프셋이 있는 파일에는 반드시 쓴다.
- 치환 쌍마다 발견 건수를 보고한다. 원본 data\\kh1 은 건드리지 않는다.
- .binl 의 길이 증가/감소는 허용된다 (work-history 17차, 21차).
  단, 치환 대상이 제어 코드 인자에 걸치지 않도록 <old_hex>에 앞뒤 문맥을 포함할 것.
- 기존 mod 파일의 되돌리기는 백업 폴더(D:\\Projects\\openkh_backups\\...)에서 복사한다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "kh1"
MOD = ROOT / "mod" / "kh1"
CREATED_LOG = ROOT.parent / "openkh_backups" / "created_by_patch.txt"


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]
    apply, from_data, same_len = "--apply" in flags, "--from-data" in flags, "--same-length" in flags
    if len(args) < 3 or len(args) % 2 == 0:
        print(__doc__)
        return 2
    pattern, pairs = args[0], args[1:]
    pairs = [(bytes.fromhex(pairs[i]), bytes.fromhex(pairs[i + 1])) for i in range(0, len(pairs), 2)]
    if same_len and any(len(o) != len(n) for o, n in pairs):
        print("--same-length: 길이가 다른 치환 쌍이 있다")
        return 2

    src_root = DATA if from_data else MOD
    files = sorted(src_root.glob(pattern))
    totals = [0] * len(pairs)
    changed, created = 0, []
    for f in files:
        rel = f.relative_to(src_root)
        dst = MOD / rel
        # mod 에 이미 있으면 그것을 기준으로 이어서 고친다
        data = dst.read_bytes() if dst.exists() else f.read_bytes()
        new = data
        for k, (old, rep) in enumerate(pairs):
            totals[k] += new.count(old)
            new = new.replace(old, rep)
        if new == data:
            continue
        changed += 1
        if apply:
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                created.append(str(rel))
            dst.write_bytes(new)
        print(f"{rel}  {len(data)} -> {len(new)}")
    if apply and created:
        with CREATED_LOG.open("a", encoding="utf-8") as log:
            log.writelines(c + "\n" for c in created)
    print(f"files matched: {len(files)}, changed: {changed}, created: {len(created)}, apply: {apply}")
    for (old, rep), n in zip(pairs, totals):
        print(f"  {old.hex(' ')} -> {rep.hex(' ')} : {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
