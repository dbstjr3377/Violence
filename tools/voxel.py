"""
복셀 모델 도구 (마인크래프트 아이템 모델 JSON + 모델별 텍스처 아틀라스).

- 상자(element)마다 재질(material)을 정하면, 각 면의 텍스처를 아틀라스에 자동 배치하고
  재질 질감(노이즈, 결, 가장자리 음영, 윗면 하이라이트)을 그려 넣는다.
- painter 함수로 면 위의 3D 좌표 → 색을 지정해 눈, 이빨, 줄무늬, 각인 같은 무늬를 그릴 수 있다.
- UV 는 마인크래프트 기본 방향 규칙을 따르므로 칠한 그대로 게임에 보인다.
"""
import math
import random

from PIL import Image

FACES = ("north", "south", "east", "west", "up", "down")


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def shade(c, k):
    return tuple(clamp(v * k) for v in c[:3])


def hnoise(x, y, z, seed=0):
    """위치 기반 결정적 노이즈 0..1"""
    h = (int(x * 73856093) ^ int(y * 19349663) ^ int(z * 83492791) ^ (seed * 2654435761)) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


# ───────────────────────── 재질 ─────────────────────────

class Material:
    def __init__(self, base, noise=0.06, edge=0.78, top=1.10, grain=None, grain_amp=0.0, spec=None, check=0.0, rough=1.0):
        self.base = base
        self.noise = noise
        self.edge = edge          # 가장자리 어둡게
        self.top = top            # 위쪽 가장자리 밝게
        self.grain = grain        # 'x','y','z' 결 방향 (나무, 브러시드 금속)
        self.grain_amp = grain_amp
        self.spec = spec          # 반사 줄무늬 색
        self.check = check        # 체크무늬(그립) 강도
        self.rough = rough
        self.seed_base = 7

    def color(self, p, fu, fv, edge_dist, seed):
        """면 질감. 위치 기반이라 이웃한 상자끼리 무늬가 이어지며, 상자마다 외곽선을 그리지 않는다."""
        x, y, z = p
        q = 4.0
        n = (hnoise(math.floor(x * q), math.floor(y * q), math.floor(z * q), self.seed_base) - 0.5) * 2 * self.noise
        k = 1.0 + n
        if self.grain:
            g = {"x": x, "y": y, "z": z}[self.grain]
            other = (y + z) if self.grain == "x" else ((x + z) if self.grain == "y" else (x + y))
            k += math.sin(g * 1.7 + math.sin(other * 3.1) * 1.3) * self.grain_amp
        if self.check:
            cu = math.floor((x + z) * 2) % 2
            cv = math.floor(y * 2) % 2
            k += self.check * (0.5 if cu ^ cv else -0.5)
        c = shade(self.base, k)
        return tuple(clamp(v) for v in c) + (255,)


MAT = {
    # 총기
    "gunmetal": Material((58, 61, 68), noise=0.05, spec=(120, 126, 136)),
    "blued": Material((44, 48, 62), noise=0.05, spec=(110, 120, 150)),
    "anodized": Material((48, 50, 52), noise=0.04),
    "polymer": Material((34, 34, 36), noise=0.07, edge=0.7),
    "polymer_tan": Material((150, 128, 96), noise=0.07),
    "steel": Material((150, 154, 162), noise=0.04, grain="z", grain_amp=0.04, spec=(220, 224, 232)),
    "chrome": Material((190, 194, 202), noise=0.03, grain="z", grain_amp=0.06, spec=(250, 250, 255)),
    "dark_steel": Material((80, 84, 92), noise=0.05, spec=(140, 146, 156)),
    "wood": Material((122, 74, 40), noise=0.05, grain="z", grain_amp=0.10),
    "wood_dark": Material((84, 48, 28), noise=0.05, grain="z", grain_amp=0.10),
    "wood_light": Material((176, 128, 80), noise=0.05, grain="z", grain_amp=0.10),
    "wood_y": Material((132, 84, 46), noise=0.05, grain="y", grain_amp=0.11),
    "wood_light_y": Material((182, 136, 86), noise=0.05, grain="y", grain_amp=0.10),
    "wood_dark_y": Material((88, 52, 30), noise=0.05, grain="y", grain_amp=0.10),
    "rubber": Material((28, 27, 27), noise=0.08, check=0.18, edge=0.75),
    "grip": Material((40, 38, 36), noise=0.06, check=0.25),
    "brass": Material((196, 158, 68), noise=0.05, spec=(250, 230, 150)),
    "gold": Material((220, 180, 70), noise=0.04, spec=(255, 240, 170)),
    "black": Material((22, 22, 24), noise=0.05, edge=0.7),
    "white": Material((236, 236, 236), noise=0.03, edge=0.86),
    "red_paint": Material((176, 30, 34), noise=0.06, spec=(230, 90, 90)),
    "red_dark": Material((112, 18, 24), noise=0.06),
    "leather": Material((96, 58, 36), noise=0.08, edge=0.7),
    "leather_dark": Material((58, 34, 22), noise=0.08, edge=0.7),
    "cloth_black": Material((30, 28, 34), noise=0.10, check=0.22),
    "tape": Material((60, 60, 64), noise=0.10, grain="y", grain_amp=0.08),
    "blade": Material((196, 202, 210), noise=0.03, grain="y", grain_amp=0.05, spec=(250, 252, 255), edge=0.9),
    "blade_dark": Material((120, 126, 134), noise=0.04, grain="y", grain_amp=0.05),
    "glass_green": Material((40, 120, 60), noise=0.05, spec=(140, 220, 160), edge=0.85),
    "glass_brown": Material((110, 60, 22), noise=0.05, spec=(200, 140, 80), edge=0.85),
    "paper": Material((232, 222, 196), noise=0.04),
    "brick": Material((156, 62, 44), noise=0.14, edge=0.72),
    "foam": Material((26, 26, 28), noise=0.12, check=0.12),
    "blue_chalk": Material((60, 110, 200), noise=0.05),
    "ivory": Material((236, 230, 210), noise=0.04),
    "silver": Material((170, 174, 182), noise=0.03, spec=(240, 240, 248)),
}


