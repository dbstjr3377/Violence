#!/usr/bin/env python3
"""
3인칭 시뮬레이터: 마인크래프트 플레이어 모델(HumanoidModel) 의 팔 자세와
ItemInHandLayer 의 손-아이템 변환을 그대로 계산해, 다른 사람이 보는 모습을 미리 본다.
 - 자세: CROSSBOW_HOLD (장전된 석궁: 양팔 조준), ITEM (한 손으로 들기)
 - 손 변환: translateToHand → X-90° → Y180° → translate(±1/16, 0.125, -0.625) → 아이템 표시 변환
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

W, H = 900, 700


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def tr(x, y, z):
    m = np.eye(4)
    m[:3, 3] = [x, y, z]
    return m


def sc(x, y, z):
    return np.diag([x, y, z, 1.0])


def part(px, py, pz, xr=0, yr=0, zr=0):
    """ModelPart.translateAndRotate: translate(px/16) · rotationZYX(z, y, x)"""
    return tr(px / 16, py / 16, pz / 16) @ rz(zr) @ ry(yr) @ rx(xr)


def entity_root(body_yaw_deg=0):
    # LivingEntityRenderer: Y(180 - bodyYaw) · scale(-1,-1,1) · translate(0,-1.501,0)
    return ry(math.radians(180 - body_yaw_deg)) @ sc(-1, -1, 1) @ tr(0, -1.501, 0)


POSES = {
    # (오른팔 xRot, yRot), (왼팔 xRot, yRot)
    "crossbow_hold": ((-math.pi / 2 + 0.1, -0.3), (-1.5, 0.6)),
    "item": ((-math.pi / 10, 0.0), (0.0, 0.0)),
    "idle": ((0.0, 0.0), (0.0, 0.0)),
}

SKIN = (208, 160, 125)
SHIRT = (60, 140, 150)
PANTS = (50, 50, 120)


def cuboid(M, x0, y0, z0, sx, sy, sz, color, out):
    """모델 픽셀 단위 상자 → 화면 다각형 목록"""
    corners = []
    for dx in (0, sx):
        for dy in (0, sy):
            for dz in (0, sz):
                corners.append(M @ np.array([(x0 + dx) / 16, (y0 + dy) / 16, (z0 + dz) / 16, 1.0]))
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for f in faces:
        pts = [corners[i][:3] for i in f]
        out.append((pts, color))


def item_polys(M, model, tex, disp):
    t = [v / 16 for v in disp.get("translation", [0, 0, 0])]
    r = [math.radians(v) for v in disp.get("rotation", [0, 0, 0])]
    s = disp.get("scale", [1, 1, 1])
    D = tr(*t) @ rx(r[0]) @ ry(r[1]) @ rz(r[2]) @ sc(*s) @ tr(-0.5, -0.5, -0.5)
    F = M @ D
    tw, th = tex.size
    px = tex.load()
    out = []
    for el in model["elements"]:
        a, b = el["from"], el["to"]
        R = np.eye(4)
        if el.get("rotation"):
            o = el["rotation"]["origin"]
            ang = math.radians(el["rotation"]["angle"])
            axis = {"x": rx, "y": ry, "z": rz}[el["rotation"]["axis"]](ang)
            R = tr(o[0] / 16, o[1] / 16, o[2] / 16) @ axis @ tr(-o[0] / 16, -o[1] / 16, -o[2] / 16)
        for f, fd in el["faces"].items():
            u0, v0, u1, v1 = fd["uv"]
            cx, cy = int((u0 + u1) / 32 * tw), int((v0 + v1) / 32 * th)
            c = px[min(tw - 1, cx), min(th - 1, cy)]
            if c[3] < 10:
                continue
            x0, y0, z0 = [v / 16 for v in a]
            x1, y1, z1 = [v / 16 for v in b]
            quad = {
                "north": [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
                "south": [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
                "east": [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
                "west": [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
                "up": [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
                "down": [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)],
            }[f]
            pts = [(F @ R @ np.array([p[0], p[1], p[2], 1.0]))[:3] for p in quad]
            shade = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "east": 0.62, "west": 0.62}[f]
            out.append((pts, tuple(int(c[i] * shade) for i in range(3))))
    return out


def render(pose, model=None, tex=None, disp=None, cam=(2.2, 2.0, 3.4), look=(0, 1.2, 0), label=""):
    root = entity_root(0)
    (rxr, ryr), (lxr, lyr) = POSES[pose]
    polys = []
    # 몸 (모델 좌표: y 아래쪽, 정면 -Z)
    cuboid(root @ part(0, 0, 0), -4, -8, -4, 8, 8, 8, SKIN, polys)              # 머리
    cuboid(root @ part(0, 0, 0), -4, 0, -2, 8, 12, 4, SHIRT, polys)             # 몸통
    ra = root @ part(-5, 2, 0, rxr, ryr, 0)
    la = root @ part(5, 2, 0, lxr, lyr, 0)
    cuboid(ra, -3, -2, -2, 4, 12, 4, SHIRT, polys)
    cuboid(la, -1, -2, -2, 4, 12, 4, SHIRT, polys)
    cuboid(ra, -3, 6, -2.01, 4, 6, 4.02, SKIN, polys)
    cuboid(la, -1, 6, -2.01, 4, 6, 4.02, SKIN, polys)
    cuboid(root @ part(-1.9, 12, 0, 0.5, 0, 0), -2, 0, -2, 4, 12, 4, PANTS, polys)   # 걷는 다리 (따로 움직임)
    cuboid(root @ part(1.9, 12, 0, -0.5, 0, 0), -2, 0, -2, 4, 12, 4, PANTS, polys)
    if model is not None:
        hand = ra @ rx(math.radians(-90)) @ ry(math.radians(180)) @ tr(1 / 16, 0.125, -0.625)
        polys += item_polys(hand, model, tex, disp)
    # 카메라
    eye = np.array(cam, dtype=float)
    fwd = np.array(look) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    f = (H / 2) / math.tan(math.radians(35))

    def proj(p):
        d = np.array(p) - eye
        x, y, z = d @ right, d @ up, d @ fwd
        return (W / 2 + x / z * f, H / 2 - y / z * f), z

    drawn = []
    for pts, col in polys:
        pp = [proj(p) for p in pts]
        depth = sum(z for _, z in pp) / len(pp)
        drawn.append((depth, [q for q, _ in pp], col))
    drawn.sort(key=lambda t: -t[0])
    img = Image.new("RGB", (W, H), (34, 30, 40))
    d = ImageDraw.Draw(img)
    for _, pts, col in drawn:
        d.polygon(pts, fill=col)
    d.text((10, 10), label, fill=(255, 255, 255))
    return img


def load(ns, name, kind="weapon"):
    m = json.load(open(os.path.join(ns, "models", "item", kind, name + ".json"), encoding="utf-8"))
    tex = Image.open(os.path.join(ns, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
    return m, tex


if __name__ == "__main__":
    from PIL import ImageFont
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
    FONT = ImageFont.truetype(os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf"), 26)
    shots = [("m16_tp", "crossbow_hold", "M16 - 양팔 조준 (석궁 자세)"), ("shotgun_tp", "crossbow_hold", "샷건 - 양팔 조준"),
             ("mp5_tp", "crossbow_hold", "MP5 - 양팔 조준"), ("magnum", "item", "매그넘 - 한 손"),
             ("silenced_pistol", "item", "소음기 권총 - 한 손"), ("katana", "item", "카타나 - 한 손 들기")]
    tiles = []
    for name, pose, label in shots:
        m = json.load(open(os.path.join(NS, "models", "item", "weapon", name + ".json"), encoding="utf-8"))
        if "parent" in m:
            base = json.load(open(os.path.join(NS, "models", "item", "weapon", m["parent"].split("/")[-1] + ".json"), encoding="utf-8"))
            base["display"] = {**base.get("display", {}), **m["display"]}
            m = base
        tex = Image.open(os.path.join(NS, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
        img = render(pose, m, tex, m["display"]["thirdperson_righthand"], cam=(2.6, 2.1, 3.0))
        ImageDraw.Draw(img).text((16, 12), label, font=FONT, fill=(255, 220, 90))
        tiles.append(img.resize((450, 350)))
    sheet = Image.new("RGB", (450 * 3, 350 * 2))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * 450, (i // 3) * 350))
    out = os.path.join(ROOT, "docs", "images", "thirdperson.png")
    sheet.save(out)
    print(out)
