#!/usr/bin/env python3
"""소방도끼 (루프 제작물). TACZ풍: 형태는 큐브로, 면은 단색, 명암은 면 방향별로 미리 칠함.

출력: tools/loop/fire_axe/out/fire_axe.json (Java 아이템 모델, 26.3 오일러 회전) + fire_axe.png
좌표: 손잡이 +Y (y 0~28), 중심 x=8,z=8. 날은 −z, 곡괭이 뿔은 +z. 두께 방향 x.
"""
import json, math, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import fp_sim  # noqa: E402
from voxel import face_point  # noqa: E402

DENSITY = 4          # 모델 1px 당 텍셀
FACES = ("north", "south", "east", "west", "up", "down")
# 면 방향별 미리 칠한 명암 (TACZ 실측: 위 +15~25%, 아래 −15~25%)
DIR = {"up": 1.22, "north": 0.94, "east": 1.0, "west": 1.0, "south": 0.94, "down": 0.80}   # 좌우·앞뒤 대칭

PAL = {
    "red":        (104, 64, 60),    # 적색 도장 (V≈0.41, S≈0.42)
    "red_top":    (92, 40, 38),
    "steel":      (112, 118, 126),  # 청회색 강철
    "ground":     (166, 172, 182),  # 연마면 (V≈0.71, 윗면 ≤0.88)
    "edge":       (194, 202, 216),  # 칼날선 (V≈0.85, 푸른 기, 연마면과 대비 작게)
    "glass":      (44, 46, 50),     # 유리섬유 자루
    "glass_dark": (34, 36, 40),
    "rubber":     (30, 30, 32),
    "rubber_rib": (40, 40, 43),
    "cap":        (52, 54, 58),
    "collar":     (84, 88, 94),     # 머리 아래 강철 칼라
}

ELS = []   # (frm, to, colour_or_fn, rotation)


def box(frm, to, col, rot=None):
    ELS.append(([float(v) for v in frm], [float(v) for v in to], col, rot))


def eul(origin, x=0, y=0, z=0):
    return {"origin": [round(v, 4) for v in origin], "x": x, "y": y, "z": z}


T = math.tan(math.radians(22.5))


def oct_y(cx, cz, r, y0, y1, col):
    """정팔각 단면 원통 (y축): 폭 2r·두께 2r·tan22.5 직사각 4장을 0/45/90/135°로 겹침"""
    w = r * T
    box([cx - r, y0, cz - w], [cx + r, y1, cz + w], col)
    box([cx - w, y0, cz - r], [cx + w, y1, cz + r], col)
    box([cx - r, y0, cz - w], [cx + r, y1, cz + w], col, eul([cx, y0, cz], y=45))
    box([cx - w, y0, cz - r], [cx + w, y1, cz + r], col, eul([cx, y0, cz], y=45))


def oct_z(cx, cy, rx, ry, z0, z1, col, rot=None):
    """팔각 단면 막대 (z축). rx≠ry 면 납작한 팔각 (모서리 45° 깎기)"""
    c = min(rx, ry) * (1 - T)       # 깎는 양
    box([cx - rx, cy - ry + c, z0], [cx + rx, cy + ry - c, z1], col, rot)
    box([cx - rx + c, cy - ry, z0], [cx + rx - c, cy + ry, z1], col, rot)


# ───────── 자루 (유리섬유, 정팔각 단면, 아래 고무 손잡이) ─────────
CX = CZ = 8.0
oct_y(CX, CZ, 1.0, 0.0, 0.3, "cap")                # 끝 마개
oct_y(CX, CZ, 1.14, 0.3, 0.75, "rubber")           # 손잡이 끝 스웰 (벌어짐)
oct_y(CX, CZ, 1.04, 0.75, 1.2, "rubber")
oct_y(CX, CZ, 0.92, 1.1, 7.6, "rubber")            # 고무 손잡이
for i in range(6):                                  # 미끄럼 방지 마디
    y = 1.9 + i * 0.9
    oct_y(CX, CZ, 1.0, y, y + 0.3, "rubber_rib")
oct_y(CX, CZ, 1.0, 7.6, 7.95, "rubber_rib")        # 손잡이 끝 테두리
oct_y(CX, CZ, 0.8, 7.95, 25.0, "glass")            # 자루 (눈 속까지)
oct_y(CX, CZ, 0.92, 20.1, 20.85, "collar")         # 머리 아래 강철 칼라

