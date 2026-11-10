"""
가면 제작 도구 (Blockbench 형식).

- 가면 = 상자(Part) 몇 개 + 칠하기 함수. 상자 면마다 텍셀(1단위 = 2px)을 칠해 텍스처 아틀라스를 만든다.
- 잡티 없음: 무작위 노이즈를 쓰지 않고, 정해 둔 모양(눈, 줄무늬, 반점)만 단색으로 칠한다.
  check_speckles() 가 주변 4칸과 모두 다른 외톨이 픽셀을 센다 (0 이어야 함).
- 결과: Java 아이템 모델(JSON) + PNG, 그리고 Blockbench 에서 바로 열 수 있는 .bbmodel (텍스처 포함).
좌표: 머리 0~16 (마인크래프트 머리), 얼굴 = -Z (north).
"""
import base64
import io
import json
import math
import os
import uuid

from PIL import Image

DENSITY = 2          # 1 모델 단위 = 2 텍셀
BLACK = (14, 12, 16)

# 면 → 바깥에서 볼 때 (왼위, 오른위, 왼아래) 꼭짓점 (fp_sim 과 같은 규칙 = 게임과 같은 UV 방향)
CORNERS = {
    "north": lambda a, b: ((b[0], b[1], a[2]), (a[0], b[1], a[2]), (b[0], a[1], a[2])),
    "south": lambda a, b: ((a[0], b[1], b[2]), (b[0], b[1], b[2]), (a[0], a[1], b[2])),
    "east": lambda a, b: ((b[0], b[1], b[2]), (b[0], b[1], a[2]), (b[0], a[1], b[2])),
    "west": lambda a, b: ((a[0], b[1], a[2]), (a[0], b[1], b[2]), (a[0], a[1], a[2])),
    "up": lambda a, b: ((a[0], b[1], a[2]), (b[0], b[1], a[2]), (a[0], b[1], b[2])),
    "down": lambda a, b: ((a[0], a[1], b[2]), (b[0], a[1], b[2]), (a[0], a[1], a[2])),
}


class Part:
    """상자 하나. paint(x, y, z, face) → (r,g,b) 또는 None(기본색). rot: {'axis','angle','origin'}"""

    def __init__(self, frm, to, color, paint=None, rot=None, name="part", faces=None):
        self.frm = [float(v) for v in frm]
        self.to = [float(v) for v in to]
        self.color = tuple(color)
        self.paint = paint
        self.rot = rot
        self.name = name
        self.faces = faces or list(CORNERS)


class Mask:
    def __init__(self, name):
        self.name = name
        self.parts = []

    def add(self, frm, to, color, paint=None, rot=None, name=None, faces=None):
        self.parts.append(Part(frm, to, color, paint, rot, name or f"p{len(self.parts)}", faces))
        return self


# ───────────────────────── 칠하기 도우미 ─────────────────────────

def layers(*painters):
    """앞의 칠하기가 우선 (None 이면 다음 것)"""
    def p(x, y, z, f):
        for q in painters:
            if q is None:
                continue
            c = q(x, y, z, f)
            if c is not None:
                return c
        return None
    return p


def on_faces(faces, painter):
    def p(x, y, z, f):
        return painter(x, y, z, f) if f in faces else None
    return p


def eye(cx, cy, rx, ry, tilt=0.0, color=BLACK, faces=("north",), cut_top=None):
    """정면 눈 (검은 구멍). tilt: 바깥쪽 눈꼬리가 올라간 정도 (+ = 바깥이 위). cx 가 8 보다 작으면 오른쪽 눈.
    타원을 기울이고, cut_top 이면 위를 비스듬히 잘라 화난 눈매 (눈가가 올라간 가면만)."""
    side = 1 if cx > 8 else -1      # 화면 기준 +x 쪽 눈이면 바깥 = +x

    def p(x, y, z, f):
        if f not in faces:
            return None
        dx, dy = x - cx, y - cy
        a = math.radians(tilt) * side
        u = dx * math.cos(a) + dy * math.sin(a)
        v = -dx * math.sin(a) + dy * math.cos(a)
        if (u / rx) ** 2 + (v / ry) ** 2 > 1:
            return None
        if cut_top is not None:
            # 안쪽(코 쪽)이 낮고 바깥이 높은 눈썹 선 아래만
            line = cy + ry * cut_top + (x - cx) * side * 0.45
            if y > line:
                return None
        return color
    return p


