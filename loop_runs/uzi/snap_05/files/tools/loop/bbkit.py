"""블록벤치 MCP 루프 공용 도구.

- 부품 좌표(강체 변환 합성) 계산, 면별 UV 아틀라스 배치·칠하기(PNG)
- 모델 생성·큐브 추가·검사·렌더·내보내기는 전부 블록벤치 MCP 서버(blockbench-headless)를 호출한다
  (bun run headless/call.ts). 파이썬은 모델 JSON 을 직접 쓰지 않는다.
"""
import json, math, os, subprocess, tempfile
from PIL import Image

BB = "/home/user/jasonjgardner/blockbench-mcp-plugin"
ROOTS = ["/home/user/Violence", "/tmp/claude-0/-home-user-Violence/9e2a1b9e-13dd-555d-a925-ee0a396b8e12/scratchpad"]
FACES = ("north", "south", "east", "west", "up", "down")
NRM = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}


# ───────── 강체 변환 (26.3 / 블록벤치 회전: Rz·Ry·Rx) ─────────
def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def _mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]
def _R(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return {"x": [[1, 0, 0], [0, c, -s], [0, s, c]], "y": [[c, 0, s], [0, 1, 0], [-s, 0, c]],
            "z": [[c, -s, 0], [s, c, 0], [0, 0, 1]]}[axis]
class Xf:
    def __init__(self, R=None, t=(0, 0, 0)):
        self.R = R or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]; self.t = list(t)
    def __mul__(self, o):
        return Xf(_mm(self.R, o.R), [a + b for a, b in zip(_mv(self.R, o.t), self.t)])
    @staticmethod
    def rot(axis, deg, about=(0, 0, 0)):
        R = _R(axis, deg); c = _mv(R, about)
        return Xf(R, [about[i] - c[i] for i in range(3)])
def _euler(R):
    y = math.asin(max(-1, min(1, -R[2][0])))
    if abs(math.cos(y)) > 1e-6:
        x = math.atan2(R[2][1], R[2][2]); z = math.atan2(R[1][0], R[0][0])
    else:
        x = math.atan2(-R[1][2], R[1][1]); z = 0.0
    return [round(math.degrees(v), 4) for v in (x, y, z)]


class Part:
    def __init__(self, frm, to, mat, origin=None, rot=None, name="cube"):
        self.frm, self.to, self.mat, self.origin, self.rot, self.name = frm, to, mat, origin, rot, name


