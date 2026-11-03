"""Steam/EGS 판 Image/dt/*.hed + *.pkg 에서 파일 꺼내기 (읽기 전용).

형식 출처: OpenKH (Apache-2.0) OpenKh.Egs/{Hed,EgsHdAsset,EgsEncryption}.cs 를 Python 으로 옮김.
  hed  = 0x20 바이트 항목: MD5(파일 이름 UTF-8, 16B) + offset u64 + dataLength i32 + actualLength i32
  pkg[offset] = seed 0x10 (= 헤더: 압축 해제 길이, 리마스터 자산 수, 압축 길이(-2 평문/-1 무압축), 날짜)
                + 리마스터 항목 0x30 x 수 (이름 0x20, offset, 원본 offset, 해제 길이, 압축 길이)
                + 원본 데이터 + 리마스터 데이터 (각각 0x10 정렬). 앞 0x100 바이트만 seed 로 만든 키로 XOR.
                압축은 zlib (앞 2바이트 머리 건너뛰고 raw deflate).
사용: python pkgextract.py <게임 폴더> <출력 폴더> <이름 목록 파일 또는 이름...>
     이름 = data/kh1 기준 상대 경로 (예: exchange/UK_item_shop_msg.bin). 리마스터 자산은 원본 이름 하나로 함께 나온다
     (출력/remastered/<원본 이름>/<자산 이름>, OpenKH 추출과 같은 배치).
"""
import glob, hashlib, os, struct, sys, zlib

MASTER = bytes.fromhex(
    "7E8897550B06F108EBBB141CD87AEC4134B2A346EF6BFEE1CF53A50512D28E52"
    "4A80E981B0F0B49CFF0F1513DA734E77BED730E5F65A113767BC836F2776D0CD"
    "690D2E514290B8B64CADCE5B1A1FF5AF01F85E3A6E688BE89FC9D9269229C833"
    "983254D4442566AC5F9921E48F1DC2D5A462F90261DE59E7079AFA2F953F86D3"
    "78A775EDD62D6487BDC7C1AAF28C17CB318AC3CC04EE6AAB5C2270CA9E716D85"
    "455DB9A9A61047FB827D847BC6E238FC2B0E209DC5F339A8A06558437CE33618"
    "724979AED17440C4914F2463BFBA239650B357DF1E03487F354D3EE6A1DD093C"
    "3D3B568D932A9B4B0C28B1E0608919DB2CF76CB51B94C0DCEAB70AF416FDA200")
SCRAMBLE = bytes([1, 0, 0, 0, 2, 0, 0, 0, 4, 0, 0, 0, 8, 0, 0, 0, 0x10, 0, 0, 0, 0x20, 0, 0, 0,
                  0x40, 0, 0, 0, 0x80, 0, 0, 0, 0x1B, 0, 0, 0, 0x36, 0, 0, 0])
PASS = 10


def gen_key(seed):
    k = bytearray(0xB0)
    for i, b in enumerate(seed):
        k[i] = b if b else i
    for i in range(PASS * 4):
        f = k[0x0C + i * 4:0x10 + i * 4]
        if i % 4 == 0:
            f = bytes([MASTER[f[1]] ^ SCRAMBLE[i], MASTER[f[2]] ^ SCRAMBLE[i + 1],
                       MASTER[f[3]] ^ SCRAMBLE[i + 2], MASTER[f[0]] ^ SCRAMBLE[i + 3]])
        for j in range(4):
            k[0x10 + i * 4 + j] = k[i * 4 + j] ^ f[j]
    return bytes(k)


def decrypt(key, data):
    d = bytearray(data)
    for idx in range(0, min(len(d), 0x100), 0x10):
        n = min(len(d) - idx, 0x10)
        for i in range(PASS, -1, -1):
            for j in range(n):
                d[idx + j] ^= key[0x10 * i + j]
    return bytes(d)


def unpack(raw, key, comp, size):
    if comp > -2:
        raw = decrypt(key, raw)
    return zlib.decompressobj(-15).decompress(raw[2:]) if comp > -1 else raw[:size]