def side_eye(cy, cz, ry, rz, color=BLACK):
    """옆면 눈 (말·기린·낙타처럼 눈이 옆에 붙은 동물)"""
    def p(x, y, z, f):
        if f not in ("east", "west"):
            return None
        return color if ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1 else None
    return p


def ellipse(cx, cy, rx, ry, color, faces=("north",), axes="xy"):
    def p(x, y, z, f):
        if f not in faces:
            return None
        a, b = {"xy": (x, y), "zy": (z, y), "xz": (x, z)}[axes]
        return color if ((a - cx) / rx) ** 2 + ((b - cy) / ry) ** 2 <= 1 else None
    return p


def rect(x0, y0, x1, y1, color, faces=("north",), axes="xy"):
    def p(x, y, z, f):
        if f not in faces:
            return None
        a, b = {"xy": (x, y), "zy": (z, y), "xz": (x, z)}[axes]
        return color if x0 <= a <= x1 and y0 <= b <= y1 else None
    return p


def stripes(color, period, width, angle_deg=0.0, wobble=0.0, faces=None, offset=0.0):
    """매끈한 줄무늬 (호랑이·얼룩말). 무작위 없이 사인 굴곡만"""
    a = math.radians(angle_deg)

    def p(x, y, z, f):
        if faces and f not in faces:
            return None
        t = y * math.cos(a) + (x + z) * 0.5 * math.sin(a) + wobble * math.sin((x + z) * 0.55)
        return color if (t + offset) % period < width else None
    return p


def spots(points, r, color, faces=None):
    """정해진 자리의 둥근 반점 (기린). points: [(x, y, z)]"""
    def p(x, y, z, f):
        if faces and f not in faces:
            return None
        for (sx, sy, sz) in points:
            if (x - sx) ** 2 + (y - sy) ** 2 + (z - sz) ** 2 <= r * r:
                return color
        return None
    return p


def shade(color, k):
    return tuple(max(0, min(255, int(round(c * k)))) for c in color)


# ───────────────────────── 빌드 ─────────────────────────

def _face_texels(part, face):
    a, b = part.frm, part.to
    tl, tr, bl = CORNERS[face](a, b)
    w = math.dist(tl, tr)
    h = math.dist(tl, bl)
    nu = max(1, int(round(w * DENSITY)))
    nv = max(1, int(round(h * DENSITY)))
    img = Image.new("RGBA", (nu, nv))
    px = img.load()
    for j in range(nv):
        for i in range(nu):
            fu, fv = (i + 0.5) / nu, (j + 0.5) / nv
            pt = [tl[k] + (tr[k] - tl[k]) * fu + (bl[k] - tl[k]) * fv for k in range(3)]
            c = part.paint(*pt, face) if part.paint else None
            c = c or part.color
            px[i, j] = (*c[:3], 255)
    return img


def build(mask, display):
    """→ (java 모델 dict, 아틀라스 Image, 면별 텍스처 [(part, face, img, (x, y))])"""
    tiles = []
    for part in mask.parts:
        for face in part.faces:
            tiles.append((part, face, _face_texels(part, face)))
    # 선반 배치 (큰 것부터)
    order = sorted(range(len(tiles)), key=lambda i: (-tiles[i][2].height, -tiles[i][2].width))
    size = 64
    while True:
        x = y = shelf = 0
        pos = {}
        ok = True
        for i in order:
            img = tiles[i][2]
            if x + img.width > size:
                x, y, shelf = 0, y + shelf, 0
            if y + img.height > size or img.width > size:
                ok = False
                break
            pos[i] = (x, y)
            x += img.width
            shelf = max(shelf, img.height)
        if ok:
            break
        size *= 2
    atlas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    placed = []
    for i, (part, face, img) in enumerate(tiles):
        atlas.paste(img, pos[i])
        placed.append((part, face, img, pos[i]))
    elements = {}
    for part, face, img, (px_, py_) in placed:
        el = elements.setdefault(id(part), {"name": part.name, "from": part.frm, "to": part.to, "faces": {}})
        if part.rot:
            el["rotation"] = part.rot
        s = 16 / size
        el["faces"][face] = {"uv": [round(px_ * s, 4), round(py_ * s, 4), round((px_ + img.width) * s, 4), round((py_ + img.height) * s, 4)],
                             "texture": "#t"}
    model = {"elements": [elements[id(p)] for p in mask.parts], "display": display}
    return model, atlas, placed