# ───────── 강체 변환 도구: 회전을 여러 번 겹쳐도 26.3 오일러(Rz·Ry·Rx) 하나로 정확히 내보냄 ─────────
def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]
def _R(axis, deg):
    a = math.radians(deg); c, s_ = math.cos(a), math.sin(a)
    return {"x": [[1, 0, 0], [0, c, -s_], [0, s_, c]], "y": [[c, 0, s_], [0, 1, 0], [-s_, 0, c]],
            "z": [[c, -s_, 0], [s_, c, 0], [0, 0, 1]]}[axis]
class Xf:
    """p_world = R·p + t"""
    def __init__(self, R=None, t=(0, 0, 0)):
        self.R = R or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]; self.t = list(t)
    def __mul__(self, o):            # self ∘ o (o 를 먼저 적용)
        return Xf(_mm(self.R, o.R), [a + b for a, b in zip(_mv(self.R, o.t), self.t)])
    @staticmethod
    def rot(axis, deg, about=(0, 0, 0)):
        R = _R(axis, deg); c = _mv(R, about)
        return Xf(R, [about[i] - c[i] for i in range(3)])
    @staticmethod
    def move(v):
        return Xf(None, v)
def _euler(R):
    y = math.asin(max(-1, min(1, -R[2][0])))
    if abs(math.cos(y)) > 1e-6:
        x = math.atan2(R[2][1], R[2][2]); z = math.atan2(R[1][0], R[0][0])
    else:
        x = math.atan2(-R[1][2], R[1][1]); z = 0.0
    return [round(math.degrees(v), 4) for v in (x, y, z)]
def put(xf, frm, to, col):
    """xf 좌표계의 상자를 월드에 놓음 (상자 중심을 기준으로 회전)"""
    c = [(frm[i] + to[i]) / 2 for i in range(3)]; h = [(to[i] - frm[i]) / 2 for i in range(3)]
    wc = [a + b for a, b in zip(_mv(xf.R, c), xf.t)]
    ex, ey, ez = _euler(xf.R)
    rot = None if max(abs(ex), abs(ey), abs(ez)) < 1e-4 else {"origin": [round(v, 4) for v in wc], "x": ex, "y": ey, "z": ez}
    box([wc[i] - h[i] for i in range(3)], [wc[i] + h[i] for i in range(3)], col, rot)

# ───────── 머리: 눈 (자루 끼우는 통) — 모든 모서리 45° 깎은 꽉 찬 블록 ─────────
def chamfer_box(frm, to, c, col, xf=None):
    """모서리 12개를 45°로 깎은 상자: 안쪽으로 들인 상자 3개 + 모서리마다 45° 돌린 막대"""
    xf = xf or Xf()
    (x0, y0, z0), (x1, y1, z1) = frm, to
    put(xf, [x0, y0 + c, z0 + c], [x1, y1 - c, z1 - c], col)
    put(xf, [x0 + c, y0, z0 + c], [x1 - c, y1, z1 - c], col)
    put(xf, [x0 + c, y0 + c, z0], [x1 - c, y1 - c, z1], col)
    h = c * math.sqrt(2) / 2
    for yy in (y0 + c, y1 - c):
        for zz in (z0 + c, z1 - c):
            put(xf * Xf.rot("x", 45, (0, yy, zz)), [x0 + c, yy - h, zz - h], [x1 - c, yy + h, zz + h], col)
    for xx in (x0 + c, x1 - c):
        for yy in (y0 + c, y1 - c):
            put(xf * Xf.rot("z", 45, (xx, yy, 0)), [xx - h, yy - h, z0 + c], [xx + h, yy + h, z1 - c], col)
        for zz in (z0 + c, z1 - c):
            put(xf * Xf.rot("y", 45, (xx, 0, zz)), [xx - h, y0 + c, zz - h], [xx + h, y1 - c, zz + h], col)

EY0, EY1 = 20.8, 25.2
X0, X1, Z0, Z1 = 7.1, 8.9, 6.9, 9.1
chamfer_box([X0, EY0, Z0], [X1, EY1, Z1], 0.177, "red")
oct_y(CX, CZ, 0.6, EY1, EY1 + 0.05, "glass_dark")   # 눈 윗면으로 보이는 자루 끝
chamfer_box([7.84, EY1 - 0.2, 7.35], [8.16, EY1 + 0.03, 8.65], 0.06, "steel")   # 자루 쐐기 (윗면과 거의 같은 높이)