class Builder:
    def __init__(self, scale=1.0, pivot=(8, 8, 8)):
        """scale: 모든 부품을 pivot 기준으로 키우거나 줄임 (회전은 그대로)"""
        self.parts = []; self.scale = scale; self.pivot = pivot
    def put(self, frm, to, mat, xf=None, name="cube"):
        xf = xf or Xf()
        if self.scale != 1.0:
            k, pv = self.scale, self.pivot
            xf = Xf([[k, 0, 0], [0, k, 0], [0, 0, k]], [pv[i] * (1 - k) for i in range(3)]) * xf
            # 회전 행렬만 뽑아 쓰도록 크기 성분을 아래에서 분리
        if self.scale != 1.0:
            k = self.scale
            c = [(frm[i] + to[i]) / 2 for i in range(3)]; h = [abs(to[i] - frm[i]) / 2 * k for i in range(3)]
            wc = [a + b for a, b in zip(_mv(xf.R, c), xf.t)]
            R = [[xf.R[i][j] / k for j in range(3)] for i in range(3)]
            e = _euler(R)
            rot = None if max(abs(v) for v in e) < 1e-4 else e
            self.parts.append(Part([round(wc[i] - h[i], 4) for i in range(3)], [round(wc[i] + h[i], 4) for i in range(3)],
                                   mat, [round(v, 4) for v in wc] if rot else None, rot, name))
            return
        c = [(frm[i] + to[i]) / 2 for i in range(3)]; h = [abs(to[i] - frm[i]) / 2 for i in range(3)]
        wc = [a + b for a, b in zip(_mv(xf.R, c), xf.t)]
        e = _euler(xf.R)
        rot = None if max(abs(v) for v in e) < 1e-4 else e
        self.parts.append(Part([round(wc[i] - h[i], 4) for i in range(3)], [round(wc[i] + h[i], 4) for i in range(3)],
                               mat, [round(v, 4) for v in wc] if rot else None, rot, name))
    def chamfer_box(self, frm, to, c, mat, xf=None, name="cube", edges="all"):
        """모서리를 45° 로 깎은 상자 (안쪽 상자 3개 + 모서리 45° 막대). edges: all | z (z축 방향 모서리 4개만) ..."""
        xf = xf or Xf()
        (x0, y0, z0), (x1, y1, z1) = frm, to
        c = min(c, (x1 - x0) / 2.2, (y1 - y0) / 2.2, (z1 - z0) / 2.2)
        self.put([x0, y0 + c, z0 + c], [x1, y1 - c, z1 - c], mat, xf, name)
        self.put([x0 + c, y0, z0 + c], [x1 - c, y1, z1 - c], mat, xf, name)
        self.put([x0 + c, y0 + c, z0], [x1 - c, y1 - c, z1], mat, xf, name)
        h = c * math.sqrt(2) / 2
        if edges in ("all", "x"):
            for yy in (y0 + c, y1 - c):
                for zz in (z0 + c, z1 - c):
                    self.put([x0 + c, yy - h, zz - h], [x1 - c, yy + h, zz + h], mat, xf * Xf.rot("x", 45, (0, yy, zz)), name)
        if edges in ("all", "z"):
            for xx in (x0 + c, x1 - c):
                for yy in (y0 + c, y1 - c):
                    self.put([xx - h, yy - h, z0 + c], [xx + h, yy + h, z1 - c], mat, xf * Xf.rot("z", 45, (xx, yy, 0)), name)
        if edges in ("all", "y"):
            for xx in (x0 + c, x1 - c):
                for zz in (z0 + c, z1 - c):
                    self.put([xx - h, y0 + c, zz - h], [xx + h, y1 - c, zz + h], mat, xf * Xf.rot("y", 45, (xx, 0, zz)), name)
    def oct(self, axis, c1, c2, r, a0, a1, mat, xf=None, name="cube"):
        """정팔각 단면 원통: 폭 2r·두께 2r·tan22.5 직사각 4장(0/45/90/135°)"""
        xf = xf or Xf()
        w = r * math.tan(math.radians(22.5))
        if axis == "z":
            for rr, (hx, hy) in ((0, (r, w)), (0, (w, r)), (45, (r, w)), (45, (w, r))):
                self.put([c1 - hx, c2 - hy, a0], [c1 + hx, c2 + hy, a1], mat, xf * Xf.rot("z", rr, (c1, c2, 0)), name)
        elif axis == "y":
            for rr, (hx, hz) in ((0, (r, w)), (0, (w, r)), (45, (r, w)), (45, (w, r))):
                self.put([c1 - hx, a0, c2 - hz], [c1 + hx, a1, c2 + hz], mat, xf * Xf.rot("y", rr, (c1, 0, c2)), name)
        else:
            for rr, (hy, hz) in ((0, (r, w)), (0, (w, r)), (45, (r, w)), (45, (w, r))):
                self.put([a0, c1 - hy, c2 - hz], [a1, c1 + hy, c2 + hz], mat, xf * Xf.rot("x", rr, (0, c1, c2)), name)


# ───────── UV 아틀라스 + 칠하기 ─────────
DIR = {"up": 1.2, "north": 1.06, "east": 1.0, "west": 1.0, "south": 0.9, "down": 0.72}   # 옆면 대칭, 앞>옆>뒤
AXDIR = {(1, 1): "up", (1, -1): "down", (2, -1): "north", (2, 1): "south", (0, 1): "east", (0, -1): "west"}


def _face_dims(frm, to, f):
    (x0, y0, z0), (x1, y1, z1) = frm, to
    if f in ("north", "south"):
        return x1 - x0, y1 - y0
    if f in ("east", "west"):
        return z1 - z0, y1 - y0
    return x1 - x0, z1 - z0


def _world_normal(p, f):
    n = list(NRM[f])
    if p.rot:
        R = _mm(_mm(_R("z", p.rot[2]), _R("y", p.rot[1])), _R("x", p.rot[0]))
        n = _mv(R, n)
    return n


