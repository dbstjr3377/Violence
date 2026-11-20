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
DIR = {"up": 1.20, "north": 1.04, "east": 1.0, "west": 0.95, "south": 0.88, "down": 0.78}

PAL = {
    "red":        (92, 40, 38),     # 탁한 적색 도장
    "red_top":    (92, 40, 38),
    "steel":      (112, 118, 126),  # 청회색 강철
    "ground":     (138, 144, 154),  # 연마면
    "edge":       (182, 192, 206),  # 칼날선 (V≈0.81, 푸른 기)
    "glass":      (60, 62, 66),     # 유리섬유 자루
    "glass_dark": (46, 48, 52),
    "rubber":     (30, 30, 32),
    "rubber_rib": (40, 40, 43),
    "cap":        (52, 54, 58),
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
oct_y(CX, CZ, 0.95, 0.0, 0.35, "cap")              # 끝 마개
oct_y(CX, CZ, 1.05, 0.35, 1.1, "rubber")           # 손잡이 끝 불룩
oct_y(CX, CZ, 0.92, 1.1, 7.6, "rubber")            # 고무 손잡이
for i in range(6):                                  # 미끄럼 방지 마디
    y = 1.9 + i * 0.9
    oct_y(CX, CZ, 0.99, y, y + 0.3, "rubber_rib")
oct_y(CX, CZ, 0.98, 7.6, 7.95, "rubber_rib")       # 손잡이 끝 테두리
oct_y(CX, CZ, 0.8, 7.95, 20.7, "glass")            # 자루

# ───────── 머리: 눈 (자루 끼우는 통, 얇은 벽판 4장 + 45° 모서리) ─────────
EY0, EY1 = 20.6, 25.4
X0, X1, Z0, Z1, W = 7.05, 8.95, 6.75, 9.25, 0.42
box([X0, EY0, Z0 + 0.25], [X0 + W, EY1, Z1 - 0.25], "red")          # 서쪽 벽
box([X1 - W, EY0, Z0 + 0.25], [X1, EY1, Z1 - 0.25], "red")          # 동쪽 벽
box([X0 + 0.25, EY0, Z0], [X1 - 0.25, EY1, Z0 + W], "red")          # 앞 벽 (날 쪽)
box([X0 + 0.25, EY0, Z1 - W], [X1 - 0.25, EY1, Z1], "red")          # 뒤 벽 (뿔 쪽)
s = 0.25 * math.sqrt(2)
for cx, cz in ((X0 + 0.25, Z0 + 0.25), (X1 - 0.25, Z0 + 0.25), (X0 + 0.25, Z1 - 0.25), (X1 - 0.25, Z1 - 0.25)):
    box([cx - s / 2, EY0, cz - s / 2], [cx + s / 2, EY1, cz + s / 2], "red", eul([cx, EY0, cz], y=45))
oct_y(CX, CZ, 0.8, 20.6, EY1 - 0.05, "glass_dark")  # 통 안으로 들어간 자루 (위에서 보임)

# ───────── 날: 단색 면, 베벨은 판 두께 단계로, 칼날선은 45° 막대 ─────────
NECK_Y0, NECK_Y1, NZ = 21.5, 24.5, 6.8     # 날 목 (눈과 붙는 곳)
ZS, ZG, ZE = 3.0, 1.55, 0.85               # 도장/연마 경계, 2차 연마, 칼날선 z
FL = 22.5                                   # 날 위아래로 벌어지는 각
def plate(z0, z1, hx, col, y0=NECK_Y0, y1=NECK_Y1):
    box([8 - hx, y0, z0], [8 + hx, y1, z1], col)
def flare(z0, z1, hx, col, h=1.6):
    box([8 - hx, NECK_Y1 - h, z0], [8 + hx, NECK_Y1, z1], col, eul([8, NECK_Y1, NZ], x=FL))
    box([8 - hx, NECK_Y0, z0], [8 + hx, NECK_Y0 + h, z1], col, eul([8, NECK_Y0, NZ], x=-FL))
# 도장된 볼 (두께 0.9)
plate(ZS, NZ, 0.45, "red"); flare(ZS, NZ, 0.45, "red")
# 1차 연마 (두께 0.6)
plate(ZG, ZS, 0.30, "ground"); flare(ZG, ZS, 0.30, "ground")
# 위아래 끝에서 벌어진 판이 닿는 높이
TOP = NECK_Y1 + (NZ - ZG) * math.tan(math.radians(FL))
BOT = NECK_Y0 - (NZ - ZG) * math.tan(math.radians(FL))
# 2차 연마 (두께 0.36) — 한 장으로 위아래 끝까지
box([8 - 0.18, BOT + 0.35, ZE], [8 + 0.18, TOP - 0.35, ZG + 0.05], "ground")
# 칼날선: 0.25 사각 막대를 45° 돌려 마름모 단면 (폭 0.177×√2)
e = 0.25
box([8 - e / 2, BOT + 0.5, ZE - e / 2], [8 + e / 2, TOP - 0.5, ZE + e / 2], "edge", eul([8, BOT + 0.5, ZE], y=45))
# 날 위·아래 뾰족한 끝 (45° 깎은 모서리)
for yy, ang in ((TOP - 0.5, 45), (BOT + 0.5, -45)):
    box([8 - 0.18, yy - 0.3, ZE], [8 + 0.18, yy + 0.3, ZE + 0.6], "ground", eul([8, yy, ZE], x=ang))

# ───────── 곡괭이 뿔 (+z): 22.5° 아래로 꺾인 2단 테이퍼 + 45° 깎은 끝 ─────────
PY = 23.0
oct_z(8, PY, 0.62, 0.95, Z1 - 0.1, 11.6, "red")
oct_z(8, PY, 0.42, 0.62, 11.4, 13.4, "red", eul([8, PY, 11.4], x=22.5))
oct_z(8, PY, 0.26, 0.36, 11.4 + 1.9, 11.4 + 2.9, "steel", eul([8, PY, 11.4], x=22.5))
box([8 - 0.12, PY - 0.12, 14.2], [8 + 0.12, PY + 0.12, 14.6], "ground", eul([8, PY, 11.4], x=22.5))


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
            el["faces"][f] = {"uv": [round(x0 * s, 5), round(y0 * s, 5), round((x0 + tw) * s, 5), round((y0 + th) * s, 5)], "texture": "#t"}
        if rot:
            el["rotation"] = rot
        elements.append(el)
    model = {"textures": {"t": "violence:item/fire_axe", "particle": "violence:item/fire_axe"}, "elements": elements}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "fire_axe.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, separators=(",", ":"))
    img.save(os.path.join(out_dir, "fire_axe.png"))
    print(f"elements={len(elements)} tex={size}x{size}")


if __name__ == "__main__":
    build(os.path.join(HERE, "out"))