# ───────── 날: 칼날선 위 회전점으로 위/가운데/아래 3구역, 볼은 y축 소각 회전 판(매끈한 쐐기) ─────────
ZE = 2.7                     # 칼날선 z
YB, YT = 21.8, 24.2          # 가운데 구역
DL = 11.25                   # 꺾임 한 번의 각 (위아래로 두 번씩 → 날 곡선·벌어짐 22.5°)
HS = (1.0, 1.0)              # 위·아래 구역 높이 (꺾일 때마다)
TH = math.tan(math.radians(DL / 2))
DEPTH = Z0 + 0.4 - ZE        # 칼날선 → 눈 속까지
ALPHA = math.degrees(math.atan2(0.62 - 0.12, DEPTH))   # 볼 판 기울기 (두께 0.24 → 눈 쪽 1.76)
# 구역 좌표계: 원점 = 칼날선 위 (8, y, ZE), +z = 날 뒤쪽(눈 방향)
LAYERS = ((0.15, 2.2, "ground", 0.04), (2.15, DEPTH, "red", 0.0))   # (d0, d1, 색, 안으로 들임: 연마면은 얇게 → 경계에 턱)
def blade_section(sec, y0, y1, miter_lo, miter_hi, e_lo=0.0, e_hi=0.0):
    """sec: 구역 변환. y0..y1: 구역 높이. miter: 아래/위 끝을 이등분선으로 자르는지"""
    for (d0, d1, col, ins) in LAYERS:
        lo = y0 + (d1 * TH if miter_lo else 0); hi = y1 - (d1 * TH if miter_hi else 0)
        for sgn in (1, -1):                      # 양쪽 볼 판: 칼날선에서 눈 쪽으로 벌어짐
            tilt = Xf.rot("y", -sgn * ALPHA, (8 + sgn * 0.12, 0, ZE))
            x0_, x1_ = (8 + 0.12 - ins, 8 + 0.12 + 0.26 - ins) if sgn > 0 else (8 - 0.12 - 0.26 + ins, 8 - 0.12 + ins)
            put(sec * tilt, [x0_, lo, ZE + d0], [x1_, hi, ZE + d1], col)
        put(sec, [8 - 0.14, lo, ZE + d0], [8 + 0.14, hi, ZE + d1], col)          # 심재
    e = 0.177                                    # 칼날선: 사각 막대를 축 둘레로 45° → 마름모
    put(sec * Xf.rot("y", 45, (8, 0, ZE + 0.1)), [8 - e / 2, y0 + e_lo, ZE + 0.1 - e / 2], [8 + e / 2, y1 + e_hi, ZE + 0.1 + e / 2], "edge")
def joint(sec, P, ang):
    """꺾임 이음매 메움: 이등분선 방향 얇은 띠 (같은 쐐기 단면)"""
    j = sec * Xf.rot("x", ang, (8, P, ZE))
    for (d0, d1, col, ins) in LAYERS:
        w = (d1 - d0) * TH + 0.03
        d0f = d0 + ((0.15 if d0 < 2.5 else 0.06) if col == "red" else 0.0)   # 연마면과 맞닿는 빨강은 더 물림
        for sgn in (1, -1):
            tilt = Xf.rot("y", -sgn * ALPHA, (8 + sgn * 0.12, 0, ZE))
            x0_, x1_ = (8.12 - ins, 8.38 - ins) if sgn > 0 else (7.62 + ins, 7.88 + ins)
            put(j * tilt, [x0_, P - w, ZE + d0f], [x1_, P + w, ZE + d1], col)
blade_section(Xf(), YB, YT, True, True, -0.05, 0.05)
for sgn in (1, -1):                              # 위(+)·아래(−)로 11.25°씩 두 번 꺾여 휘는 날
    sec, y = Xf(), (YT if sgn > 0 else YB)
    for i, h in enumerate(HS):
        joint(sec, y, sgn * DL / 2)
        sec = sec * Xf.rot("x", sgn * DL, (8, y, ZE))
        last = i == len(HS) - 1
        if sgn > 0:
            blade_section(sec, y, y + h, True, not last, -0.05, -0.45 if last else 0.05)
            y += h
        else:
            blade_section(sec, y - h, y, not last, True, 0.45 if last else -0.05, 0.05)
            y -= h

