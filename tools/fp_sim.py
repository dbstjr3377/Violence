#!/usr/bin/env python3
"""
1인칭 화면 시뮬레이터.
마인크래프트의 1인칭 아이템 렌더링 변환을 그대로 계산해 화면 구도를 미리 본다.
 - 손 위치: translate(0.56, -0.52, -0.72) (오른손, 장착 애니메이션 끝난 상태)
 - 표시 변환: translate(t/16) · rotationXYZ(r) · scale(s), 그 뒤 모델 (-0.5,-0.5,-0.5) 이동, 1/16 배
 - 손 렌더링 FOV 70 (수직), 카메라는 -Z 를 바라봄
"""
import json
import math
import os

from PIL import Image, ImageDraw

W, H = 1280, 720
FOV = 70.0


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def element_rot(p, r):
    if not r:
        return p
    o = r["origin"]
    q = [p[i] - o[i] for i in range(3)]
    if "axis" in r:
        a = math.radians(r["angle"])
        R = {"x": rx(a), "y": ry(a), "z": rz(a)}[r["axis"]]
    else:
        # 26.3 오일러 회전: Rz·Ry·Rx
        R = mm(mm(rz(math.radians(r.get("z", 0))), ry(math.radians(r.get("y", 0)))), rx(math.radians(r.get("x", 0))))
    q = mv(R, q)
    return [q[i] + o[i] for i in range(3)]


CORNERS = {
    # 면 → (fu,fv) 를 3D 로 바꾸는 기준점: 왼위, 오른위, 왼아래 (바깥에서 볼 때)
    "north": lambda a, b: ((b[0], b[1], a[2]), (a[0], b[1], a[2]), (b[0], a[1], a[2])),
    "south": lambda a, b: ((a[0], b[1], b[2]), (b[0], b[1], b[2]), (a[0], a[1], b[2])),
    "east": lambda a, b: ((b[0], b[1], b[2]), (b[0], b[1], a[2]), (b[0], a[1], b[2])),
    "west": lambda a, b: ((a[0], b[1], a[2]), (a[0], b[1], b[2]), (a[0], a[1], a[2])),
    "up": lambda a, b: ((a[0], b[1], a[2]), (b[0], b[1], a[2]), (a[0], b[1], b[2])),
    "down": lambda a, b: ((a[0], a[1], b[2]), (b[0], a[1], b[2]), (a[0], a[1], a[2])),
}
LIGHT = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "east": 0.6, "west": 0.6}


def render_items(draw_list, model, tex, disp, hand=(0.56, -0.52, -0.72), recoil=(0, 0, 0)):
    t = [v / 16 for v in disp.get("translation", [0, 0, 0])]
    r = [math.radians(v) for v in disp.get("rotation", [0, 0, 0])]
    s = disp.get("scale", [1, 1, 1])
    R = mm(mm(rx(r[0]), ry(r[1])), rz(r[2]))
    texs = tex if isinstance(tex, dict) else {"#t": tex}
    if "#skin" not in texs:
        sp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resourcepack", "assets", "violence", "textures", "skin", "self.png")
        if os.path.isfile(sp):
            texs["#skin"] = Image.open(sp).convert("RGBA")
    main_tex = texs.get("#t") or next(iter(texs.values()))

    def xf(p):
        q = [(p[i] / 16 - 0.5) * s[i] for i in range(3)]
        q = mv(R, q)
        return [q[i] + t[i] + hand[i] + recoil[i] for i in range(3)]

    for el in model["elements"]:
        a, b = el["from"], el["to"]
        for f, fd in el["faces"].items():
            tex_f = texs.get(fd.get("texture", "#t"), main_tex)
            tw, th = tex_f.size
            px = tex_f.load()
            tl, tr, bl = CORNERS[f](a, b)
            tl, tr, bl = (element_rot(list(p), el.get("rotation")) for p in (tl, tr, bl))
            u0, v0, u1, v1 = fd["uv"]
            x0, y0 = int(round(u0 / 16 * tw)), int(round(v0 / 16 * th))
            x1, y1 = int(round(u1 / 16 * tw)), int(round(v1 / 16 * th))
            nu, nv = max(1, x1 - x0), max(1, y1 - y0)
            du = [(tr[i] - tl[i]) / nu for i in range(3)]
            dv = [(bl[i] - tl[i]) / nv for i in range(3)]
            light = 1.0 if el.get("light_emission") else LIGHT[f]
            for j in range(nv):
                for i in range(nu):
                    c = px[x0 + i, y0 + j]
                    if c[3] < 10:
                        continue
                    p0 = [tl[k] + du[k] * i + dv[k] * j for k in range(3)]
                    quad = [p0, [p0[k] + du[k] for k in range(3)], [p0[k] + du[k] + dv[k] for k in range(3)], [p0[k] + dv[k] for k in range(3)]]
                    vq = [xf(p) for p in quad]
                    # 뒷면 제거
                    e1 = [vq[1][k] - vq[0][k] for k in range(3)]
                    e2 = [vq[3][k] - vq[0][k] for k in range(3)]
                    n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
                    cen = [sum(v[k] for v in vq) / 4 for k in range(3)]
                    # (e1×e2) 는 면의 안쪽을 향함 → 카메라(원점)에서 보이려면 (e1×e2)·중심 > 0
                    if n[0] * cen[0] + n[1] * cen[1] + n[2] * cen[2] < 0:
                        continue
                    if any(v[2] > -0.05 for v in vq):
                        continue
                    col = tuple(int(c[k] * light) for k in range(3))
                    draw_list.append((cen[2], vq, col))


