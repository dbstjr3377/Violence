"""
가면 21종 (복셀). 좌표: 0..16 이 머리를 감싸는 영역, 얼굴(정면)은 북쪽(-Z), 위는 +Y.

만드는 방식
 - 둥근 덩어리는 가로 조각을 쌓은 타원체(blob)로, 머리·주둥이·볼을 따로 빚어 붙인다.
 - 색은 동물마다 3~4톤 팔레트: 바탕, 어두운 그늘(아래·뒤), 밝은 부분(주둥이·볼·배), 포인트(코·입·뿔).
   위→아래로 살짝 어두워지는 그라데이션(shaded)과 털 결 노이즈(fur)를 겹친다.
 - 눈은 앞을 보는 동물(고양이과·개과·곰·원숭이·쥐)은 정면 눈, 초식동물(말·기린·낙타·얼룩말·토끼)은 옆 눈.
   눈 = 흰자 없는 홍채 + 동공(둥근/세로/가로) + 작은 하이라이트 + 눈꺼풀 선.
"""
import math
import random

from voxel import Material, Model, hnoise, rbox, rot

BLACK = (16, 13, 15)
WHITE = (246, 244, 236)
MOUTH = (96, 22, 34)
TONGUE = (214, 92, 112)
GLINT = (255, 255, 250)


def mat(rgb, noise=0.06):
    return Material(rgb, noise=noise)