# ───────── 곡괭이 뿔 (+z): 위·아래·양옆 판 4장이 끝으로 모이는 피라미드, 11.25° 아래로 ─────────
PY, PZ, PL = 23.0, Z1 - 0.3, 4.6
base = Xf.rot("x", 11.25, (8, PY, PZ))
# 쐐기: 끝점에서 뒤로 벌어지는 위·아래 판 2장(끝점 기준 ±각) + 축 위 속채움 상자들
HY, TA = 0.85, 0.3
TIPZ = PZ + PL
by = math.degrees(math.atan2(HY - TA, PL))
tb = math.tan(math.radians(by))
for (s0, s1, col, hx) in ((0.0, 1.5, "ground", 0.4), (1.5, PL + 0.3, "red", 0.42)):
    for sgn in (1, -1):
        f = base * Xf.rot("x", sgn * by, (8, PY, TIPZ))
        y0_, y1_ = (PY, PY + TA) if sgn > 0 else (PY - TA, PY)
        put(f, [8 - hx, y0_, TIPZ - s1], [8 + hx, y1_, TIPZ - s0], col)
    k = s0 + (0.15 if s0 == 0 else 0.0)                  # 속채움: 판 사이 틈 (s·tan) 을 덮는 상자
    while k < s1 - 0.05:
        ln = min(TA / tb * 0.9, s1 - k)
        hy = (k + ln) * tb + 0.02
        put(base, [8 - hx + 0.02, PY - hy, TIPZ - k - ln], [8 + hx - 0.02, PY + hy, TIPZ - k], col)
        k += ln

# ───────── 빌드 ─────────
def colour(c, p):
    name = c(p) if callable(c) else c
    return PAL[name]


def face_dims(frm, to, f):
    (x0, y0, z0), (x1, y1, z1) = frm, to
    if f in ("north", "south"):
        return x1 - x0, y1 - y0
    if f in ("east", "west"):
        return z1 - z0, y1 - y0
    return x1 - x0, z1 - z0


class _B:
    def __init__(self, a, b):
        self.frm, self.to = a, b


def build(out_dir):
    faces = []
    for ei, (frm, to, col, rot) in enumerate(ELS):
        for f in FACES:
            w, h = face_dims(frm, to, f)
            faces.append((max(1, math.ceil(h * DENSITY - 1e-6)), max(1, math.ceil(w * DENSITY - 1e-6)), ei, f))
    faces.sort(key=lambda t: (-t[0], -t[1]))
    size = 64
    while True:
        x = y = shelf = 0; placed = {}; ok = True
        for th, tw, ei, f in faces:
            if x + tw > size:
                x, y, shelf = 0, y + shelf + 1, 0
            if y + th > size:
                ok = False; break
            placed[(ei, f)] = (x, y, tw, th); x += tw + 1; shelf = max(shelf, th)
        if ok:
            break
        size *= 2
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0)); px = img.load()
    elements = []
    for ei, (frm, to, col, rot) in enumerate(ELS):
        b = _B(frm, to)
        el = {"from": [round(v, 4) for v in frm], "to": [round(v, 4) for v in to], "faces": {}}
        for f in FACES:
            x0, y0, tw, th = placed[(ei, f)]
            for j in range(th):
                for i in range(tw):
                    p = face_point(b, f, (i + 0.5) / tw, (j + 0.5) / th)
                    if rot:
                        p = fp_sim.element_rot(list(p), rot)
                    c = colour(col, p)
                    k = DIR[f]
                    px[x0 + i, y0 + j] = tuple(max(0, min(255, int(round(v * k)))) for v in c) + (255,)
            s = 16.0 / size
            fw, fh = face_dims(frm, to, f)       # UV 크기 = 실제 면 크기 × DENSITY (텍셀 밀도 균일, 작은 면은 한 텍셀 안)
            uw, vh = max(fw * DENSITY, 0.05), max(fh * DENSITY, 0.05)
            el["faces"][f] = {"uv": [round(x0 * s, 5), round(y0 * s, 5), round((x0 + uw) * s, 5), round((y0 + vh) * s, 5)], "texture": "#t"}
        if rot:
            el["rotation"] = rot
        elements.append(el)
    import pack_models
    model = {"textures": {"t": "violence:item/fire_axe", "particle": "violence:item/fire_axe"}, "elements": elements,
             "display": pack_models.MELEE_DISPLAY}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "fire_axe.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, separators=(",", ":"))
    img.save(os.path.join(out_dir, "fire_axe.png"))
    print(f"elements={len(elements)} tex={size}x{size}")


if __name__ == "__main__":
    build(os.path.join(HERE, "out"))