def flat(rgb, noise=0.05, edge=0.82, top=1.06):
    return Material(rgb, noise=noise, edge=edge, top=top)


# ───────────────────────── 모델 ─────────────────────────

class Box:
    def __init__(self, frm, to, mat, rot=None, painter=None, faces=None, light=False):
        self.frm = [float(v) for v in frm]
        self.to = [float(v) for v in to]
        self.mat = MAT[mat] if isinstance(mat, str) else mat
        self.rot = rot
        self.painter = painter
        self.faces = faces or FACES
        self.light = light


def face_dims(b, f):
    (x0, y0, z0), (x1, y1, z1) = b.frm, b.to
    if f in ("north", "south"):
        return x1 - x0, y1 - y0
    if f in ("east", "west"):
        return z1 - z0, y1 - y0
    return x1 - x0, z1 - z0


def face_point(b, f, fu, fv):
    """면 위 정규화 좌표(fu: 왼→오, fv: 위→아래, 바깥에서 볼 때) → 3D 좌표"""
    (x0, y0, z0), (x1, y1, z1) = b.frm, b.to
    if f == "north":
        return (x1 - (x1 - x0) * fu, y1 - (y1 - y0) * fv, z0)
    if f == "south":
        return (x0 + (x1 - x0) * fu, y1 - (y1 - y0) * fv, z1)
    if f == "east":
        return (x1, y1 - (y1 - y0) * fv, z1 - (z1 - z0) * fu)
    if f == "west":
        return (x0, y1 - (y1 - y0) * fv, z0 + (z1 - z0) * fu)
    if f == "up":
        return (x0 + (x1 - x0) * fu, y1, z0 + (z1 - z0) * fv)
    return (x0 + (x1 - x0) * fu, y0, z1 - (z1 - z0) * fv)  # down


class Model:
    def __init__(self, name, tex_size=256, density=4, seed=0, auto_round=0.0):
        self.name = name
        self.auto_round = auto_round
        self.boxes = []
        self.tex_size = tex_size
        self.density = density
        self.seed = seed

    def box(self, frm, to, mat, rot=None, painter=None, faces=None, light=False):
        r = self.auto_round
        dims = [to[i] - frm[i] for i in range(3)]
        if r > 0 and faces is None and not light and min(dims) >= r * 3.2:
            # 모서리를 깎아 둥글게 (상자 3개)
            (x0, y0, z0), (x1, y1, z1) = frm, to
            e = 0.015
            self.boxes.append(Box([x0, y0 + r, z0 + r], [x1, y1 - r, z1 - r], mat, rot, painter, None, False))
            self.boxes.append(Box([x0 + r, y0, z0 + r + e], [x1 - r, y1, z1 - r - e], mat, rot, painter, None, False))
            self.boxes.append(Box([x0 + r + e, y0 + r + e, z0], [x1 - r - e, y1 - r - e, z1], mat, rot, painter, None, False))
            return self
        self.boxes.append(Box(frm, to, mat, rot, painter, faces, light))
        return self

    def add(self, other):
        self.boxes.extend(other.boxes)
        return self

    def build(self, tex_ref):
        """(model_json, texture_image) 반환"""
        size = self.tex_size
        while True:
            try:
                return self._build(tex_ref, size)
            except OverflowError:
                if size >= 1024:
                    raise
                size *= 2
                self.density = self.density  # 밀도 유지, 아틀라스만 키움

    def _build(self, tex_ref, size):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = img.load()
        d = self.density
        # 면 목록 (큰 것부터 배치)
        faces = []
        for bi, b in enumerate(self.boxes):
            for f in b.faces:
                w, h = face_dims(b, f)
                tw, th = max(1, int(math.ceil(w * d - 1e-6))), max(1, int(math.ceil(h * d - 1e-6)))
                faces.append((th, tw, bi, f))
        faces.sort(key=lambda t: (-t[0], -t[1]))
        # 선반 배치
        x = y = shelf = 0
        placed = {}
        for th, tw, bi, f in faces:
            if x + tw > size:
                x, y, shelf = 0, y + shelf, 0
            if y + th > size:
                raise OverflowError
            placed[(bi, f)] = (x, y, tw, th)
            x += tw
            shelf = max(shelf, th)
        rnd = random.Random(self.seed)
        elements = []
        for bi, b in enumerate(self.boxes):
            el = {"from": [round(v, 4) for v in b.frm], "to": [round(v, 4) for v in b.to], "faces": {}}
            for f in b.faces:
                x0, y0, tw, th = placed[(bi, f)]
                for j in range(th):
                    for i in range(tw):
                        fu, fv = (i + 0.5) / tw, (j + 0.5) / th
                        p = face_point(b, f, fu, fv)
                        edge = min(i, j, tw - 1 - i, th - 1 - j)
                        col = None
                        if b.painter:
                            col = b.painter(f, p, fu, fv)
                        if col is None:
                            col = b.mat.color(p, fu, fv, edge, 0)
                        elif len(col) == 3:
                            col = tuple(clamp(v) for v in col) + (255,)
                        px[x0 + i, y0 + j] = col
                k = 16.0 / size
                el["faces"][f] = {"uv": [round(x0 * k, 5), round(y0 * k, 5), round((x0 + tw) * k, 5), round((y0 + th) * k, 5)], "texture": "#t"}
            if b.rot:
                el["rotation"] = b.rot
            if b.light:
                el["light_emission"] = 15
            elements.append(el)
        _ = rnd
        model = {"textures": {"t": tex_ref, "particle": tex_ref}, "elements": elements}
        # 사용한 영역만 남기도록 높이를 줄이지는 않음 (정사각형 유지)
        return model, img