def project(v):
    f = (H / 2) / math.tan(math.radians(FOV / 2))
    return (W / 2 + v[0] / -v[2] * f, H / 2 - v[1] / -v[2] * f)


def background(kind="room"):
    img = Image.new("RGB", (W, H), (60, 58, 66))
    d = ImageDraw.Draw(img)
    hy = H * 0.47
    # 벽
    for y in range(int(hy)):
        k = y / hy
        d.line([(0, y), (W, y)], fill=(int(70 + 40 * k), int(60 + 30 * k), int(72 + 20 * k)))
    # 바닥 (원근 타일)
    for y in range(int(hy), H):
        k = (y - hy) / (H - hy)
        d.line([(0, y), (W, y)], fill=(int(40 + 70 * k), int(36 + 50 * k), int(40 + 40 * k)))
    for i in range(-12, 13):
        d.line([(W / 2 + i * 30, hy), (W / 2 + i * 260, H)], fill=(30, 28, 34), width=1)
    for j in range(1, 14):
        y = hy + (H - hy) * (j / 14) ** 2
        d.line([(0, y), (W, y)], fill=(30, 28, 34), width=1)
    # 문틀, 창문
    d.rectangle([W * 0.30, H * 0.20, W * 0.37, H * 0.47], fill=(110, 70, 40))
    d.rectangle([W * 0.55, H * 0.16, W * 0.72, H * 0.33], fill=(120, 170, 190))
    d.rectangle([W * 0.55, H * 0.16, W * 0.72, H * 0.33], outline=(200, 200, 210), width=3)
    return img


def scene(model_path, tex_path, disp, out, flash=False, recoil=(0, 0, 0), label=None):
    model = json.load(open(model_path, encoding="utf-8"))
    tex = Image.open(tex_path).convert("RGBA")
    img = background()
    d = ImageDraw.Draw(img)
    items = []
    render_items(items, model, tex, disp, recoil=recoil)
    items.sort(key=lambda t: t[0])
    for _, vq, col in items:
        d.polygon([project(v) for v in vq], fill=col)
    # 조준점
    cx, cy = W / 2, H / 2
    d.line([(cx - 9, cy), (cx + 9, cy)], fill=(255, 255, 255), width=2)
    d.line([(cx, cy - 9), (cx, cy + 9)], fill=(255, 255, 255), width=2)
    # 핫바 자리 표시
    d.rectangle([W / 2 - 182, H - 44, W / 2 + 182, H - 4], outline=(200, 200, 200), width=2)
    if label:
        d.text((16, 14), label, fill=(255, 255, 255))
    img.save(out)
    return img


def muzzle_screen(disp, muzzle, hand=(0.56, -0.52, -0.72)):
    """모델 좌표의 총구 → 시점 좌표 (오른쪽, 위, 앞)"""
    t = [v / 16 for v in disp.get("translation", [0, 0, 0])]
    r = [math.radians(v) for v in disp.get("rotation", [0, 0, 0])]
    s = disp.get("scale", [1, 1, 1])
    R = mm(mm(rx(r[0]), ry(r[1])), rz(r[2]))
    q = [(muzzle[i] / 16 - 0.5) * s[i] for i in range(3)]
    q = mv(R, q)
    v = [q[i] + t[i] + hand[i] for i in range(3)]
    return v, project(v)


def turntable(model, tex, rotation, size=300, dist=2.4, bg=(30, 26, 36), scale=1.0):
    """모델 한 개를 원근 카메라로 렌더 (미리보기용)"""
    global W, H
    ow, oh = W, H
    W, H = size, size
    try:
        img = Image.new("RGB", (size, size), bg)
        d = ImageDraw.Draw(img)
        items = []
        render_items(items, model, tex, {"rotation": rotation, "scale": [scale] * 3}, hand=(0, 0, -dist))
        items.sort(key=lambda t: t[0])
        for _, vq, col in items:
            d.polygon([project(v) for v in vq], fill=col)
        return img
    finally:
        W, H = ow, oh
