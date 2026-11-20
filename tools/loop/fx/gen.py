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


def star_tile(n, spikes=8, inner=0.32, seed=0, ring=True):
    """정면 별 화염 (픽셀아트, 반투명 없음)"""
    im = Image.new("RGBA", (n, n), CLEAR); d = ImageDraw.Draw(im); c = n / 2
    for i in range(spikes):
        a = i * math.tau / spikes + 0.3 + seed * 0.17
        ln = c * (0.98 if i % 2 == 0 else 0.62)
        w = 0.32 if i % 2 == 0 else 0.4
        d.polygon([(c, c), (c + math.cos(a - w) * c * inner, c + math.sin(a - w) * c * inner),
                   (c + math.cos(a) * ln, c + math.sin(a) * ln), (c + math.cos(a + w) * c * inner, c + math.sin(a + w) * c * inner)], fill=EDGE)
        ln2 = ln * 0.72
        d.polygon([(c, c), (c + math.cos(a - w * 0.6) * c * inner * 0.8, c + math.sin(a - w * 0.6) * c * inner * 0.8),
                   (c + math.cos(a) * ln2, c + math.sin(a) * ln2), (c + math.cos(a + w * 0.6) * c * inner * 0.8, c + math.sin(a + w * 0.6) * c * inner * 0.8)], fill=MID)
    r1, r2 = c * 0.42, c * 0.22
    d.ellipse([c - r1, c - r1, c + r1, c + r1], fill=HOT)
    d.ellipse([c - r2, c - r2, c + r2, c + r2], fill=CORE)
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
    """1인칭 화염: 정면 별 2장(엇갈림) + 앞으로 뻗는 십자 불꽃 판 2장 + 옆으로 튀는 작은 불꽃 4장"""
    parts, uvs = [], {}
    st = at.add(star_tile(32)); st2 = at.add(star_tile(24, spikes=6, seed=3)); fl = at.add(flame_tile(32, 16)); sm = at.add(flame_tile(16, 8))
    clr = at.clear_uv()
    def add(p, faceuv):
        uvs[len(parts)] = {f: faceuv.get(f, clr) for f in FACES}; parts.append(p)
    s = 3.4
    add(P([-s, -s, 0.3], [s, s, 0.32], name="star"), {"north": st, "south": st})
    s2 = 2.4
    add(P([-s2, -s2, 0.9], [s2, s2, 0.92], rot=[0, 0, 22.5], origin=[0, 0, 0.91], name="star2"), {"north": st2, "south": st2})
    L, H = 6.0, 2.8
    add(P([-0.01, -H / 2, 0.0], [0.01, H / 2, L], name="flame_v"), {"east": fl, "west": [fl[2], fl[1], fl[0], fl[3]]})
    add(P([-H / 2, -0.01, 0.0], [H / 2, 0.01, L], name="flame_h"), {"up": rot_uv(fl), "down": rot_uv(fl)})
    for k, ang in enumerate((45, 135, 225, 315)):   # 옆으로 튀는 작은 불꽃 (총구 앞 45° 방향)
        add(P([-0.01, -0.7, 0.2], [0.01, 0.7, 2.4], rot=[0, 0, ang - 90 if ang > 90 else ang], origin=[0, 0, 0.2], name="spark"), {"east": sm, "west": sm})
    return parts, uvs


def rot_uv(uv):
    return uv   # up/down 면은 UV 회전 없이 같은 그림 (길이 방향이 z)


def muzzle_3p(at):
    parts, uvs = [], {}
    st = at.add(star_tile(32, seed=1)); clr = at.clear_uv()
    uvs[0] = {f: (st if f in ("north", "south") else clr) for f in FACES}
    parts.append(P([0, 0, 8], [16, 16, 8.01], name="muzzle"))
    return parts, uvs


def tracer(at):
    """머리(+z) 쪽이 굵고 밝으며 꼬리 쪽으로 가늘어지고 주황으로 식는 줄기. 단면은 정사각형 (어느 쪽에서 봐도 같은 폭)"""
    parts, uvs = [], {}
    segs = [(0.0, 4.0, 2.4, EDGE), (3.8, 9.0, 3.6, MID), (8.8, 14.0, 5.0, HOT), (13.8, 16.0, 6.0, CORE)]
    for z0, z1, w, col in segs:
        t = Image.new("RGBA", (4, 4), col); d = ImageDraw.Draw(t)
        if col != CORE:
            d.rectangle([1, 0, 2, 3], fill=HOT if col != HOT else CORE)   # 가운데 밝은 심 (길이 방향)
        uv = at.add(t)
        uvs[len(parts)] = {f: uv for f in FACES}
        parts.append(P([8 - w / 2, 8 - w / 2, z0], [8 + w / 2, 8 + w / 2, z1], name="tracer"))
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
