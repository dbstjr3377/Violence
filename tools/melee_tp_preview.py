#!/usr/bin/env python3
"""
3인칭 근접 무기 자세 미리보기 (바닐라 HumanoidModel 계산을 옮김, 게임 캡처 아님).
 - 두 손 대기 자세: 석궁 장전 팔 각도 + 어깨 위로 젖힌 무기. 주 손을 바꾸면 좌우가 뒤집힘
   오른쪽 대기 = 다음 공격이 오→왼, 왼쪽 대기 = 다음 공격이 왼→오
 - 휘두르기: 바닐라 공격 동작(WHACK)이 주 팔과 몸통을 비틀고, 무기는 키프레임(melee_tp.py)으로 옆으로 휘두름
결과: docs/images/melee_tp.png, build-out/melee_tp/swing.gif
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import melee_tp as MT  # noqa: E402
import models_melee  # noqa: E402
import tp_sim as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
FONT = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")
TILE = 420


def item_polys(M, model, tex, disp, mirror):
    """tp_sim.item_polys 와 같지만 바닐라 왼손 반전을 적용"""
    D = MT.display_matrix(disp, mirror)
    F = M @ D @ np.linalg.inv(T.sc(*disp["scale"]) @ T.tr(-0.5, -0.5, -0.5))
    ident = {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": disp["scale"]}
    return T.item_polys(F, model, tex, ident)


def render(model, tex, disp, attack, label, cam=(2.0, 1.9, 3.2), charge=1.0, size=TILE, extra=None):
    """왼손 주 손 + 오른팔(보조 손) 휘두르기 — 플러그인이 보는 사람에게 보내는 것과 같음"""
    root = T.entity_root(0)
    right, left, body_y, rpiv, lpiv = MT.arm_pose(True, attack, charge, attack_off=True)
    polys = []
    body = root @ T.part(0, 0, 0, 0, body_y, 0)
    T.cuboid(root @ T.part(0, 0, 0), -4, -8, -4, 8, 8, 8, T.SKIN, polys)
    T.cuboid(body, -4, 0, -2, 8, 12, 4, T.SHIRT, polys)
    ra = root @ T.part(rpiv[0], 2, rpiv[1], right["x"], right["y"], right["z"])
    la = root @ T.part(lpiv[0], 2, lpiv[1], left["x"], left["y"], left["z"])
    T.cuboid(ra, -3, -2, -2, 4, 12, 4, T.SHIRT, polys)
    T.cuboid(la, -1, -2, -2, 4, 12, 4, T.SHIRT, polys)
    T.cuboid(ra, -3, 6, -2.01, 4, 6, 4.02, T.SKIN, polys)
    T.cuboid(la, -1, 6, -2.01, 4, 6, 4.02, T.SKIN, polys)
    T.cuboid(root @ T.part(-1.9, 12, 0), -2, 0, -2, 4, 12, 4, T.PANTS, polys)
    T.cuboid(root @ T.part(1.9, 12, 0), -2, 0, -2, 4, 12, 4, T.PANTS, polys)
    polys += item_polys(MT.hand_matrix(True, attack, charge, attack_off=True), model, tex, disp["thirdperson_lefthand"], True)
    if extra:
        polys += extra
    eye = np.array(cam, dtype=float)
    look = np.array([0, 1.25, 0])
    fwd = look - eye
    fwd /= np.linalg.norm(fwd)
    rt = np.cross(fwd, [0, 1, 0])
    rt /= np.linalg.norm(rt)
    up = np.cross(rt, fwd)
    W = H = size
    f = (H / 2) / math.tan(math.radians(34))
    drawn = []
    for pts, col in polys:
        pp = []
        for p in pts:
            d = np.array(p) - eye
            z = d @ fwd
            pp.append(((W / 2 + (d @ rt) / z * f, H / 2 - (d @ up) / z * f), z))
        drawn.append((sum(z for _, z in pp) / len(pp), [q for q, _ in pp], col))
    drawn.sort(key=lambda t: -t[0])
    img = Image.new("RGB", (W, H), (34, 30, 40))
    d = ImageDraw.Draw(img)
    for _, pts, col in drawn:
        d.polygon(pts, fill=col)
    if label:
        d.text((10, 8), label, font=ImageFont.truetype(FONT, 18), fill=(255, 220, 90))
    return img


def load(name):
    m = json.load(open(os.path.join(NS, "models", "item", "weapon", name + ".json"), encoding="utf-8"))
    tex = Image.open(os.path.join(NS, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
    return m, tex


def sequence(grip, kind):
    """한 번 휘두르기: 대기 → 프레임 0..5 → 끝 자세(=반대쪽 대기). (표시 변환, 공격 시간, 장전 진행)"""
    out = [(MT.stance(grip, left=kind == "l2r"), 0.0, 1.0)]
    for d, (_, att, ch) in zip(MT.swing_frames(grip, kind), MT.frame_states()):
        out.append((d, att, ch))
    return out


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "bat"
    m, tex = load(name)
    grip = models_melee.GRIP[name]
    cam = (1.0, 1.9, 3.4)
    tiles = [render(m, tex, MT.stance(grip), 0, "오른쪽 대기 (다음: 오른쪽에서 왼쪽)", cam),
             render(m, tex, MT.stance(grip, left=True), 0, "왼쪽 대기 (다음: 왼쪽에서 오른쪽)", cam)]
    for kind, label in (("r2l", "오른쪽에서"), ("l2r", "왼쪽에서")):
        seq = sequence(grip, kind)
        for i in (2, 3, 5):
            d, a, ch = seq[i]
            tiles.append(render(m, tex, d, a, f"{label} 휘두르기 {i}/6틱", cam, ch))
    sheet = Image.new("RGB", (4 * TILE, 2 * TILE))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 4) * TILE, (i // 4) * TILE))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "images", "melee_tp.png")
    sheet.save(out)
    print(out)
    # GIF (20fps): 오른쪽 대기 → 오→왼 → 왼쪽 대기 → 왼→오 → 오른쪽 대기. 정면과 뒤쪽 시점을 나란히
    frames = []
    for kind in ("r2l", "l2r"):
        seq = sequence(grip, kind)
        steps = [seq[0]] * 6 + seq[1:]
        for d, a, ch in steps:
            im = Image.new("RGB", (640, 320))
            im.paste(render(m, tex, d, a, "", cam, ch, size=320), (0, 0))
            im.paste(render(m, tex, d, a, "", (-1.6, 2.2, -3.0), ch, size=320), (320, 0))
            frames.append(im)
    gdir = os.path.join(ROOT, "build-out", "melee_tp")
    os.makedirs(gdir, exist_ok=True)
    gif = os.path.join(gdir, f"swing_{name}.gif")
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=50, loop=0)
    print(gif)