def check_speckles(placed):
    """면 안에서 위·아래·좌·우 4칸과 모두 다른 외톨이 픽셀 수 (잡티)"""
    total = 0
    where = []
    for part, face, img, _ in placed:
        px = img.load()
        w, h = img.size
        for j in range(h):
            for i in range(w):
                c = px[i, j]
                nb = [px[i + di, j + dj] for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= i + di < w and 0 <= j + dj < h]
                if len(nb) >= 3 and all(n != c for n in nb):
                    total += 1
                    where.append((part.name, face, i, j))
    return total, where


def check_fragments(placed, min_size=4):
    """면 안에서 같은 색끼리 이어진 조각이 min_size 픽셀보다 작은 것 (자잘한 잡티 조각)"""
    bad = []
    for part, face, img, _ in placed:
        px = img.load()
        w, h = img.size
        seen = [[False] * w for _ in range(h)]
        for j in range(h):
            for i in range(w):
                if seen[j][i]:
                    continue
                c = px[i, j]
                stack = [(i, j)]
                seen[j][i] = True
                n = 0
                while stack:
                    a, b = stack.pop()
                    n += 1
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x, y = a + da, b + db
                        if 0 <= x < w and 0 <= y < h and not seen[y][x] and px[x, y] == c:
                            seen[y][x] = True
                            stack.append((x, y))
                if n < min_size and n < w * h:
                    bad.append((part.name, face, i, j, n))
    return bad


def clean_speckles(placed):
    """외톨이 픽셀을 주변에서 가장 많은 색으로 메움 (한 번)"""
    fixed = 0
    for part, face, img, _ in placed:
        px = img.load()
        w, h = img.size
        snap = img.copy().load()
        for j in range(h):
            for i in range(w):
                c = snap[i, j]
                nb = [snap[i + di, j + dj] for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= i + di < w and 0 <= j + dj < h]
                if len(nb) >= 3 and all(n != c for n in nb):
                    px[i, j] = max(set(nb), key=nb.count)
                    fixed += 1
    return fixed


def repaste(placed, atlas):
    for _, _, img, pos in placed:
        atlas.paste(img, pos)


def write_outputs(mask, model, atlas, tex_ref, model_path, png_path, bbmodel_path):
    m = dict(model)
    m["textures"] = {"t": tex_ref, "particle": tex_ref}
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, separators=(",", ":"))
    atlas.save(png_path)
    if bbmodel_path:
        write_bbmodel(mask, model, atlas, bbmodel_path)


def write_bbmodel(mask, model, atlas, path):
    """Blockbench 프로젝트 (Java 블록/아이템 형식, 텍스처 내장)"""
    buf = io.BytesIO()
    atlas.save(buf, "PNG")
    size = atlas.width
    tex_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"violence-mask-{mask.name}-tex"))
    els = []
    for k, e in enumerate(model["elements"]):
        faces = {}
        for f, fd in e["faces"].items():
            faces[f] = {"uv": [v * size / 16 for v in fd["uv"]], "texture": 0}
        el = {"name": e.get("name", f"cube{k}"), "box_uv": False, "rescale": False, "locked": False,
              "from": e["from"], "to": e["to"], "autouv": 0, "color": k % 8,
              "origin": e.get("rotation", {}).get("origin", [8, 8, 8]), "faces": faces, "type": "cube",
              "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"violence-mask-{mask.name}-{k}"))}
        r = e.get("rotation")
        if r:
            rot = [0, 0, 0]
            if "axis" in r:
                rot["xyz".index(r["axis"])] = r["angle"]
            else:
                rot = [r.get("x", 0), r.get("y", 0), r.get("z", 0)]
            el["rotation"] = rot
        els.append(el)
    bb = {
        "meta": {"format_version": "4.10", "model_format": "java_block", "box_uv": False},
        "name": mask.name,
        "parent": "",
        "ambientocclusion": True,
        "front_gui_light": False,
        "visible_box": [1, 1, 0],
        "resolution": {"width": size, "height": size},
        "elements": els,
        "outliner": [e["uuid"] for e in els],
        "textures": [{"path": "", "name": mask.name + ".png", "folder": "item/mask", "namespace": "violence",
                      "id": "0", "width": size, "height": size, "uv_width": size, "uv_height": size,
                      "particle": True, "render_mode": "default", "visible": True, "internal": True,
                      "saved": True, "uuid": tex_id,
                      "source": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}],
        "display": model.get("display", {}),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bb, f, ensure_ascii=False, indent=1)