def rbox(m, frm, to, r, mat, painter=None, rot_=None):
    """모서리를 깎은 상자 (상자 3개). 겹치는 면은 살짝 안쪽으로 물려 깜빡임이 없게 한다."""
    (x0, y0, z0), (x1, y1, z1) = frm, to
    r = min(r, (x1 - x0) / 2.01, (y1 - y0) / 2.01, (z1 - z0) / 2.01)
    e = 0.02
    m.box([x0, y0 + r, z0 + r], [x1, y1 - r, z1 - r], mat, painter=painter, rot=rot_)
    m.box([x0 + r, y0, z0 + r + e], [x1 - r, y1, z1 - r - e], mat, painter=painter, rot=rot_)
    m.box([x0 + r + e, y0 + r + e, z0], [x1 - r - e, y1 - r - e, z1], mat, painter=painter, rot=rot_)
    return m


def rot(axis, angle, origin):
    return {"axis": axis, "angle": angle, "origin": list(origin)}


def octagon_rod(m, axis, c1, c2, r, start, end, mat, painter=None):
    """축 방향 원통 근사 (단면 팔각형 = 상자 2개)"""
    a = r
    b = r * 0.5
    c = r * 0.8
    if axis == "z":
        m.box([c1 - a, c2 - b, start], [c1 + a, c2 + b, end], mat, painter=painter)
        m.box([c1 - b, c2 - a, start], [c1 + b, c2 + a, end], mat, painter=painter)
        m.box([c1 - c, c2 - c, start], [c1 + c, c2 + c, end], mat, painter=painter)
    elif axis == "y":
        m.box([c1 - a, start, c2 - b], [c1 + a, end, c2 + b], mat, painter=painter)
        m.box([c1 - b, start, c2 - a], [c1 + b, end, c2 + a], mat, painter=painter)
        m.box([c1 - c, start, c2 - c], [c1 + c, end, c2 + c], mat, painter=painter)
    else:
        m.box([start, c1 - a, c2 - b], [end, c1 + a, c2 + b], mat, painter=painter)
        m.box([start, c1 - b, c2 - a], [end, c1 + b, c2 + a], mat, painter=painter)
    return m


def disc(m, axis, cx, cy, cz, r, thick, mat, painter=None):
    """원판 근사 (팔각형)"""
    b = r * 0.42
    t = thick / 2
    if axis == "x":
        m.box([cx - t, cy - r, cz - b], [cx + t, cy + r, cz + b], mat, painter=painter)
        m.box([cx - t, cy - b, cz - r], [cx + t, cy + b, cz + r], mat, painter=painter)
        m.box([cx - t, cy - r * 0.78, cz - r * 0.78], [cx + t, cy + r * 0.78, cz + r * 0.78], mat, painter=painter)
    elif axis == "y":
        m.box([cx - r, cy - t, cz - b], [cx + r, cy + t, cz + b], mat, painter=painter)
        m.box([cx - b, cy - t, cz - r], [cx + b, cy + t, cz + r], mat, painter=painter)
        m.box([cx - r * 0.78, cy - t, cz - r * 0.78], [cx + r * 0.78, cy + t, cz + r * 0.78], mat, painter=painter)
    else:
        m.box([cx - r, cy - b, cz - t], [cx + r, cy + b, cz + t], mat, painter=painter)
        m.box([cx - b, cy - r, cz - t], [cx + b, cy + r, cz + t], mat, painter=painter)
        m.box([cx - r * 0.78, cy - r * 0.78, cz - t], [cx + r * 0.78, cy + r * 0.78, cz + t], mat, painter=painter)
    return m