def md5name(name):
    return hashlib.md5(name.encode("utf-8")).digest()


class Pkgs:
    def __init__(self, game, pattern=("Image/dt/kh1_*.hed",)):
        self.idx = {}
        for pat in pattern:
            for hed in sorted(glob.glob(os.path.join(game, pat))):
                b = open(hed, "rb").read()
                for o in range(0, len(b) - 0x1F, 0x20):
                    h = b[o:o + 16]
                    off, dlen, alen = struct.unpack_from("<qii", b, o + 16)
                    self.idx[h] = (hed[:-4] + ".pkg", off, dlen, alen)

    def has(self, name):
        return md5name(name) in self.idx

    def read(self, name):
        """-> (원본 bytes, {리마스터 이름: bytes})"""
        pkg, off, dlen, alen = self.idx[md5name(name)]
        with open(pkg, "rb") as fp:
            fp.seek(off)
            blob = fp.read(dlen)
        seed = blob[:0x10]
        size, count, comp, _ = struct.unpack("<iiii", seed)
        key = gen_key(seed)
        p = 0x10
        ents = []
        for _ in range(count):
            nm = blob[p:p + 0x20].split(b"\0")[0].decode("ascii")
            r_off, _, r_size, r_comp = struct.unpack_from("<iiii", blob, p + 0x20)
            ents.append((nm, r_size, r_comp))
            p += 0x30
        n = comp if comp >= 0 else size
        orig = unpack(blob[p:p + n], key, comp, size)
        p += n
        rem = {}
        for nm, r_size, r_comp in ents:
            n = r_comp if r_comp >= 0 else r_size
            n += -n % 16
            p += -(off + p) % 16          # 정렬은 pkg 파일 안 절대 위치 기준 (AlignPosition)
            # 무압축 리마스터 자산은 OpenKH 처럼 16바이트 패딩까지 그대로 둔다 (추출 결과를 OpenKH 와 같게)
            rem[nm] = unpack(blob[p:p + n], key, r_comp, n)
            p += n
        return orig, rem


def extract(pk, name, out):
    orig, rem = pk.read(name)
    dst = os.path.join(out, name)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    open(dst, "wb").write(orig)
    for nm, data in rem.items():
        d = os.path.join(out, "remastered", name, nm)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        open(d, "wb").write(data)
    return len(rem)


HERE = os.path.dirname(os.path.abspath(__file__))
SETS = (("Image/dt/kh1_*.hed", "needed_kh1.txt", ("data", "kh1")),
        ("Image/SettingMenu.hed", "needed_settingmenu.txt", ("data", "settingmenu")))


def extract_all(game, root, log=print):
    """빌드에 필요한 원본만 root/data/kh1, root/data/settingmenu 로 꺼낸다. 돌려줌: 꺼낸 수"""
    total = 0
    for pat, lst, sub in SETS:
        names = [l.strip() for l in open(os.path.join(HERE, lst), encoding="utf-8") if l.strip()]
        pk = Pkgs(game, (pat,))
        miss = [n for n in names if not pk.has(n)]
        if miss:
            raise FileNotFoundError(f"게임 파일에서 찾지 못함 ({len(miss)}개): {miss[:5]}")
        out = os.path.join(root, *sub)
        for i, n in enumerate(names):
            extract(pk, n, out)
            if log and (i + 1) % 50 == 0:
                log(f"  원본 꺼내는 중 {i + 1}/{len(names)}")
        total += len(names)
    return total


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2:          # <게임 폴더> <작업 루트>: 필요한 원본 전부
        print("꺼냄", extract_all(a[0], a[1]))
    else:                    # <게임 폴더> <출력 폴더> <이름...|목록 파일>
        game, out, *names = a
        if len(names) == 1 and os.path.isfile(names[0]):
            names = [l.strip() for l in open(names[0], encoding="utf-8") if l.strip()]
        pk = Pkgs(game)
        miss = [n for n in names if not pk.has(n)]
        for n in names:
            if n not in miss:
                extract(pk, n, out)
        print(f"꺼냄 {len(names) - len(miss)}, 없음 {len(miss)}", *miss[:10])
