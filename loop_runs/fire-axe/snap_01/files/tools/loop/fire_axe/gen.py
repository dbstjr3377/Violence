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
    "red":        (142, 36, 34),
    "red_dark":   (104, 26, 26),
    "steel":      (150, 154, 160),
    "steel_dark": (96, 100, 106),
    "edge":       (206, 212, 222),
    "wood":       (122, 78, 48),
    "wood_end":   (92, 58, 36),
    "rubber":     (36, 36, 38),
    "rubber_rib": (52, 52, 56),
    "pin":        (70, 72, 76),
}

ELS = []   # (frm, to, colour_or_fn, rotation)


def box(frm, to, col, rot=None):
    ELS.append(([float(v) for v in frm], [float(v) for v in to], col, rot))


def eul(origin, x=0, y=0, z=0):
    return {"origin": [round(v, 4) for v in origin], "x": x, "y": y, "z": z}


def chamfer_y(x0, x1, z0, z1, y0, y1, c, col):
    """y축 기둥, 세로 모서리 4개를 45°로 깎음 (상자 2개 + 45° 회전 막대 4개)"""
    box([x0, y0, z0 + c], [x1, y1, z1 - c], col)
    box([x0 + c, y0, z0], [x1 - c, y1, z1], col)
    s = c * math.sqrt(2)
    for cx, cz in ((x0 + c, z0 + c), (x1 - c, z0 + c), (x0 + c, z1 - c), (x1 - c, z1 - c)):
        box([cx - s / 2, y0, cz - s / 2], [cx + s / 2, y1, cz + s / 2], col, eul([cx, y0, cz], y=45))


def chamfer_z(x0, x1, y0, y1, z0, z1, c, col, rot=None):
    """z축 기둥, 모서리 4개를 45°로 깎음. rot 이 있으면 전체에 같은 회전을 줌 (막대는 근사)"""
    box([x0, y0 + c, z0], [x1, y1 - c, z1], col, rot)
    box([x0 + c, y0, z0], [x1 - c, y1, z1], col, rot)


def oct_y(cx, cz, r, y0, y1, col):
    """정팔각 단면 원통 (y축): 정사각 + 45° 돌린 정사각"""
    a = r * math.cos(math.radians(22.5))
    box([cx - a, y0, cz - a], [cx + a, y1, cz + a], col)
    box([cx - a, y0, cz - a], [cx + a, y1, cz + a], col, eul([cx, y0, cz], y=45))


def oct_x(cy, cz, r, x0, x1, col):
    a = r * math.cos(math.radians(22.5))
    box([x0, cy - a, cz - a], [x1, cy + a, cz + a], col)
    box([x0, cy - a, cz - a], [x1, cy + a, cz + a], col, eul([x0, cy, cz], x=45))


# ───────── 손잡이 (히코리 원목, 팔각 단면, 아래 손잡이 고무 슬리브) ─────────
CX = CZ = 8.0
oct_y(CX, CZ, 1.05, 0.0, 0.5, "wood_end")          # 끝 마구리
oct_y(CX, CZ, 1.12, 0.5, 1.3, "wood")              # 스웰(손잡이 끝 불룩)
oct_y(CX, CZ, 0.98, 1.3, 7.6, "rubber")            # 고무 슬리브
for i in range(7):                                  # 미끄럼 방지 마디
    y = 1.8 + i * 0.8
    oct_y(CX, CZ, 1.06, y, y + 0.22, "rubber_rib")
oct_y(CX, CZ, 1.04, 7.6, 7.9, "rubber_rib")        # 슬리브 끝 테두리
oct_y(CX, CZ, 0.86, 7.9, 20.4, "wood")             # 자루
oct_y(CX, CZ, 0.92, 19.4, 20.6, "wood")            # 머리 아래 살짝 굵어짐

# ───────── 머리: 눈(자루 끼우는 구멍) ─────────
EY0, EY1 = 20.6, 25.4
chamfer_y(7.05, 8.95, 6.7, 9.3, EY0, EY1, 0.25, "red")
box([7.2, EY1, 7.05], [8.8, EY1 + 0.06, 8.95], "wood_end")     # 위로 보이는 자루 끝
box([7.92, EY1 + 0.02, 7.1], [8.08, EY1 + 0.08, 8.9], "steel_dark")  # 쐐기
oct_x(23.0, 8.0, 0.32, 6.95, 9.05, "pin")           # 고정 핀


# ───────── 날 ─────────
GROUND_Z = 2.5   # 이보다 앞(−z)은 연마된 강철 띠
def blade_col(p):
    return "steel" if p[2] < GROUND_Z else "red"

BX0, BX1 = 7.45, 8.55            # 날 몸통 두께
box([BX0, 21.4, 1.2], [BX1, 24.6, 6.8], blade_col)
# 위·아래로 벌어지는 부분 (24° 기울인 판)
box([BX0, 22.6, 1.2], [BX1, 24.6, 6.8], blade_col, eul([8, 24.6, 6.8], x=24))
box([BX0, 21.4, 1.2], [BX1, 23.4, 6.8], blade_col, eul([8, 21.4, 6.8], x=-24))
# 2차 연마면 (더 얇은 판) + 칼날선 (45° 돌린 막대 = 마름모 단면)
for (y0, y1, ang, oy) in ((21.0, 25.0, 0, None), (24.4, 26.6, -12, 24.6), (19.4, 21.6, 12, 21.4)):
    rot = eul([8, oy, 1.2], x=ang) if ang else None
    box([7.68, y0, 0.55], [8.32, y1, 1.25], "edge", rot)
    s = 0.36
    box([8 - s / 2, y0, 0.55 - s / 2], [8 + s / 2, y1, 0.55 + s / 2], "edge",
        eul([8, oy if oy else y0, 0.55], x=ang, y=45) if ang else eul([8, y0, 0.55], y=45))

# ───────── 곡괭이 뿔 (+z, 끝으로 갈수록 가늘고 살짝 아래로) ─────────
segs = [(9.3, 11.0, 0.62, 0.95, 4, "red"), (11.0, 12.6, 0.48, 0.72, 8, "red"), (12.6, 13.8, 0.34, 0.5, 13, "steel"), (13.8, 14.6, 0.2, 0.28, 18, "steel")]
for z0, z1, hx, hy, ang, col in segs:
    chamfer_z(8 - hx, 8 + hx, 23.0 - hy, 23.0 + hy, z0 - 0.15, z1, min(hx, hy) * 0.35, col, eul([8, 23.0, 9.3], x=ang))


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