def tone(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def dark(c, k=0.7):
    return tone(c, k)


def light(c, k=1.18):
    return tone(c, k)


def mixc(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ───────────────────────── 칠하기 (painter) ─────────────────────────

def fur(base, seed=0, amt=0.12, streak=1.4, y0=-2.0, y1=18.0, lo=0.86, hi=1.06):
    """털 결(세로로 흐르는 노이즈) + 위→아래 그라데이션"""
    def p(face, pt, fu, fv):
        n = hnoise(math.floor(pt[0] * streak * 2 + pt[2] * streak * 2), math.floor(pt[1] * streak * 0.6), 0, seed)
        n2 = hnoise(math.floor(pt[0] * 5), math.floor(pt[1] * 5), math.floor(pt[2] * 5), seed + 9)
        t = max(0.0, min(1.0, (pt[1] - y0) / (y1 - y0)))
        k = (lo + (hi - lo) * t) * (1 + (n - 0.5) * amt * 2 + (n2 - 0.5) * 0.05)
        return tone(base, k)
    return p


def skin(base, seed=0, amt=0.05, y0=-2.0, y1=18.0, lo=0.88, hi=1.05):
    """맨살·비늘처럼 결 없는 고른 질감 + 그라데이션"""
    def p(face, pt, fu, fv):
        n = hnoise(math.floor(pt[0] * 4), math.floor(pt[1] * 4), math.floor(pt[2] * 4), seed)
        t = max(0.0, min(1.0, (pt[1] - y0) / (y1 - y0)))
        return tone(base, (lo + (hi - lo) * t) * (1 + (n - 0.5) * amt * 2))
    return p


def chain(*ps):
    def p(face, pt, fu, fv):
        for q in ps:
            if q is None:
                continue
            c = q(face, pt, fu, fv)
            if c is not None:
                return c
        return None
    return p


def where(cond, painter):
    """cond(pt, face) 가 참인 곳만 painter 로"""
    def p(face, pt, fu, fv):
        return painter(face, pt, fu, fv) if cond(pt, face) else None
    return p


def patches(color, seed, cell=3.2, border=0.55):
    """기린 무늬: 셀(보로노이) 안쪽은 무늬색, 셀 경계는 바탕색이 드러남"""
    def p(face, pt, fu, fv):
        x, y, z = pt[0] / cell, pt[1] / cell, pt[2] / cell
        best = [9.0, 9.0]
        for i in range(-1, 2):
            for j in range(-1, 2):
                for k in range(-1, 2):
                    cx, cy, cz = math.floor(x) + i, math.floor(y) + j, math.floor(z) + k
                    px = cx + hnoise(cx, cy, cz, seed)
                    py = cy + hnoise(cx, cy, cz, seed + 1)
                    pz = cz + hnoise(cx, cy, cz, seed + 2)
                    d = math.sqrt((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2)
                    if d < best[0]:
                        best = [d, best[0]]
                    elif d < best[1]:
                        best[1] = d
        return color if best[1] - best[0] > border / cell * 2.2 else None
    return p


def stripes(color, period=3.0, width=1.1, axis=(0.0, 1.0, 0.0), wobble=0.9, seed=0):
    """줄무늬 (axis 방향으로 반복, 물결)"""
    def p(face, pt, fu, fv):
        v = pt[0] * axis[0] + pt[1] * axis[1] + pt[2] * axis[2]
        v += math.sin(pt[0] * 0.8 + pt[2] * 0.6 + seed) * wobble + math.sin(pt[1] * 1.3 + seed * 2) * wobble * 0.4
        return color if v % period < width else None
    return p


# ───────────────────────── 조각 도구 ─────────────────────────

class Sculpt:
    def __init__(self, name, seed):
        self.m = Model(name, seed=seed, density=4)
        self.rng = random.Random(seed)

    def box(self, frm, to, rgb, painter=None, rot_=None, noise=0.04):
        self.m.box(list(frm), list(to), mat(rgb, noise), painter=painter, rot=rot_)

    def rbox(self, frm, to, r, rgb, painter=None, noise=0.04, rot_=None):
        rbox(self.m, list(frm), list(to), r, mat(rgb, noise), painter=painter, rot_=rot_)

    def head(self, base, painter=None, r=2.6, frm=(0, 0, 0), to=(16, 16, 16)):
        self.rbox(frm, to, r, base, painter)

    def blob(self, c, rad, rgb, painter=None, n=5, round_=0.7, axis="y"):
        """타원체 (axis 방향 조각 n개)"""
        cx, cy, cz = c
        rx, ry, rz = rad
        for k in range(n):
            t0, t1 = -1 + 2 * k / n, -1 + 2 * (k + 1) / n
            tm = (t0 + t1) / 2
            s = math.sqrt(max(0.0, 1 - tm * tm)) * 1.05
            if axis == "y":
                a, b = (cx - rx * s, cy + ry * t0, cz - rz * s), (cx + rx * s, cy + ry * t1, cz + rz * s)
            elif axis == "z":
                a, b = (cx - rx * s, cy - ry * s, cz + rz * t0), (cx + rx * s, cy + ry * s, cz + rz * t1)
            else:
                a, b = (cx + rx * t0, cy - ry * s, cz - rz * s), (cx + rx * t1, cy + ry * s, cz + rz * s)
            rr = min(round_, (b[0] - a[0]) * 0.3, (b[1] - a[1]) * 0.3, (b[2] - a[2]) * 0.3)
            self.rbox(a, b, rr, rgb, painter)

    def eye(self, cx, cy, z, w, h, iris=BLACK, pupil=None, slit="round", lid=None, glint=True, rim=None):
        """정면 눈 (앞쪽 -z 를 봄). w/h = 반지름. slit: round / vertical / horizontal"""
        rows = 4
        if rim:
            for k in range(rows):
                t = (k + 0.5) / rows * 2 - 1
                half = (w + 0.35) * math.sqrt(max(0.0, 1 - t * t)) * 1.08
                y0 = cy - h - 0.3 + (2 * h + 0.6) * k / rows
                self.box((cx - half, y0, z + 0.02), (cx + half, y0 + (2 * h + 0.6) / rows, z + 0.3), rim, noise=0.02)
        for k in range(rows):
            t = (k + 0.5) / rows * 2 - 1
            half = w * math.sqrt(max(0.0, 1 - t * t)) * 1.08
            y0 = cy - h + 2 * h * k / rows
            self.box((cx - half, y0, z - 0.06), (cx + half, y0 + 2 * h / rows, z + 0.3), iris, noise=0.02)
        if pupil:
            if slit == "vertical":
                pw, ph = max(0.3, w * 0.22), h * 0.95
            elif slit == "horizontal":
                pw, ph = w * 0.7, max(0.3, h * 0.25)
            else:
                pw, ph = w * 0.5, h * 0.55
            self.box((cx - pw, cy - ph, z - 0.12), (cx + pw, cy + ph, z + 0.1), pupil, noise=0.0)
        if glint:
            g = max(0.28, min(w, h) * 0.3)
            gx, gy = cx + w * 0.3, cy + h * 0.3
            self.box((gx - g / 2, gy - g / 2, z - 0.18), (gx + g / 2, gy + g / 2, z - 0.05), GLINT, noise=0.0)
        if lid:
            self.box((cx - w - 0.3, cy + h - 0.1, z - 0.45), (cx + w + 0.3, cy + h + 0.7, z + 0.35), lid, noise=0.04)

    def side_eyes(self, cz, cy, rz, ry, x_left=0.0, x_right=16.0, iris=(50, 34, 26), pupil=BLACK, lid=None, rim=None):
        """옆을 보는 눈 (초식동물). 양쪽 면에 같은 눈"""
        for x, sgn in ((x_left, -1), (x_right, 1)):
            def slab(dx0, dx1, y0, y1, z0, z1, c):
                a, b = (x + sgn * dx0, y0, z0), (x + sgn * dx1, y1, z1)
                self.box((min(a[0], b[0]), y0, z0), (max(a[0], b[0]), y1, z1), c, noise=0.02)
            if rim:
                slab(-0.05, 0.2, cy - ry - 0.35, cy + ry + 0.35, cz - rz - 0.35, cz + rz + 0.35, rim)
            rows = 4
            for k in range(rows):
                t = (k + 0.5) / rows * 2 - 1
                half = rz * math.sqrt(max(0.0, 1 - t * t)) * 1.08
                y0 = cy - ry + 2 * ry * k / rows
                slab(0.0, 0.3, y0, y0 + 2 * ry / rows, cz - half, cz + half, iris)
            slab(0.25, 0.38, cy - ry * 0.55, cy + ry * 0.55, cz - rz * 0.5, cz + rz * 0.5, pupil)
            g = max(0.28, min(rz, ry) * 0.3)
            slab(0.33, 0.45, cy + ry * 0.25, cy + ry * 0.25 + g, cz - rz * 0.4, cz - rz * 0.4 + g, GLINT)
            if lid:
                slab(-0.05, 0.6, cy + ry - 0.1, cy + ry + 0.7, cz - rz - 0.3, cz + rz + 0.3, lid)

    def teeth(self, x0, x1, y_top, z, n, h, rgb=WHITE, down=True, fang_every=0, w_ratio=0.78, depth=0.6):
        step = (x1 - x0) / n
        for i in range(n):
            x = x0 + step * i + step * (1 - w_ratio) / 2
            hh = h * (1.8 if fang_every and (i == 0 or i == n - 1) else 1.0)
            y0, y1 = (y_top - hh, y_top) if down else (y_top, y_top + hh)
            self.box((x, y0, z), (x + step * w_ratio, y1, z + depth), rgb, noise=0.02)

    def tufts(self, region, n, size, rgb, painter=None, jitter=0.08):
        (x0, y0, z0), (x1, y1, z1) = region
        for _ in range(n):
            w = self.rng.uniform(*size)
            h = self.rng.uniform(*size) * 1.2
            x = self.rng.uniform(x0, x1 - w)
            y = self.rng.uniform(y0, y1 - h)
            z = self.rng.uniform(z0, z1 - w)
            k = 1 + self.rng.uniform(-jitter, jitter)
            self.m.box([x, y, z], [x + w, y + h, z + w], mat(tone(rgb, k), 0.06), painter=painter)

    def ear(self, x0, x1, y0, y1, z0, z1, outer, inner, tip=None, taper=3, inner_inset=0.7, tilt=0.0, painter=None):
        """뾰족한 귀: 위로 갈수록 좁아지는 조각 + 앞면 안쪽 색 + (선택) 끝 색"""
        h = (y1 - y0) / taper
        cxm = (x0 + x1) / 2
        for i in range(taper):
            s = 1 - i / taper * 0.62
            hw = (x1 - x0) / 2 * s
            off = tilt * i
            ya, yb = y0 + h * i, y0 + h * (i + 1)
            c = tip if (tip and i == taper - 1) else outer
            self.box((cxm - hw + off, ya, z0 + i * 0.15), (cxm + hw + off, yb, z1 - i * 0.15), c, painter=None if c is tip else painter)
            if inner and i < taper - 1:
                self.box((cxm - hw + inner_inset + off, ya + 0.3, z0 - 0.08 + i * 0.15), (cxm + hw - inner_inset + off, yb, z0 + 0.25 + i * 0.15), inner)

    def done(self):
        return self.m


# ───────────────────────── 1. 리처드 (닭) ─────────────────────────

def richard():
    """흰 수탉: 깃털 비늘이 겹친 머리, 붉은 맨살 얼굴, 톱니 볏, 두 갈래 육수, 주황 부리"""
    s = Sculpt("richard", 301)
    white, cream, shade_w = (244, 241, 232), (236, 226, 200), (214, 210, 204)
    red, comb = (214, 40, 46), (226, 30, 42)
    s.head(white, fur(white, 1, 0.05, lo=0.9, hi=1.03))
    # 목털: 머리 아래·뒤로 늘어진 가는 깃털 (뒤로 갈수록 크림색) — 실루엣이 둥글게 흘러내림
    for i in range(9):
        z0 = 2.0 + i * 1.6
        col = mixc(white, cream, i / 8)
        for x0 in (-0.5, 3.6, 7.7, 11.8):
            dy = (hash((i, x0)) % 7) * 0.25
            s.box((x0, -2.4 + dy, z0), (x0 + 4.2, 1.2, z0 + 1.9), col, fur(col, 2 + i, 0.05))
    # 붉은 얼굴: 눈 둘레 + 뺨 (옆면 앞쪽)
    for x0, x1 in ((-0.4, 3.6), (12.4, 16.4)):
        s.rbox((x0, 5.2, -0.6), (x1, 12.6, 7.8), 1.4, red, skin(red, 3, 0.06))
    s.side_eyes(4.2, 10.2, 1.0, 0.95, x_left=-0.4, x_right=16.4, iris=(236, 132, 30), pupil=BLACK, rim=(170, 30, 36))
    # 흰 귓불
    for x0, x1 in ((-0.6, -0.15), (16.15, 16.6)):
        s.rbox((x0, 5.6, 5.4), (x1, 7.8, 7.6), 0.25, WHITE)
    # 볏: 톱니 다섯 개 (앞이 낮고 가운데가 높음)
    s.rbox((6.6, 14.8, -1.2), (9.4, 17.4, 14.0), 0.9, comb, skin(comb, 4, 0.05))
    for z0, h in ((-1.4, 3.4), (1.6, 5.2), (4.8, 6.2), (8.0, 5.6), (11.2, 4.2)):
        s.rbox((6.8, 16.6, z0), (9.2, 16.6 + h, z0 + 2.6), 0.9, comb, skin(comb, 5, 0.05, y0=15, y1=23, lo=0.85, hi=1.1))
    # 부리: 위턱(굽음) + 아래턱 + 콧구멍
    beak, beak_d = (246, 176, 40), (214, 130, 26)
    s.rbox((5.6, 7.6, -4.2), (10.4, 10.4, 0.6), 0.7, beak, skin(beak, 6, 0.04, y0=7, y1=11))
    s.rbox((6.4, 7.4, -6.0), (9.6, 9.8, -3.8), 0.6, beak)
    s.box((7.2, 7.0, -6.8), (8.8, 8.6, -5.6), beak_d)
    s.box((6.6, 9.4, -2.6), (7.3, 10.0, -1.9), (110, 60, 16))
    s.box((8.7, 9.4, -2.6), (9.4, 10.0, -1.9), (110, 60, 16))
    s.rbox((6.2, 6.0, -3.4), (9.8, 7.4, 0.4), 0.5, beak_d)
    # 육수 (두 갈래, 아래로 둥글게)
    for x0 in (6.0, 8.3):
        s.blob((x0 + 0.85, 3.4, -1.0), (0.95, 2.6, 1.1), (204, 30, 40), skin((204, 30, 40), 7, 0.05), n=4, round_=0.5)
    return s.done()


# ───────────────────────── 2. 돈 후안 (말) ─────────────────────────

def don_juan():
    """밤색 말: 긴 얼굴, 흰 콧등 줄, 짙은 주둥이, 검은 갈기, 쫑긋한 귀"""
    s = Sculpt("don_juan", 302)
    coat = (150, 86, 46)
    muzzle = (78, 56, 46)
    blaze = (240, 234, 222)
    mane = (30, 22, 20)
    is_blaze = lambda p, f: f in ("north", "up") and abs(p[0] - 8) < 1.6 - max(0.0, -p[2]) * 0.03
    s.head(coat, chain(where(is_blaze, lambda f, p, u, v: blaze), fur(coat, 2, 0.1)))
    # 긴 얼굴: 콧등이 앞쪽으로 길게 (위가 넓고 아래로 좁아짐)
    s.rbox((3.2, 2.0, -7.0), (12.8, 11.6, 1.0), 2.0, coat, chain(where(is_blaze, lambda f, p, u, v: blaze), fur(coat, 3, 0.1)))
    s.blob((8.0, 4.4, -8.0), (4.6, 4.2, 3.2), muzzle, skin(muzzle, 4, 0.06), n=5, axis="z")
    s.rbox((5.8, 7.6, -10.2), (10.2, 9.2, -5.0), 0.6, blaze)                 # 콧등 흰 줄 끝
    for x in (4.4, 9.8):                                                       # 큰 콧구멍
        s.rbox((x, 4.2, -11.45), (x + 1.8, 6.6, -10.9), 0.4, (24, 16, 14))
    s.box((4.8, 1.6, -11.35), (11.2, 2.1, -9.0), (40, 28, 24))               # 입 선
    s.side_eyes(2.6, 10.4, 1.3, 1.0, x_left=-0.05, x_right=16.05, iris=(46, 30, 22), lid=dark(coat, 0.7))
    # 귀: 뾰족, 안쪽 짙은 색
    for x0 in (2.0, 10.8):
        s.ear(x0, x0 + 3.2, 15.0, 21.6, 6.0, 8.6, coat, (90, 52, 34), taper=3, painter=fur(coat, 5, 0.08))
    # 갈기: 정수리에서 앞머리로 흘러내림 + 목 뒤로 길게
    s.tufts(((5.6, 14.2, 7.0), (10.4, 19.4, 17.4)), 26, (1.2, 2.4), mane, jitter=0.18)
    s.tufts(((5.8, 2.0, 15.0), (10.2, 16.0, 18.4)), 16, (1.2, 2.4), mane, jitter=0.18)
    s.tufts(((4.6, 12.0, -2.2), (11.4, 16.6, 2.0)), 10, (1.2, 2.2), mane, jitter=0.18)       # 앞머리
    return s.done()


# ───────────────────────── 3. 그레이엄 (토끼) ─────────────────────────

def graham():
    """갈색 토끼: 크림색 주둥이·턱, 분홍 코, 앞니, 길게 선 귀(분홍 안쪽)"""
    s = Sculpt("graham", 303)
    coat = (168, 122, 82)
    cream = (240, 226, 200)
    pink = (238, 150, 160)
    s.head(coat, fur(coat, 3, 0.1))
    s.blob((4.6, 5.0, 0.2), (3.0, 3.0, 2.2), cream, fur(cream, 4, 0.05), n=4)          # 볼 (부풀어 오름)
    s.blob((11.4, 5.0, 0.2), (3.0, 3.0, 2.2), cream, fur(cream, 4, 0.05), n=4)
    s.rbox((5.6, 1.0, -2.0), (10.4, 4.6, 1.0), 0.8, cream)                              # 턱
    s.rbox((6.6, 6.4, -2.6), (9.4, 8.2, -1.0), 0.6, pink)                               # 코
    s.box((7.85, 4.4, -2.4), (8.15, 6.6, -1.8), dark(coat, 0.5))                        # 인중
    s.box((6.7, 1.8, -2.5), (7.9, 4.6, -1.7), WHITE)                                    # 앞니
    s.box((8.1, 1.8, -2.5), (9.3, 4.6, -1.7), WHITE)
    for cx in (3.6, 12.4):
        s.eye(cx, 10.4, -0.05, 1.6, 1.7, iris=(40, 24, 16), pupil=BLACK, lid=dark(coat, 0.75))
    for x, y in ((2.4, 5.6), (3.0, 4.4), (13.0, 5.6), (12.4, 4.4)):                    # 수염
        s.box((x - 1.6, y, -1.0), (x + 0.4, y + 0.25, -0.8), (250, 248, 240))
    # 긴 귀: 세 마디로 살짝 바깥으로 기울어짐
    for x0, sgn in ((2.0, -1), (10.4, 1)):
        for i in range(3):
            ya = 15.0 + i * 5.0
            ox = sgn * i * 0.7
            s.rbox((x0 + ox, ya, 6.0), (x0 + 3.6 + ox, ya + 5.4, 8.6), 1.0, coat, fur(coat, 6, 0.08))
            s.box((x0 + 0.8 + ox, ya + 0.4, 5.85), (x0 + 2.8 + ox, ya + 5.0, 6.1), pink if i < 2 else light(pink, 1.06))
    return s.done()


# ───────────────────────── 4. 데니스 (늑대) ─────────────────────────

def dennis():
    """회색 늑대: 등은 짙은 회색, 볼·주둥이·턱은 흰 털, 으르렁거리는 입, 호박색 눈"""
    s = Sculpt("dennis", 304)
    gray = (120, 122, 130)
    saddle = (78, 78, 86)
    white = (226, 226, 230)
    top = lambda p, f: p[1] > 12.5 or p[2] > 10
    s.head(gray, chain(where(top, fur(saddle, 5, 0.18)), fur(gray, 6, 0.16)))
    s.blob((3.4, 5.4, 1.2), (3.6, 3.4, 2.6), white, fur(white, 7, 0.08), n=4)             # 흰 볼 털
    s.blob((12.6, 5.4, 1.2), (3.6, 3.4, 2.6), white, fur(white, 7, 0.08), n=4)
    # 주둥이 (위턱: 위는 회색, 아래는 흰색) + 코
    snout = lambda f, p, u, v: white if p[1] < 7.6 else None
    s.rbox((4.4, 6.0, -7.4), (11.6, 10.4, 1.0), 1.6, gray, chain(snout, fur(gray, 8, 0.12)))
    s.rbox((5.8, 8.6, -8.4), (10.2, 10.4, -6.4), 0.7, (26, 24, 28))
    s.box((6.4, 9.6, -8.5), (7.4, 10.2, -8.3), (60, 56, 62))
    # 벌린 입 + 이빨 + 아래턱
    s.box((5.0, 4.2, -6.8), (11.0, 6.1, 0.6), MOUTH)
    s.box((6.4, 4.3, -5.6), (9.6, 4.9, -1.0), TONGUE)
    s.teeth(5.0, 11.0, 6.0, -7.1, 6, 0.9, fang_every=1)
    s.rbox((5.4, 2.0, -5.8), (10.6, 4.3, 0.8), 0.8, white, fur(white, 9, 0.06))
    s.teeth(5.4, 10.6, 4.3, -6.0, 5, 0.7, down=False, fang_every=1)
    for cx in (4.4, 11.6):
        s.eye(cx, 11.0, -0.05, 1.4, 0.85, iris=(230, 168, 50), pupil=BLACK, lid=dark(gray, 0.62))
    for x0, x1 in ((3.0, 6.0), (10.0, 13.0)):                                               # 찌푸린 미간
        s.box((x0, 12.0, -0.5), (x1, 12.6, 0.2), dark(gray, 0.6))
    for x0 in (1.4, 10.6):
        s.ear(x0, x0 + 4.0, 15.0, 22.0, 5.2, 8.8, saddle, (200, 190, 186), tip=(40, 40, 46), taper=3, painter=fur(saddle, 10, 0.12))
    s.tufts(((-1.4, 1.0, 3.0), (1.0, 10.0, 13.0)), 12, (1.2, 2.2), white, jitter=0.06)
    s.tufts(((15.0, 1.0, 3.0), (17.4, 10.0, 13.0)), 12, (1.2, 2.2), white, jitter=0.06)
    s.tufts(((1.0, -1.2, 1.0), (15.0, 1.6, 14.0)), 14, (1.2, 2.2), white, jitter=0.05)
    return s.done()


# ───────────────────────── 5. 조지 (기린) ─────────────────────────

def george():
    """기린: 크림 바탕에 밤색 그물 무늬, 밝은 주둥이, 끝이 검은 뿔(오시콘), 옆 귀"""
    s = Sculpt("george", 305)
    base = (238, 206, 140)
    patch = (170, 98, 44)
    pt = patches(patch, 5, 3.0, 0.55)
    s.head(base, chain(pt, fur(base, 7, 0.05)))
    s.rbox((3.4, 0.4, -8.0), (12.6, 9.4, 1.0), 2.0, base, chain(where(lambda p, f: p[2] > -4.5, pt), fur(base, 8, 0.05)))
    s.rbox((3.8, 0.0, -8.8), (12.2, 5.0, -3.0), 1.6, (226, 198, 160), skin((226, 198, 160), 9))
    for x in (4.8, 9.8):
        s.box((x, 4.4, -8.95), (x + 1.4, 6.0, -8.6), (40, 26, 18))
    s.box((5.0, 1.2, -8.85), (11.0, 1.6, -6.0), (120, 80, 50))
    s.side_eyes(3.4, 10.4, 1.3, 1.1, x_left=-0.05, x_right=16.05, iris=(40, 26, 18), lid=(150, 96, 50))
    for x in (-0.6, 16.2):                                                                # 긴 속눈썹
        s.box((x, 11.4, 2.0), (x + 0.4, 12.1, 4.8), (60, 36, 20))
    for x0 in (4.0, 10.2):
        s.rbox((x0, 15.0, 6.0), (x0 + 1.8, 21.6, 7.8), 0.6, base, fur(base, 11, 0.05))
        s.blob((x0 + 0.9, 22.0, 6.9), (1.4, 1.2, 1.4), (70, 44, 26), n=3, round_=0.5)
    for x0, x1 in ((-4.4, 0.4), (15.6, 20.4)):
        s.rbox((x0, 11.0, 6.4), (x1, 13.0, 9.0), 0.8, base)
        s.box((x0 + 0.6, 11.4, 6.25), (x1 - 0.6, 12.6, 6.5), (230, 170, 150))
    s.tufts(((7.0, 14.6, 9.0), (9.0, 17.2, 17.4)), 10, (0.8, 1.4), (150, 86, 40))      # 짧은 갈기
    return s.done()


# ───────────────────────── 6. 루퍼스 (코끼리) ─────────────────────────

def rufus():
    """회색 코끼리: 주름진 피부, 큰 귀(안쪽 분홍빛), 아래로 휘는 코, 상아"""
    s = Sculpt("rufus", 306)
    gray = (134, 136, 146)
    wrinkle = lambda f, p, u, v: tone(gray, 0.78) if f not in ("up", "down") and (p[1] * 1.3 + math.sin(p[0] * 0.8) * 0.5) % 2.0 < 0.3 else None
    s.head(gray, chain(wrinkle, skin(gray, 9, 0.06)))
    s.blob((8.0, 13.0, 1.0), (7.0, 3.2, 2.4), light(gray, 1.05), skin(light(gray, 1.05), 10), n=3)   # 볼록한 이마
    for cx in (3.8, 12.2):
        s.eye(cx, 10.0, -0.05, 1.1, 0.9, iris=(40, 30, 26), pupil=BLACK, lid=dark(gray, 0.72))
    for x0, x1 in ((-7.4, 0.4), (15.6, 23.4)):                                          # 귀
        s.rbox((x0, 0.0, 5.0), (x1, 15.8, 8.4), 2.2, gray, chain(wrinkle, skin(gray, 11)))
        s.rbox((x0 + 1.2, 1.4, 4.85), (x1 - 1.2, 14.4, 5.2), 1.0, (196, 150, 156))
    # 코: 마디마다 조금씩 가늘어지며 앞·아래로 휨, 주름 줄
    segs = [(5.0, 3.0, -2.6, 11.0, 9.6, 0.8), (5.4, -1.2, -3.8, 10.6, 4.4, -0.2), (5.8, -5.4, -5.0, 10.2, 0.2, -1.4),
            (6.1, -9.2, -6.4, 9.9, -4.0, -2.8), (6.3, -12.4, -8.2, 9.7, -8.0, -4.4)]
    for x0, y0, z0, x1, y1, z1 in segs:
        s.rbox((x0, y0, z0), (x1, y1, z1), 1.0, gray, chain(wrinkle, skin(gray, 12)))
    s.rbox((6.0, -14.0, -9.8), (10.0, -11.6, -7.0), 0.9, dark(gray, 0.86))
    s.box((6.8, -13.4, -9.95), (7.7, -12.4, -9.7), BLACK)
    s.box((8.3, -13.4, -9.95), (9.2, -12.4, -9.7), BLACK)
    ivory = (246, 238, 212)
    for x0, sgn in ((2.8, -1), (11.4, 1)):                                                # 상아: 아래로 갔다 앞·위로 휨
        s.rbox((x0, 0.6, -2.0), (x0 + 1.8, 3.6, 0.6), 0.5, ivory)
        s.rbox((x0 + 0.1 + sgn * 0.2, -2.6, -3.8), (x0 + 1.7 + sgn * 0.2, 1.0, -1.4), 0.5, ivory)
        s.rbox((x0 + 0.2 + sgn * 0.4, -4.8, -6.4), (x0 + 1.6 + sgn * 0.4, -2.0, -3.4), 0.5, ivory)
        s.box((x0 + 0.4 + sgn * 0.5, -5.0, -8.0), (x0 + 1.4 + sgn * 0.5, -3.6, -6.2), ivory)
    return s.done()


# ───────────────────────── 7. 라미 (낙타) ─────────────────────────

def rami():
    """낙타: 모래색, 정수리의 덥수룩한 짙은 털, 두툼한 눈꺼풀, 처진 갈라진 윗입술, 작은 귀"""
    s = Sculpt("rami", 307)
    sand = (212, 168, 108)
    hair = (140, 92, 52)
    s.head(sand, fur(sand, 11, 0.08))
    s.rbox((3.4, 0.4, -9.2), (12.6, 9.4, 1.0), 2.2, sand, fur(sand, 12, 0.07))
    s.rbox((3.6, -1.6, -8.8), (12.4, 1.4, -1.6), 1.0, (194, 148, 92))                    # 처진 아랫입술
    s.rbox((3.8, 0.8, -9.8), (7.9, 4.0, -7.0), 0.8, (200, 156, 98))                      # 갈라진 윗입술
    s.rbox((8.1, 0.8, -9.8), (12.2, 4.0, -7.0), 0.8, (200, 156, 98))
    s.box((4.6, 0.9, -9.4), (11.4, 1.3, -6.0), (110, 70, 40))
    for x in (4.8, 9.8):
        s.box((x, 5.6, -9.35), (x + 1.4, 6.1, -8.9), (70, 40, 20))                        # 가는 콧구멍
    s.side_eyes(3.6, 10.4, 1.3, 1.0, x_left=-0.05, x_right=16.05, iris=(36, 24, 16), lid=(186, 138, 84))
    for x in (-0.7, 16.3):
        s.box((x, 11.6, 1.8), (x + 0.4, 12.2, 5.2), (90, 56, 30))                          # 긴 속눈썹
    s.tufts(((-1.2, 12.0, -1.0), (17.2, 18.6, 14.0)), 40, (1.4, 2.6), hair, jitter=0.15)
    s.tufts(((2.0, 11.0, -1.6), (14.0, 14.6, 2.0)), 12, (1.2, 2.2), hair, jitter=0.15)       # 앞머리
    for x0 in (1.4, 12.4):
        s.ear(x0, x0 + 2.2, 15.4, 18.6, 6.4, 8.2, sand, (150, 100, 60), taper=2)
    return s.done()


# ───────────────────────── 8. 윌럼 (원숭이) ─────────────────────────

def willem():
    """침팬지: 짙은 갈색 털, 하트 모양 살색 얼굴, 튀어나온 눈썹뼈와 주둥이, 큰 귀"""
    s = Sculpt("willem", 308)
    furc = (78, 52, 36)
    face = (210, 166, 136)
    s.head(furc, fur(furc, 13, 0.2))
    s.rbox((2.4, 1.4, -1.2), (13.6, 11.6, 2.0), 2.4, face, skin(face, 14, 0.05))        # 얼굴판
    s.rbox((2.0, 10.4, -2.6), (14.0, 12.6, 0.6), 1.0, dark(face, 0.82), skin(dark(face, 0.82), 15))   # 눈썹뼈
    s.rbox((5.4, 11.4, -1.6), (10.6, 13.2, 1.0), 0.8, face)                                # 이마 가운데 (하트 윗부분)
    for cx in (5.2, 10.8):
        s.eye(cx, 8.8, -1.25, 1.3, 1.1, iris=(70, 40, 24), pupil=BLACK, rim=dark(face, 0.7))
    s.blob((8.0, 4.0, -2.0), (3.6, 2.6, 2.2), light(face, 1.04), skin(light(face, 1.04), 16), n=4)   # 주둥이
    s.box((6.8, 5.6, -4.05), (7.6, 6.3, -3.8), (80, 46, 34))
    s.box((8.4, 5.6, -4.05), (9.2, 6.3, -3.8), (80, 46, 34))
    s.box((5.2, 2.8, -3.95), (10.8, 3.3, -3.6), (130, 72, 64))                             # 입 선
    for x0, x1 in ((-3.6, 0.4), (15.6, 19.6)):
        s.blob(((x0 + x1) / 2, 9.0, 7.4), (2.0, 2.8, 1.4), face, skin(face, 17), n=4)
        s.box((x0 + 1.0, 7.6, 5.9), (x1 - 1.0, 10.4, 6.2), dark(face, 0.7))
    s.tufts(((0.4, 13.4, 0.0), (15.6, 17.4, 14.0)), 18, (1.2, 2.2), furc, jitter=0.18)
    s.tufts(((-1.0, 1.0, 2.0), (1.2, 12.0, 14.0)), 10, (1.2, 2.2), furc, jitter=0.18)
    s.tufts(((14.8, 1.0, 2.0), (17.0, 12.0, 14.0)), 10, (1.2, 2.2), furc, jitter=0.18)
    return s.done()


# ───────────────────────── 9. 피터 (유니콘) ─────────────────────────

def peter():
    """유니콘: 흰 몸(연보라 그늘), 파스텔 무지개 갈기, 금빛 나선 뿔, 푸른 눈"""
    s = Sculpt("peter", 309)
    wh = (248, 246, 252)
    shade_ = lambda f, p, u, v: tone((236, 230, 248), 1.0 + (hnoise(math.floor(p[0] * 4), math.floor(p[1] * 4), math.floor(p[2] * 4), 15) - 0.5) * 0.04) if p[1] < 6 or p[2] > 11 else None
    s.head(wh, chain(shade_, skin(wh, 15, 0.03)))
    s.rbox((3.4, 0.4, -6.8), (12.6, 10.2, 1.0), 2.0, wh, chain(shade_, skin(wh, 16, 0.03)))
    s.rbox((3.8, 0.0, -9.4), (12.2, 7.8, -4.6), 1.8, (240, 222, 232), skin((240, 222, 232), 17, 0.03))   # 분홍빛 주둥이
    for x in (4.8, 9.8):
        s.rbox((x, 4.4, -9.55), (x + 1.4, 6.2, -9.2), 0.3, (196, 150, 176))
    s.box((5.2, 1.4, -9.5), (10.8, 1.8, -7.0), (190, 150, 170))
    s.side_eyes(3.2, 10.4, 1.3, 1.1, x_left=-0.05, x_right=16.05, iris=(70, 150, 230), pupil=(20, 30, 70), lid=(200, 190, 220))
    for x in (-0.65, 16.25):
        s.box((x, 11.5, 2.0), (x + 0.4, 12.2, 4.6), (90, 80, 120))                         # 속눈썹
    # 금빛 나선 뿔 (앞으로 살짝 기울어짐)
    gold, gold_d = (246, 206, 92), (196, 146, 44)
    spiral = lambda f, p, u, v: gold_d if (p[1] * 1.1 + math.atan2(p[0] - 8, p[2] - 2) * 0.9) % 1.6 < 0.5 else gold
    for i, (r, y0, y1) in enumerate([(1.5, 15.0, 18.6), (1.2, 18.6, 22.0), (0.9, 22.0, 25.4), (0.6, 25.4, 28.4), (0.35, 28.4, 30.4)]):
        dz = -i * 0.8
        s.box((8 - r, y0, 2.4 - r + dz), (8 + r, y1, 2.4 + r + dz), gold, spiral)
    # 파스텔 무지개 갈기: 뒤로 갈수록 색이 바뀌는 가닥
    rainbow = [(250, 160, 190), (252, 200, 140), (250, 236, 150), (170, 230, 180), (150, 200, 250), (196, 160, 240)]
    for i, c in enumerate(rainbow):
        z0 = 1.0 + i * 2.6
        s.tufts(((5.4, 13.4, z0), (10.6, 19.2, z0 + 2.8)), 5, (1.2, 2.2), c, jitter=0.04)
        s.tufts(((5.8, 2.0 + i * 1.6, 15.0), (10.2, 4.6 + i * 1.6 + 2.0, 18.4)), 3, (1.2, 2.0), c, jitter=0.04)
    s.tufts(((5.2, 12.0, -1.8), (10.8, 15.2, 1.6)), 6, (1.2, 2.0), rainbow[0], jitter=0.04)     # 앞머리
    for x0 in (2.4, 11.6):
        s.ear(x0, x0 + 2.4, 15.2, 19.6, 6.4, 8.4, wh, (240, 200, 220), taper=2)
    return s.done()


# ───────────────────────── 10. 잭 (개구리) ─────────────────────────

def zack():
    """청개구리: 등은 선명한 초록(짙은 점), 턱·입술은 연노랑, 튀어나온 큰 눈(금빛 홍채, 가로 동공)"""
    s = Sculpt("zack", 310)
    green = (96, 186, 64)
    belly = (238, 234, 170)
    sp = where(lambda p, f: p[1] > 6.5, lambda f, p, u, v: dark(green, 0.66) if hnoise(math.floor(p[0] * 0.55), math.floor(p[1] * 0.55), math.floor(p[2] * 0.55), 10) > 0.82 else None)
    low = where(lambda p, f: p[1] < 5.2, lambda f, p, u, v: belly)
    s.head(green, chain(low, sp, skin(green, 17, 0.05)), to=(16, 14, 16))
    s.rbox((-0.8, 1.0, -1.0), (16.8, 6.4, 12.0), 2.2, belly, skin(belly, 18, 0.04))         # 넓은 턱
    s.box((-0.95, 5.0, -1.15), (16.95, 5.5, 10.6), (60, 110, 40))                           # 입 선
    s.rbox((-0.4, 5.4, -0.8), (16.4, 7.6, 13.0), 1.0, green, chain(sp, skin(green, 19)))
    for cx in (3.0, 13.0):
        s.blob((cx, 14.6, 1.2), (3.2, 3.2, 3.0), green, chain(sp, skin(green, 20)), n=5)       # 눈 둔덕
        s.eye(cx, 14.8, -2.05, 2.1, 2.1, iris=(236, 190, 50), pupil=BLACK, slit="horizontal", rim=(56, 120, 36))
    for x in (6.6, 9.0):
        s.box((x, 9.4, -0.12), (x + 0.6, 10.0, 0.1), (40, 80, 26))
    return s.done()


# ───────────────────────── 11. 릭 (여우) ─────────────────────────

def rick():
    """붉은 여우: 주황 털, 흰 볼·주둥이 아래·턱, 검은 코와 귀 끝, 날렵한 주둥이, 호박색 눈"""
    s = Sculpt("rick", 311)
    org = (222, 108, 36)
    white = (246, 240, 228)
    lowwhite = where(lambda p, f: p[1] < 6.0 and f in ("east", "west", "north", "down"), lambda f, p, u, v: white)
    s.head(org, chain(lowwhite, fur(org, 19, 0.12)))
    s.blob((3.2, 4.6, 1.0), (3.8, 3.2, 2.6), white, fur(white, 20, 0.05), n=4)              # 흰 볼 (옆으로 뻗침)
    s.blob((12.8, 4.6, 1.0), (3.8, 3.2, 2.6), white, fur(white, 20, 0.05), n=4)
    under = lambda f, p, u, v: white if p[1] < 5.6 else None
    s.rbox((5.0, 3.6, -8.2), (11.0, 8.8, 0.8), 1.4, org, chain(under, fur(org, 21, 0.1)))
    s.rbox((6.6, 6.8, -9.0), (9.4, 8.6, -7.4), 0.6, (24, 20, 22))
    s.box((5.6, 3.0, -7.4), (10.4, 3.6, 0.2), (60, 36, 30))                                 # 입 선 (다문 입, 살짝 웃음)
    for cx in (4.4, 11.6):
        s.eye(cx, 10.6, -0.05, 1.5, 0.75, iris=(232, 160, 40), pupil=BLACK, slit="vertical", lid=dark(org, 0.62))
    for x0 in (1.2, 10.6):
        s.ear(x0, x0 + 4.2, 15.0, 22.4, 5.4, 8.8, org, white, tip=(34, 22, 18), taper=3, painter=fur(org, 22, 0.1))
    s.tufts(((-1.2, 1.0, 2.0), (1.0, 6.6, 12.0)), 8, (1.0, 2.0), white, jitter=0.04)
    s.tufts(((15.0, 1.0, 2.0), (17.2, 6.6, 12.0)), 8, (1.0, 2.0), white, jitter=0.04)
    return s.done()


# ───────────────────────── 12. 브랜던 (흑표범) ─────────────────────────

def brandon():
    """흑표범: 거의 검은 털에 보랏빛 윤기(위쪽이 밝게), 연두빛 노란 눈(세로 동공), 송곳니 드러낸 입"""
    s = Sculpt("brandon", 312)
    base = (46, 40, 56)
    sheen = lambda f, p, u, v: tone((84, 72, 104), 1 + (hnoise(math.floor(p[0] * 3), math.floor(p[1] * 3), math.floor(p[2] * 3), 23) - 0.5) * 0.12) if f == "up" or (p[1] > 13.0 and f != "down") else None
    s.head(base, chain(sheen, fur(base, 24, 0.14, lo=0.8, hi=1.1)))
    s.blob((8.0, 7.4, -1.6), (4.4, 2.6, 3.0), (58, 52, 70), chain(sheen, fur((58, 52, 70), 25, 0.1)), n=4)   # 주둥이
    s.rbox((6.6, 8.4, -5.2), (9.4, 9.8, -4.0), 0.5, (90, 60, 80))                             # 코
    s.box((4.4, 3.0, -4.2), (11.6, 5.4, 0.6), MOUTH)
    s.box((6.0, 3.1, -3.2), (10.0, 3.7, -0.4), TONGUE)
    s.teeth(4.4, 11.6, 5.4, -4.5, 6, 0.8, fang_every=1)
    s.rbox((4.8, 1.0, -3.8), (11.2, 3.1, 0.6), 0.7, (52, 46, 62))
    s.teeth(4.8, 11.2, 3.1, -4.0, 5, 0.7, down=False, fang_every=1)
    for cx in (4.4, 11.6):
        s.eye(cx, 11.0, -0.05, 1.5, 0.85, iris=(208, 222, 70), pupil=BLACK, slit="vertical", lid=(30, 26, 36))
    for x0 in (1.4, 11.0):
        s.blob((x0 + 1.8, 16.4, 7.6), (1.9, 1.8, 1.2), base, sheen, n=3)
        s.box((x0 + 0.9, 15.4, 6.3), (x0 + 2.7, 17.4, 6.6), (110, 70, 90))
    for x, y in ((2.0, 6.6), (2.6, 5.6), (13.6, 6.6), (13.0, 5.6)):                         # 흰 수염 몇 가닥
        s.box((x - 1.6, y, -1.2), (x + 0.4, y + 0.22, -1.0), (210, 210, 216))
    return s.done()


# ───────────────────────── 13. 얼 (바다코끼리) ─────────────────────────

def earl():
    """바다코끼리: 주름진 갈색 피부, 볼록한 수염판(빳빳한 연노랑 수염), 작은 눈, 긴 상아"""
    s = Sculpt("earl", 313)
    hide = (140, 100, 82)
    wr = lambda f, p, u, v: tone(hide, 0.8) if f not in ("up", "down") and (p[1] * 1.1 + math.sin(p[0] * 0.7 + p[2] * 0.4) * 0.6) % 2.4 < 0.3 else None
    s.head(hide, chain(wr, skin(hide, 25, 0.07)))
    pad = (196, 156, 120)
    bristle = lambda f, p, u, v: (110, 76, 58) if f == "north" and (math.floor(p[0] * 1.6) + math.floor(p[1] * 1.6)) % 3 == 0 and hnoise(math.floor(p[0] * 1.6), math.floor(p[1] * 1.6), 0, 13) > 0.45 else None
    for x0 in (1.0, 8.0):
        s.blob((x0 + 3.5, 5.0, -2.4), (3.6, 3.6, 3.0), pad, chain(bristle, skin(pad, 26)), n=5)
    s.rbox((6.6, 7.4, -4.6), (9.4, 9.0, -3.4), 0.5, (60, 40, 34))
    for x, y in ((1.4, 6.0), (1.8, 3.6), (14.2, 6.0), (13.8, 3.6), (3.8, 1.8), (12.2, 1.8)):   # 뻗친 수염
        s.box((x, y, -5.7), (x + 0.3, y + 0.3, -5.0), (242, 226, 176))
    for cx in (4.0, 12.0):
        s.eye(cx, 11.4, -0.05, 0.75, 0.6, iris=(30, 20, 16), lid=dark(hide, 0.7))
    ivory = (248, 242, 222)
    for x0 in (3.6, 10.6):
        s.rbox((x0, -3.6, -4.4), (x0 + 1.8, 2.4, -2.0), 0.5, ivory)
        s.rbox((x0 + 0.2, -8.2, -4.6), (x0 + 1.6, -3.4, -2.6), 0.5, ivory)
        s.box((x0 + 0.45, -10.4, -4.4), (x0 + 1.35, -8.0, -3.0), ivory)
    return s.done()


# ───────────────────────── 14. 제이크 (코브라) ─────────────────────────

def jake():
    """코브라: 올리브 비늘, 넓게 펼친 후드(안쪽 크림색 + 안경 무늬), 노란 눈(세로 동공), 송곳니, 갈라진 혀"""
    s = Sculpt("jake", 314)
    olive = (98, 132, 58)
    cream = (232, 218, 160)
    scl = lambda f, p, u, v: tone(olive, 0.78) if (math.floor(p[0] * 1.5 + p[1] * 0.75) + math.floor(p[1] * 1.5) + math.floor(p[2] * 1.5)) % 2 == 0 else None
    s.head(olive, chain(scl, skin(olive, 27, 0.05)))
    # 후드 (머리 뒤로 넓게, 앞면은 크림색 배, 가장자리는 짙은 올리브)
    def hood_front(f, p, u, v):
        if f != "north":
            return None
        return tone(cream, 0.82) if p[1] % 3.2 < 0.7 else cream                                 # 배 비늘 가로 띠

    def spectacle(f, p, u, v):
        if f != "south":
            return None
        ring = lambda cx: ((p[0] - cx) / 2.6) ** 2 + ((p[1] - 11.0) / 2.3) ** 2
        r1, r2 = ring(4.6), ring(11.4)
        if 0.35 < r1 < 1 or 0.35 < r2 < 1 or (abs(p[1] - 11.0) < 0.5 and 7.2 < p[0] < 8.8):
            return (34, 30, 24)
        if r1 <= 0.35 or r2 <= 0.35:
            return cream
        return None
    for w, y0, y1, z in ((24, 0.0, 16.0, 9.2), (28, 2.0, 18.0, 9.6), (22, 17.0, 21.0, 9.8)):
        s.rbox((8 - w / 2, y0, z), (8 + w / 2, y1, 12.0), 1.8, olive, chain(spectacle, hood_front, scl))
    for x0, x1 in ((-6.2, -5.0), (21.0, 22.2)):                                                 # 후드 가장자리 짙은 테
        s.box((x0, 2.4, 9.5), (x1, 17.6, 12.1), dark(olive, 0.6))
    s.rbox((3.6, 4.2, -4.4), (12.4, 9.2, 0.8), 1.4, olive, chain(scl, skin(olive, 28)))       # 주둥이
    s.box((3.9, 2.0, -4.0), (12.1, 4.2, 0.4), MOUTH)
    s.rbox((4.2, 0.6, -3.6), (11.8, 2.2, 0.4), 0.6, cream)
    s.box((4.8, 1.9, -4.3), (5.8, 4.2, -3.6), WHITE)                                          # 송곳니
    s.box((10.2, 1.9, -4.3), (11.2, 4.2, -3.6), WHITE)
    tongue = (210, 40, 60)
    s.box((7.5, 1.4, -7.4), (8.5, 2.0, -3.6), tongue)
    s.box((6.9, 1.4, -8.6), (7.6, 2.0, -7.2), tongue)
    s.box((8.4, 1.4, -8.6), (9.1, 2.0, -7.2), tongue)
    for cx in (3.8, 12.2):
        s.eye(cx, 10.8, -0.05, 1.6, 0.95, iris=(242, 200, 50), pupil=BLACK, slit="vertical", lid=dark(olive, 0.6))
    for x in (6.8, 8.8):
        s.box((x, 8.6, -4.55), (x + 0.5, 9.1, -4.35), (30, 40, 20))
    return s.done()


# ───────────────────────── 15. 리히터 (쥐) ─────────────────────────

def richter():
    """쥐: 회갈색 털(배 쪽 밝음), 뾰족한 주둥이, 분홍 코·큰 둥근 귀, 앞니, 수염, 붉은빛 검은 눈"""
    s = Sculpt("richter", 315)
    coat = (112, 104, 98)
    under = (190, 180, 172)
    pink = (232, 150, 160)
    low = where(lambda p, f: p[1] < 5.0, fur(under, 26, 0.08))
    s.head(coat, chain(low, fur(coat, 27, 0.18)))
    s.blob((8.0, 5.6, -2.0), (4.2, 3.4, 3.2), coat, chain(low, fur(coat, 28, 0.14)), n=4)
    s.rbox((5.8, 3.6, -8.6), (10.2, 7.4, -3.8), 1.4, coat, chain(low, fur(coat, 29, 0.12)))
    s.rbox((6.8, 5.4, -9.6), (9.2, 7.4, -8.2), 0.6, pink)
    s.box((7.0, 2.4, -7.4), (7.9, 4.0, -6.8), (246, 230, 190))                                # 누런 앞니
    s.box((8.1, 2.4, -7.4), (9.0, 4.0, -6.8), (246, 230, 190))
    for side in (-1, 1):                                                                       # 수염 3가닥
        for i in range(3):
            x0 = 6.0 if side < 0 else 10.0
            y = 5.2 + i * 0.7
            a, b = (x0 - 4.6, y, -7.0 + i * 0.5), (x0, y + 0.18, -6.8 + i * 0.5)
            if side > 0:
                a, b = (x0, y, -7.0 + i * 0.5), (x0 + 4.6, y + 0.18, -6.8 + i * 0.5)
            s.box(a, b, (220, 220, 224))
    for cx in (4.8, 11.2):
        s.eye(cx, 10.2, -0.05, 1.1, 1.0, iris=(36, 10, 14), pupil=BLACK, lid=dark(coat, 0.7))
    for x0 in (-1.4, 11.0):
        s.rbox((x0, 13.4, 5.4), (x0 + 6.4, 20.6, 7.8), 2.6, coat, fur(coat, 30, 0.1))
        s.rbox((x0 + 1.0, 14.4, 5.25), (x0 + 5.4, 19.6, 5.6), 1.8, pink)
    s.tufts(((0.0, 13.0, 0.0), (16.0, 16.2, 14.0)), 12, (1.0, 2.0), coat, jitter=0.15)
    return s.done()


# ───────────────────────── 16. 돼지 학살자 (돼지) ─────────────────────────

def pig_butcher():
    """돼지: 연분홍 살, 진분홍 코(콧구멍 두 개), 앞으로 접힌 귀, 피가 튄 자국"""
    s = Sculpt("pig_butcher", 316)
    pink = (238, 178, 168)
    snout = (226, 132, 132)
    def blood(f, p, u, v):
        # 아래쪽(턱·볼)으로 갈수록 많아지는 튄 자국 + 오른쪽 볼에서 흘러내린 줄
        if f == "north" and 10.6 < p[0] < 11.4 and 3.0 < p[1] < 9.5:
            return (128, 16, 22)
        density = max(0.0, (8.0 - p[1]) / 8.0)
        n = hnoise(math.floor(p[0] * 1.3), math.floor(p[1] * 1.3), math.floor(p[2] * 1.3), 16)
        return (132, 18, 24) if f != "up" and n > 1.0 - density * 0.22 else None
    s.head(pink, chain(blood, skin(pink, 31, 0.05)))
    s.blob((4.2, 5.6, 0.6), (3.0, 2.8, 2.2), light(pink, 1.03), chain(blood, skin(pink, 32)), n=4)       # 통통한 볼
    s.blob((11.8, 5.6, 0.6), (3.0, 2.8, 2.2), light(pink, 1.03), chain(blood, skin(pink, 32)), n=4)
    s.blob((8.0, 5.8, -2.4), (3.6, 2.8, 2.0), snout, skin(snout, 33), n=4, axis="z")                     # 코 (원통)
    s.rbox((4.8, 3.4, -4.6), (11.2, 8.2, -4.1), 1.4, light(snout, 1.04))
    for x in (5.8, 8.8):
        s.rbox((x, 4.8, -4.75), (x + 1.4, 6.8, -4.4), 0.4, (110, 40, 48))
    s.box((4.6, 2.0, -2.6), (11.4, 2.6, 0.4), (130, 50, 56))                                  # 입 선
    for cx in (4.2, 11.8):
        s.eye(cx, 10.8, -0.05, 1.1, 0.7, iris=(36, 22, 18), lid=dark(pink, 0.78))
    for x0, sgn in ((0.4, -1), (11.0, 1)):                                                    # 접힌 귀
        s.rbox((x0, 14.6, 3.4), (x0 + 4.6, 18.4, 7.6), 1.2, pink, skin(pink, 34))
        s.box((x0 + 0.4, 13.0, 1.0), (x0 + 4.2, 15.2, 3.8), pink, rot_=rot("x", -22.5, [x0 + 2.3, 15.0, 3.4]))
        s.box((x0 + 1.0, 15.0, 3.2), (x0 + 3.6, 17.6, 3.5), (214, 120, 130))
    s.tufts(((2.0, 3.0, -2.0), (14.0, 12.0, 0.6)), 6, (0.5, 0.9), (150, 22, 28), jitter=0.05)   # 튄 피 방울
    return s.done()


# ───────────────────────── 17. 코리 (얼룩말) ─────────────────────────

def cory():
    """얼룩말: 얼굴은 세로 줄무늬, 이마는 갈매기 무늬, 검은 주둥이, 흑백 줄무늬로 선 갈기"""
    s = Sculpt("cory", 317)
    ink = (26, 24, 28)
    def zebra(f, p, u, v):
        # 이마(y>9)는 가운데로 모이는 V 무늬, 아래는 세로 줄
        if p[1] > 9:
            q = abs(p[0] - 8) * 0.55 + p[1] + math.sin(p[2] * 0.5) * 0.4
        else:
            q = p[0] * 0.9 + math.sin(p[1] * 0.45 + p[2] * 0.3) * 0.8 + p[2] * 0.35
        return ink if q % 2.6 < 1.05 else None
    s.head(WHITE, chain(zebra, skin(WHITE, 35, 0.03)))
    s.rbox((3.4, 0.4, -5.6), (12.6, 10.2, 1.0), 2.0, WHITE, chain(zebra, skin(WHITE, 36, 0.03)))
    s.rbox((3.8, 0.0, -9.6), (12.2, 7.8, -4.8), 1.8, (40, 38, 42), skin((40, 38, 42), 37))
    for x in (4.8, 9.8):
        s.rbox((x, 4.2, -9.75), (x + 1.4, 6.4, -9.4), 0.3, (12, 10, 12))
    s.side_eyes(3.0, 10.4, 1.3, 1.0, x_left=-0.05, x_right=16.05, iris=(30, 22, 18), lid=ink)
    mane = lambda f, p, u, v: WHITE if math.floor(p[2] * 0.85) % 2 == 0 else ink
    s.tufts(((6.0, 14.2, -0.4), (10.0, 20.4, 17.2)), 28, (1.0, 2.0), ink, painter=mane)
    for x0 in (2.0, 11.2):
        s.ear(x0, x0 + 2.8, 15.0, 20.6, 6.4, 8.6, WHITE, (210, 206, 206), tip=ink, taper=3, painter=zebra)
    return s.done()


# ───────────────────────── 18. 마크 (곰) ─────────────────────────

def mark():
    """갈색 곰: 짙은 갈색 털(어깨 쪽 더 짙음), 밝은 황갈색 주둥이, 검은 코, 작고 둥근 귀"""
    s = Sculpt("mark", 318)
    brown = (112, 72, 44)
    deep = (82, 52, 32)
    muzzle = (190, 146, 100)
    back = lambda p, f: p[2] > 9 or p[1] < 2
    s.head(brown, chain(where(back, fur(deep, 33, 0.2)), fur(brown, 34, 0.18)))
    s.blob((8.0, 5.0, -2.0), (4.4, 3.4, 3.0), muzzle, fur(muzzle, 35, 0.08), n=5)           # 주둥이
    s.blob((8.0, 7.4, -4.8), (1.9, 1.2, 1.0), (30, 22, 20), n=3, round_=0.4)                # 코
    s.box((7.85, 3.6, -4.95), (8.15, 6.4, -4.7), (60, 40, 30))
    s.box((5.6, 3.2, -4.75), (10.4, 3.6, -4.5), (60, 40, 30))
    for cx in (4.4, 11.6):
        s.eye(cx, 10.8, -0.05, 0.95, 0.85, iris=(40, 22, 14), pupil=BLACK, lid=dark(brown, 0.68))
    s.rbox((3.2, 12.0, -0.6), (12.8, 13.6, 1.0), 0.6, tone(brown, 1.1))                    # 이마 털 결
    for x0 in (-0.4, 11.6):
        s.blob((x0 + 2.4, 16.2, 7.6), (2.4, 2.2, 1.6), brown, fur(brown, 36, 0.12), n=4)
        s.rbox((x0 + 1.2, 15.2, 6.0), (x0 + 3.6, 17.6, 6.3), 0.8, (150, 104, 74))
    s.tufts(((-1.2, 0.0, 1.0), (1.0, 14.0, 15.0)), 12, (1.4, 2.4), deep, jitter=0.15)
    s.tufts(((15.0, 0.0, 1.0), (17.2, 14.0, 15.0)), 12, (1.4, 2.4), deep, jitter=0.15)
    return s.done()


# ───────────────────────── 19. 토니 (호랑이) ─────────────────────────

def tony():
    """호랑이: 주황 털에 검은 줄(이마는 가로 줄, 볼은 사선), 흰 볼·눈 위 흰 점·주둥이, 포효하는 입"""
    s = Sculpt("tony", 319)
    org = (232, 134, 40)
    cream = (250, 240, 214)
    ink = (30, 18, 12)
    st = stripes(ink, 3.0, 0.95, axis=(0.22, 1.0, 0.18), wobble=0.8, seed=3)
    s.head(org, chain(where(lambda p, f: p[1] < 6.6 and f in ("east", "west", "down"), lambda f, p, u, v: cream), st, fur(org, 35, 0.08)))
    for cx in (3.6, 12.4):
        s.blob((cx, 4.6, 0.8), (3.6, 3.2, 2.4), cream, chain(stripes(ink, 3.2, 0.8, axis=(0.9, 0.6, 0.0), wobble=0.5, seed=5), fur(cream, 36, 0.05)), n=4)
    s.rbox((4.0, 5.6, -5.0), (12.0, 10.2, 1.0), 1.6, cream, skin(cream, 37))
    s.rbox((6.2, 8.6, -5.8), (9.8, 10.2, -4.6), 0.6, (220, 112, 130))
    s.box((4.2, 2.2, -4.6), (11.8, 5.6, 0.4), MOUTH)
    s.box((5.6, 2.4, -4.0), (10.4, 3.2, -1.0), TONGUE)
    s.rbox((4.6, 0.4, -4.2), (11.4, 2.4, 0.4), 0.7, cream)
    s.teeth(4.2, 11.8, 5.6, -4.8, 6, 0.85, fang_every=1)
    s.teeth(4.6, 11.4, 2.4, -4.4, 5, 0.8, down=False, fang_every=1)
    for cx in (4.4, 11.6):
        s.eye(cx, 11.4, -0.05, 1.5, 0.8, iris=(240, 196, 70), pupil=BLACK, lid=ink)
        s.box((cx - 1.0, 12.6, -0.25), (cx + 1.0, 13.4, 0.1), cream)                            # 눈 위 흰 점
    for x0 in (1.0, 11.0):
        s.blob((x0 + 2.0, 16.4, 7.6), (2.0, 1.9, 1.2), org, fur(org, 38, 0.08), n=3)
        s.box((x0 + 1.0, 15.4, 6.35), (x0 + 3.0, 17.4, 6.65), cream)
        s.box((x0 + 1.2, 17.0, 8.6), (x0 + 2.8, 18.2, 8.9), ink)                                  # 귀 뒤 검은 무늬
    s.tufts(((-1.4, 1.0, 1.0), (0.8, 8.4, 8.0)), 8, (1.0, 2.0), cream, jitter=0.04)
    s.tufts(((15.2, 1.0, 1.0), (17.4, 8.4, 8.0)), 8, (1.0, 2.0), cream, jitter=0.04)
    return s.done()


# ───────────────────────── 20. 형사 (중절모) ─────────────────────────

def detective():
    """중절모: 짙은 회갈색 펠트, 가운데가 접힌 크라운, 앞 양쪽 꼬집은 자국, 검은 리본 띠와 작은 깃털, 앞이 살짝 내려간 챙"""
    s = Sculpt("detective", 320)
    felt = (86, 74, 66)
    band = (26, 22, 22)
    feel = skin(felt, 39, 0.05, y0=13, y1=22, lo=0.85, hi=1.08)
    s.rbox((-3.8, 13.0, -2.6), (19.8, 14.2, 18.6), 1.2, felt, feel)                        # 챙
    s.box((-2.0, 12.4, -4.6), (18.0, 13.6, -2.4), felt, feel)                                # 앞챙 아래로 꺾임
    s.rbox((0.8, 14.0, 0.8), (15.2, 19.6, 15.2), 1.8, felt, feel)                            # 크라운
    s.rbox((1.8, 19.2, 1.8), (14.2, 21.4, 14.2), 1.6, felt, feel)
    s.box((6.6, 20.6, 1.4), (9.4, 21.9, 14.6), tone(felt, 0.72))                              # 가운데 접힘
    for x0 in (2.0, 12.0):                                                                     # 앞 꼬집음
        s.box((x0, 17.0, 0.6), (x0 + 2.0, 20.2, 1.4), tone(felt, 0.75))
    s.box((0.7, 14.2, 0.7), (15.3, 15.9, 15.3), band)
    s.rbox((12.6, 14.4, 2.4), (15.6, 16.0, 5.0), 0.4, band)                                    # 리본 매듭
    s.box((14.6, 15.4, 3.0), (15.6, 18.4, 3.8), (176, 40, 40))                                 # 작은 깃털
    s.box((14.8, 18.2, 3.2), (15.4, 19.6, 3.6), (210, 70, 60))
    return s.done()


# ───────────────────────── 21. 바이커 (헬멧) ─────────────────────────

def biker():
    """풀페이스 헬멧: 광택 있는 진홍색 셸 + 흰 줄무늬 두 줄, 짙은 연기빛 바이저(빛 반사), 턱 통풍구"""
    s = Sculpt("biker", 321)
    shell = (176, 28, 44)
    def glossy(f, p, u, v):
        if f in ("up", "north", "south") and (6.4 < p[0] < 7.3 or 8.7 < p[0] < 9.6):
            return (236, 236, 240)                                                             # 흰 줄무늬 두 줄
        if f in ("up", "west") and p[1] > 12 and 2.0 < p[2] < 9.0 and 2.0 < p[0] < 6.0:
            return tone(shell, 1.32)                                                            # 광택 반사
        return None
    s.rbox((-1.2, -1.2, -1.2), (17.2, 17.4, 17.2), 3.2, shell, chain(glossy, skin(shell, 40, 0.025, lo=0.86, hi=1.08)))
    visor = (22, 24, 34)
    refl = lambda f, p, u, v: (120, 140, 180) if f == "north" and (abs((p[0] - p[1] * 0.8) % 7 - 1.2) < 0.45 or abs((p[0] - p[1] * 0.8) % 7 - 2.4) < 0.18) else None
    s.rbox((0.4, 3.6, -1.95), (15.6, 11.8, -0.8), 1.4, visor, refl)
    s.box((0.2, 11.6, -2.3), (15.8, 12.4, -1.0), (40, 40, 46))                                # 바이저 테
    for x in (-2.0, 16.8):
        s.rbox((x, 6.0, 4.4), (x + 1.2, 9.6, 8.2), 0.5, (40, 40, 46))                         # 바이저 경첩
    s.rbox((3.2, -1.8, -1.6), (12.8, 2.6, 0.6), 0.6, (36, 36, 42))                             # 턱 보호대
    for x in (5.0, 7.2, 9.4):
        s.box((x, -0.6, -1.75), (x + 1.4, 1.6, -1.5), (14, 14, 18))                           # 통풍구
    return s.done()


MASKS = {f.__name__: f for f in [richard, don_juan, graham, dennis, george, rufus, rami, willem, peter, zack, rick,
                                 brandon, earl, jake, richter, pig_butcher, cory, mark, tony, detective, biker]}
