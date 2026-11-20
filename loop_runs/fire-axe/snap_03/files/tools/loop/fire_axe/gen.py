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
    "glass":      (44, 46, 50),     # 유리섬유 자루
    "glass_dark": (34, 36, 40),
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
s = 0.25 * math.sqrt(2) * 1.15
for cx, cz in ((X0 + 0.25, Z0 + 0.25), (X1 - 0.25, Z0 + 0.25), (X0 + 0.25, Z1 - 0.25), (X1 - 0.25, Z1 - 0.25)):
    box([cx - s / 2, EY0, cz - s / 2], [cx + s / 2, EY1, cz + s / 2], "red", eul([cx, EY0, cz], y=45))
oct_y(CX, CZ, 0.8, 20.6, EY1 - 0.05, "glass_dark")  # 통 안으로 들어간 자루 (위에서 보임)

# ───────── 날: 칼날선 위 회전점으로 위/가운데/아래 3구역을 같은 단면으로 이음 (쐐기 4단) ─────────
ZE = 0.85                    # 칼날선 z
YB, YT = 21.6, 24.4          # 가운데 구역 (날 목 높이)
FL = 22.5                    # 위아래 구역이 벌어지는 각 = 날 곡선
H = 2.6                      # 위·아래 구역 높이
# (z0, z1, 반두께, 색): 날 끝 → 눈 쪽으로 두꺼워지는 쐐기
LAYERS = [(ZE, 1.6, 0.15, "ground"), (1.55, 3.0, 0.27, "ground"), (2.95, 4.9, 0.4, "red"), (4.85, 7.0, 0.52, "red")]
def section(y0, y1, rot):
    for z0, z1, hx, col in LAYERS:
        box([8 - hx, y0, z0], [8 + hx, y1, z1], col, rot)
    e = 0.25                 # 칼날선: 0.25 막대를 y축 45° → 마름모 단면
    r = dict(rot) if rot else {"origin": [8, y0, ZE], "x": 0, "y": 0, "z": 0}
    box([8 - e / 2, y0, ZE - e / 2], [8 + e / 2, y1, ZE + e / 2], "edge", {"origin": r["origin"], "x": r.get("x", 0), "y": 45, "z": 0})
section(YB, YT, None)
section(YT, YT + H, eul([8, YT, ZE], x=FL))           # 위: 날 끝이 뒤로 젖혀지며 위로 벌어짐
section(YB - H, YB, eul([8, YB, ZE], x=-FL))          # 아래

# ───────── 곡괭이 뿔 (+z): 정팔각 사슬, 마디마다 아래로 꺾이며 가늘어짐 ─────────
def oct_seg(cy, cz, ry, rx, L, ang, col):
    """(cy,cz)에서 시작해 +z 로 L, x축으로 ang° (양수=아래로) 꺾인 팔각 단면 마디. 끝점 반환"""
    rot = eul([8, cy, cz], x=ang) if ang else None
    c = min(rx, ry) * (1 - T)
    box([8 - rx, cy - ry + c, cz], [8 + rx, cy + ry - c, cz + L], col, rot)
    box([8 - rx + c, cy - ry, cz], [8 + rx - c, cy + ry, cz + L], col, rot)
    a = math.radians(ang)
    return cy - L * math.sin(a), cz + L * math.cos(a)
cy, cz = 23.0, Z1 - 0.15
for L, ry, rx, ang, col in ((2.0, 0.95, 0.62, 0, "red"), (1.7, 0.72, 0.46, 11.25, "red"),
                            (1.3, 0.5, 0.32, 22.5, "ground"), (0.75, 0.3, 0.2, 33.75, "ground"), (0.45, 0.14, 0.1, 45, "edge")):
    cy, cz = oct_seg(cy, cz - 0.05, ry, rx, L + 0.05, ang, col)


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
