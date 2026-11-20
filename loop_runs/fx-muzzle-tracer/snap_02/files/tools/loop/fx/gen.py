#!/usr/bin/env python3
"""총구 화염 / 탄도 궤적 루프 제작물 (블록벤치 MCP).
 - muzzle_fp : 1인칭 사격 프레임의 총구 화염. 총구 = 원점, +z = 총구 방향 (단위: 모델 px). 총 모델에 붙여 쓴다(bb_adapter.attach)
 - muzzle    : 3인칭(다른 사람이 볼 때) 화염 판. 16x16 판(z=8), 빌보드로 띄움 (Fx.muzzle)
 - tracer    : 탄 궤적. 0~16 정육면체 안, +z 끝이 탄두 쪽. Fx.tracer 가 (폭, 폭, 길이) 로 늘림
사용: python3 tools/loop/fx/gen.py [렌더 폴더]
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from bbkit import Part, build_bbmodel, export_java, validate, render_views, mcp  # noqa: E402

OUT = os.path.join(HERE, "out")
FACES = ("north", "south", "east", "west", "up", "down")

# 팔레트 (빛나는 화염: 흰 심 → 노랑 → 주황 → 테두리 붉은 주황)
CORE, HOT, MID, EDGE = (255, 252, 230, 255), (255, 226, 110, 255), (255, 176, 40, 255), (232, 108, 24, 255)
CLEAR = (0, 0, 0, 0)


class Atlas:
    """작은 그림들을 한 장에 모으고 16 단위 UV 를 돌려줌"""
    def __init__(self, size=64):
        self.img = Image.new("RGBA", (size, size), CLEAR); self.size = size; self.x = self.y = self.row = 0
    def add(self, tile):
        w, h = tile.size
        if self.x + w > self.size:
            self.x, self.y, self.row = 0, self.y + self.row, 0
        self.img.paste(tile, (self.x, self.y)); k = 16 / self.size
        uv = [self.x * k, self.y * k, (self.x + w) * k, (self.y + h) * k]
        self.x += w; self.row = max(self.row, h)
        return uv
    def clear_uv(self):
        if not hasattr(self, "_c"):
            self._c = self.add(Image.new("RGBA", (1, 1), CLEAR))
        return self._c


def star_tile(n, spikes=6, inner=0.34, seed=0, ring=True):
    """정면 화염 (픽셀아트, 반투명 없음): 바늘 5~6개, 길이·간격·굵기가 제각각인 비대칭 별"""
    import random
    rnd = random.Random(seed * 7 + n)
    im = Image.new("RGBA", (n, n), CLEAR); d = ImageDraw.Draw(im); c = n / 2
    a = rnd.uniform(0, math.tau)
    for i in range(spikes):
        a += math.tau / spikes * rnd.uniform(0.7, 1.3)
        ln = c * rnd.uniform(0.55, 0.98)
        w = rnd.uniform(0.26, 0.45)
        d.polygon([(c, c), (c + math.cos(a - w) * c * inner, c + math.sin(a - w) * c * inner),
                   (c + math.cos(a) * ln, c + math.sin(a) * ln), (c + math.cos(a + w) * c * inner, c + math.sin(a + w) * c * inner)], fill=EDGE)
        ln2 = ln * 0.7
        d.polygon([(c, c), (c + math.cos(a - w * 0.6) * c * inner * 0.8, c + math.sin(a - w * 0.6) * c * inner * 0.8),
                   (c + math.cos(a) * ln2, c + math.sin(a) * ln2), (c + math.cos(a + w * 0.6) * c * inner * 0.8, c + math.sin(a + w * 0.6) * c * inner * 0.8)], fill=MID)
    r1, r2 = c * 0.4, c * 0.2
    d.ellipse([c - r1, c - r1 * 0.85, c + r1, c + r1 * 0.85], fill=HOT)
    d.ellipse([c - r2, c - r2, c + r2, c + r2], fill=CORE)
    return despeck(im)


def despeck(im):
    """네 이웃이 모두 같은 색인 외톨이 픽셀을 이웃 색으로 (잡티 검사 통과)"""
    px = im.load(); W, H = im.size
    for _ in range(2):
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                nb = [px[x + 1, y], px[x - 1, y], px[x, y + 1], px[x, y - 1]]
                if all(q == nb[0] for q in nb) and px[x, y] != nb[0]:
                    px[x, y] = nb[0]
    return im


def flame_tile(w, h):
    """옆에서 본 불꽃 (왼쪽 = 총구, 오른쪽으로 가늘어짐). 가운데 밝은 심"""
    im = Image.new("RGBA", (w, h), CLEAR); px = im.load(); cy = (h - 1) / 2
    for x in range(w):
        t = x / (w - 1)
        half = (h / 2) * (1 - t) ** 0.75 * (0.75 + 0.25 * math.cos(t * 7))
        for y in range(h):
            o = abs(y - cy)
            if o <= half * 0.3:
                px[x, y] = CORE if t < 0.5 else HOT
            elif o <= half * 0.65:
                px[x, y] = HOT if t < 0.35 else MID
            elif o <= half:
                px[x, y] = MID if t < 0.6 else EDGE
    return im


def P(frm, to, rot=None, origin=None, name="fx"):
    return Part([round(v, 4) for v in frm], [round(v, 4) for v in to], "fx", origin, rot, name)


def muzzle_fp(at):
    """1인칭 화염: 비대칭 정면 별 2장(엇갈림, 크기 다름) + 별 앞에서 시작해 앞으로 뻗는 십자 불꽃 판 2장"""
    parts, uvs = [], {}
    st = at.add(star_tile(32, seed=2)); st2 = at.add(star_tile(24, spikes=5, seed=5)); fl = at.add(flame_tile(32, 16))
    clr = at.clear_uv()
    def add(p, faceuv):
        uvs[len(parts)] = {f: faceuv.get(f, clr) for f in FACES}; parts.append(p)
    s = 3.4
    add(P([-s, -s, 0.3], [s, s, 0.32], name="star"), {"north": st, "south": st})
    s2 = 2.2
    add(P([-s2, -s2, 0.9], [s2, s2, 0.92], rot=[0, 0, 22.5], origin=[0, 0, 0.91], name="star2"), {"north": st2, "south": st2})
    L, H = 6.0, 2.8
    add(P([-0.01, -H / 2, 0.35], [0.01, H / 2, L], name="flame_v"), {"east": fl, "west": [fl[2], fl[1], fl[0], fl[3]]})
    add(P([-H / 2, -0.01, 0.35], [H / 2, 0.01, L], name="flame_h"), {"up": fl, "down": fl})
    return parts, uvs


def rot_uv(uv):
    return uv   # up/down 면은 UV 회전 없이 같은 그림 (길이 방향이 z)


def muzzle_3p(at):
    parts, uvs = [], {}
    st = at.add(star_tile(32, seed=1)); clr = at.clear_uv()
    uvs[0] = {f: (st if f in ("north", "south") else clr) for f in FACES}
    parts.append(P([0, 0, 8], [16, 16, 8.01], name="muzzle"))
    return parts, uvs


def streak_tile(w, h):
    """세로가 길이 방향(위 = +z 탄두). 탄두는 흰 심이 굵고, 꼬리로 갈수록 가늘어지며 노랑 → 주황으로 식음"""
    im = Image.new("RGBA", (w, h), CLEAR); px = im.load(); cx = (w - 1) / 2
    for y in range(h):
        t = 1 - y / (h - 1)                # 0 = 탄두(위), 1 = 꼬리(아래)
        half = (w / 2) * (1 - 0.75 * t)
        for x in range(w):
            o = abs(x - cx)
            if o > half:
                continue
            core = o <= half * 0.4
            if t < 0.2:
                px[x, y] = CORE if core else HOT
            elif t < 0.55:
                px[x, y] = HOT if core else MID
            else:
                px[x, y] = MID if core else EDGE
    return despeck(im)


def tracer(at):
    """탄 궤적: 가운데에서 엇갈린 십자 판 2장 (어느 방향에서 봐도 줄기), 길이 방향으로 탄두 흰색 → 꼬리 주황"""
    parts, uvs = [], {}
    vt = streak_tile(8, 32)
    tl = at.add(vt.transpose(Image.FLIP_TOP_BOTTOM))  # 위·아래 면: v=0 이 z=0(북쪽) → 탄두(+z)가 그림 아래로
    th = at.add(vt.rotate(90, expand=True))           # 옆면(동·서): u=0 이 z=16 → 탄두(위)를 왼쪽으로 돌린 그림
    clr = at.clear_uv()
    uvs[0] = {f: clr for f in FACES}; uvs[0]["east"] = th; uvs[0]["west"] = th
    parts.append(P([7.99, 0, 0], [8.01, 16, 16], name="tracer_v"))
    uvs[1] = {f: clr for f in FACES}; uvs[1]["up"] = tl; uvs[1]["down"] = tl
    parts.append(P([0, 7.99, 0], [16, 8.01, 16], name="tracer_h"))
    return parts, uvs


def build_one(name, maker, render_dir=None, views=("front", "right", "three-quarter", "top")):
    os.makedirs(OUT, exist_ok=True)
    at = Atlas(64)
    parts, uvs = maker(at)
    png = os.path.join(OUT, name + ".png"); at.img.save(png)
    bb = os.path.join(OUT, name + ".bbmodel")
    build_bbmodel(bb, name, parts, png, uvs, name, fmt="free")
    mcp("bbmodel_edit", {"file": bb, "operations": [{"op": "update_texture", "target": name, "render_mode": "emissive"}]})
    validate(bb)
    export_java(bb, os.path.join(OUT, name + ".json"))
    if render_dir:
        render_views(bb, render_dir, name, views=views)
    print(name, len(parts))


def build_all(render_dir=None):
    build_one("muzzle_fp", muzzle_fp, render_dir)
    build_one("muzzle", muzzle_3p, render_dir, views=("front", "three-quarter"))
    build_one("tracer", tracer, render_dir)


if __name__ == "__main__":
    build_all(sys.argv[1] if len(sys.argv) > 1 else None)
