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
    "edge":       (160, 168, 182),  # 칼날선 (윗면 V≈0.86, 푸른 기)
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

# ───────── 머리: 눈 (자루 끼우는 통) — 모든 모서리 45° 깎은 꽉 찬 블록 ─────────
def chamfer_box(frm, to, c, col):
    """모서리 12개를 45°로 깎은 상자: 안쪽으로 들인 상자 3개 + 모서리마다 45° 돌린 막대"""
    (x0, y0, z0), (x1, y1, z1) = frm, to
    box([x0, y0 + c, z0 + c], [x1, y1 - c, z1 - c], col)
    box([x0 + c, y0, z0 + c], [x1 - c, y1, z1 - c], col)
    box([x0 + c, y0 + c, z0], [x1 - c, y1 - c, z1], col)
    s_ = c * math.sqrt(2)
    h = s_ / 2
    for yy in (y0 + c, y1 - c):            # x축 방향 모서리 (위·아래, 앞·뒤)
        for zz in (z0 + c, z1 - c):
            box([x0 + c, yy - h, zz - h], [x1 - c, yy + h, zz + h], col, eul([x0 + c, yy, zz], x=45))
    for xx in (x0 + c, x1 - c):            # z축 방향 모서리
        for yy in (y0 + c, y1 - c):
            box([xx - h, yy - h, z0 + c], [xx + h, yy + h, z1 - c], col, eul([xx, yy, z0 + c], z=45))
    for xx in (x0 + c, x1 - c):            # y축 방향 모서리
        for zz in (z0 + c, z1 - c):
            box([xx - h, y0 + c, zz - h], [xx + h, y1 - c, zz + h], col, eul([xx, y0 + c, zz], y=45))

EY0, EY1 = 20.6, 25.4
X0, X1, Z0, Z1 = 7.05, 8.95, 6.75, 9.25
chamfer_box([X0, EY0, Z0], [X1, EY1, Z1], 0.2, "red")
oct_y(CX, CZ, 0.62, EY1, EY1 + 0.04, "glass_dark")   # 위로 보이는 자루 끝 (눈 윗면에만)

# ───────── 날: 칼날선 위 회전점으로 위/가운데/아래 3구역을 같은 단면으로 이음 (쐐기 4단) ─────────
ZE = 0.85                    # 칼날선 z
YB, YT = 21.6, 24.4          # 가운데 구역 (날 목 높이)
FL = 22.5                    # 위아래 구역이 벌어지는 각 = 날 곡선
H = 2.6                      # 위·아래 구역 높이
# (z0, z1, 반두께, 색): 날 끝 → 눈 쪽으로 두꺼워지는 쐐기
LAYERS = [(ZE, 1.6, 0.15, "ground"), (1.55, 3.0, 0.27, "ground"), (2.95, 4.9, 0.4, "red"), (4.85, 7.0, 0.52, "red")]
TH = math.tan(math.radians(FL / 2))        # 이음매를 꺾임각의 절반(이등분선)으로 맞춤
for z0, z1, hx, col in LAYERS:
    d1 = z1 - ZE
    m = d1 * TH
    box([8 - hx, YB + m, z0], [8 + hx, YT - m, z1], col)                                   # 가운데
    box([8 - hx, YT + m, z0], [8 + hx, YT + H, z1], col, eul([8, YT, ZE], x=FL))           # 위
    box([8 - hx, YB - H, z0], [8 + hx, YB - m, z1], col, eul([8, YB, ZE], x=-FL))          # 아래
    w = (d1 - (z0 - ZE)) * TH + 0.02                                                       # 이음매 메움 (이등분선 방향 띠)
    box([8 - hx, YT - w, z0], [8 + hx, YT + w, z1], col, eul([8, YT, ZE], x=FL / 2))
    box([8 - hx, YB - w, z0], [8 + hx, YB + w, z1], col, eul([8, YB, ZE], x=-FL / 2))
e = 0.25                                       # 칼날선: 0.25 막대를 y축 45° → 마름모 단면
for y0, y1, rx in ((YB, YT, 0), (YT, YT + H, FL), (YB - H, YB, -FL)):
    box([8 - e / 2, y0, ZE - e / 2], [8 + e / 2, y1, ZE + e / 2], "edge", eul([8, YT if rx > 0 else YB, ZE], x=rx, y=45))

# ───────── 곡괭이 뿔 (+z): 한 축(11.25° 아래로)을 따라 3단으로 가늘어지는 팔각 + 쐐기 끝 ─────────
PY, PZ, PA = 23.0, Z1 - 0.2, 11.25
PR = eul([8, PY, PZ], x=PA)
def pick_seg(z0, z1, ry, rx, col):
    c = min(rx, ry) * (1 - T)
    box([8 - rx, PY - ry + c, PZ + z0], [8 + rx, PY + ry - c, PZ + z1], col, PR)
    box([8 - rx + c, PY - ry, PZ + z0], [8 + rx - c, PY + ry, PZ + z1], col, PR)
pick_seg(0.0, 1.9, 0.92, 0.6, "red")
pick_seg(1.85, 3.4, 0.7, 0.46, "red")
pick_seg(3.35, 4.5, 0.48, 0.32, "ground")
# 쐐기 끝: 뿔 축 끝점에서 0.3 두께 판 두 장을 축 ±30°로 기울여 옆에서 보면 뾰족
_a = math.radians(PA)
QY, QZ = PY - 4.45 * math.sin(_a), PZ + 4.45 * math.cos(_a)
R_ = 0.3                     # 위·아래 판이 축 쪽으로 30° 모여 만나는 쐐기 (길이 2R)
for sgn in (1, -1):
    oy = QY + sgn * R_
    y0, y1 = (oy - 0.22, oy) if sgn > 0 else (oy, oy + 0.22)
    box([8 - 0.28, y0, QZ - 0.05], [8 + 0.28, y1, QZ + 2 * R_ / math.cos(math.radians(30)) * 0.5 + 0.1], "ground",
        eul([8, oy, QZ - 0.05], x=PA + sgn * 30))

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