def atlas(parts, palette, density=4, painter=None):
    """면마다 고유 UV (모델 1px = density 텍셀). 면은 단색 × 월드 법선 명암. painter(part, face, i, j, tw, th) → 색 이름 or None"""
    faces = []
    for pi, p in enumerate(parts):
        for f in FACES:
            w, h = _face_dims(p.frm, p.to, f)
            faces.append((max(1, math.ceil(h * density - 1e-6)), max(1, math.ceil(w * density - 1e-6)), pi, f))
    faces.sort(key=lambda t: (-t[0], -t[1]))
    size = 64
    while True:
        x = y = shelf = 0; placed = {}; ok = True
        for th, tw, pi, f in faces:
            if x + tw > size:
                x, y, shelf = 0, y + shelf + 1, 0
            if y + th > size:
                ok = False; break
            placed[(pi, f)] = (x, y, tw, th); x += tw + 1; shelf = max(shelf, th)
        if ok:
            break
        size *= 2
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0)); px = img.load()
    uvs = {}
    k16 = 16.0 / size
    for pi, p in enumerate(parts):
        uvs[pi] = {}
        for f in FACES:
            x0, y0, tw, th = placed[(pi, f)]
            n = _world_normal(p, f)
            kf = sum(n[a] ** 2 * DIR[AXDIR[(a, 1 if n[a] >= 0 else -1)]] for a in range(3))
            for j in range(th):
                for i in range(tw):
                    mat = (painter(p, f, i, j, tw, th) if painter else None) or p.mat
                    c = palette[mat]
                    px[x0 + i, y0 + j] = tuple(max(0, min(255, int(round(v * kf)))) for v in c) + (255,)
            w, h = _face_dims(p.frm, p.to, f)
            uw, vh = max(w * density, 0.05), max(h * density, 0.05)
            uvs[pi][f] = [round(x0 * k16, 5), round(y0 * k16, 5), round((x0 + uw) * k16, 5), round((y0 + vh) * k16, 5)]
    return img, uvs


# ───────── 블록벤치 MCP 호출 ─────────
def mcp(tool, args):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=ROOTS[1]) as f:
        json.dump(args, f)
        path = f.name
    cmd = ["bun", "run", "headless/call.ts"] + sum([["--root", r] for r in ROOTS], []) + [tool, "@" + path]
    r = subprocess.run(cmd, cwd=BB, capture_output=True, text=True, timeout=600)
    os.unlink(path)
    if r.returncode != 0:
        raise RuntimeError(f"{tool} 실패: {r.stdout[-2000:]} {r.stderr[-2000:]}")
    return r.stdout


def build_bbmodel(bbfile, name, parts, img_path, uvs, tex_name):
    mcp("bbmodel_create", {"file": bbfile, "format": "java_block", "name": name, "overwrite": True,
                           "resolution": {"width": 16, "height": 16}})
    mcp("bbmodel_add_texture", {"file": bbfile, "image": img_path, "name": tex_name})
    ops = []
    for pi, p in enumerate(parts):
        op = {"op": "add_cube", "name": p.name, "from": p.frm, "to": p.to,
              "faces": {f: {"uv": uvs[pi][f], "texture": tex_name} for f in FACES}}
        if p.rot:
            op["origin"] = p.origin; op["rotation"] = p.rot
        ops.append(op)
    for k in range(0, len(ops), 400):
        mcp("bbmodel_edit", {"file": bbfile, "operations": ops[k:k + 400]})


def validate(bbfile):
    out = mcp("bbmodel_validate", {"file": bbfile, "gates": ["outliner", "degenerate", "block_limits"], "min_thickness": 0.05})
    return out


def render_views(bbfile, outdir, stem, views=("right", "left", "three-quarter", "top")):
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for v in views:
        p = os.path.join(outdir, f"{stem}_{v}.png")
        mcp("bbmodel_render", {"file": bbfile, "view": v, "lighting": "studio", "width": 1024, "height": 768,
                               "output": p, "overwrite": True})
        paths.append(p)
    return paths


def export_java(bbfile, out_json):
    mcp("bbmodel_export_java_block", {"file": bbfile, "output": out_json, "version": "26.3",
                                      "export_groups": False, "export_pivots": False, "overwrite": True})
