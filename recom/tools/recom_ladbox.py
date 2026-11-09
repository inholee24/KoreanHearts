"""그림 글자 작업(imgtext.json)에 스프라이트 사각형 "box" 를 채운다 (개발용, 설치기 빌드에는 안 쓴다).

배경 (게임 확인 2026-11-09): 게임은 .imz 그림을 통째로 그리지 않고, 같은 이름 .lad (형제 폴더 *.SPR) 의
SEQD 표에 있는 사각형만 잘라 그린다. 사각형 밖으로 나간 새 글자 픽셀은 잘리고, 여러 사각형에 걸친 글자는
조각마다 다른 위치에 그려져 끊어진다 (일시 정지 제목).
LAYD/SEQD (UK_pause.lad 바이트로 확인): "SEQD" 위치 i 에서 u32 개수 @i+8, u32 표 오프셋(i 기준) @i+0xC,
  레코드 0x2C 바이트: u32 ?, i32 x0, y0, x1, y1 (x1/y1 미포함), 8 바이트, 색 4개.
그림이 여러 장인 .imz 는 레코드의 텍스처 번호를 아직 모르므로 첫 그림만 다룬다.

사용 (RECOMKO_DATA 필요):
  python -I -X utf8 recom_ladbox.py scan     작업마다 글자 영역 가운데를 품는 가장 작은 사각형과 지금 box 를 보여 준다
  python -I -X utf8 recom_ladbox.py apply    box 가 없는 작업에 채워 넣는다 (lines 가 있는 작업만)
"""
import glob, hashlib, json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import recom_imz as I, recom_paths as P
import recom_imgtext as T


def sprites(path):
    b = open(path, "rb").read()
    i = b.find(b"SEQD")
    if i < 0:
        return []
    n, off = struct.unpack_from("<II", b, i + 8)
    return [struct.unpack_from("<iiii", b, i + off + k * 0x2C + 4) for k in range(n)]


def lad_of(imz):
    stem = os.path.basename(imz)[:-4]
    hits = glob.glob(os.path.join(os.path.dirname(os.path.dirname(imz)), "*", stem + ".lad"))
    return hits[0] if hits else None


def main(a):
    spec = T.read_spec()
    changed = 0
    for imz in T.all_images():
        raw, ims = I.load(imz)
        k = hashlib.sha1(ims[0][2].tobytes()).hexdigest()[:10]
        if k not in spec:
            continue
        lad = lad_of(imz)
        sp = sprites(lad) if lad else []
        for j, job in enumerate(spec[k]["jobs"]):
            if not job.get("lines"):
                continue
            x0, y0, x1, y1 = job["r"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            inn = [s for s in sp if s[0] <= cx < s[2] and s[1] <= cy < s[3]]
            own = min(inn, key=lambda s: (s[2] - s[0]) * (s[3] - s[1])) if inn else None
            print(f"{spec[k]['name']:16} job{j:<2} r={job['r']} 사각형={own} box={job.get('box')}")
            if a[0] == "apply" and own and "box" not in job:
                job["box"] = list(own)
                changed += 1
    if a[0] == "apply":
        nl = "\r\n" if b"\r\n" in open(T.SPEC, "rb").read() else "\n"     # 원래 줄바꿈 유지
        json.dump(spec, open(T.SPEC, "w", encoding="utf-8", newline=nl), ensure_ascii=False, indent=1)
        print("box 채움", changed)


if __name__ == "__main__":
    main(sys.argv[1:] or ["scan"])
