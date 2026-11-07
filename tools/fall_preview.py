#!/usr/bin/env python3
"""
쓰러질 때 넘어지는 동작 미리보기 (게임 캡처 아님).
 - 인형: plugin-src/src/main/resources/fall.json 의 6프레임을 플러그인(FallPose)과 같은 계산으로 놓음
 - 실제 몸: 바닐라 엎드린 자세(AvatarRenderer: X-90° 회전, (0,-1,0.3) 이동, 머리 -45°, 팔 머리 위)를
   모델 계산 그대로 따로 그려서, 인형 마지막 프레임과 겹치는지 확인
결과: docs/images/fall.png (프레임 6장 + 실제 몸 겹침), build-out/fall/fall.gif
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tp_sim as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALL = os.path.join(ROOT, "plugin-src", "src", "main", "resources", "fall.json")
FONT = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")
PX = 0.9375 / 16

# FallPose.Part: 관절(px), 관절→중심(px), 크기(px)
PARTS = {
    "head": ((0, 24, 0), (0, 4, 0)),
    "body": ((0, 12, 0), (0, 6, 0)),
    "arm_r": ((-5, 22, 0), (-1, -4, 0)),
    "arm_l": ((5, 22, 0), (1, -4, 0)),
    "leg_r": ((-1.9, 12, 0), (0, -6, 0)),
    "leg_l": ((1.9, 12, 0), (0, -6, 0)),
}
# build_pack.PUPPET_PARTS 와 같은 상자 (16 단위, 중심 8) — 색 번호 0/1
BOXES = {
    "head": [([4, 4, 4], [12, 12, 12], 0), ([3.9, 10, 3.9], [12.1, 12.1, 12.1], 1), ([3.9, 7.5, 11.9], [12.1, 10, 12.1], 1)],
    "body": [([4, 2, 6], [12, 14, 10], 0)],
    "arm": [([6, 10, 6], [10, 14, 10], 0), ([6, 2, 6], [10, 10, 10], 1)],
    "leg": [([6, 4, 6], [10, 14, 10], 0), ([6, 2, 6], [10, 4, 10], 1)],
}
SKIN, HAIR, SHIRT, PANTS, SHOES = (200, 154, 122), (59, 42, 30), (60, 140, 150), (50, 50, 120), (34, 34, 34)
COLORS = {"head": (SKIN, HAIR), "body": (SHIRT, SHIRT), "arm": (SHIRT, SKIN), "leg": (PANTS, SHOES)}


def rot_xyz(a):
    return T.rx(math.radians(a[0])) @ T.ry(math.radians(a[1])) @ T.rz(math.radians(a[2]))


def load():
    return json.load(open(FALL, encoding="utf-8"))


def puppet_polys(frame, polys):
    """FallPose.place 와 같은 계산 + 아이템 디스플레이의 Y180° (모델 +z 가 뒤쪽)"""
    body = T.rx(math.radians(frame["pitch"]))
    for name, (joint, off) in PARTS.items():
        local = rot_xyz(frame.get(name, [0, 0, 0]))
        c = (local @ np.array([*off, 1.0]))[:3] + np.array(joint)
        c = (body @ np.array([*(c * PX), 1.0]))[:3] + np.array([0, frame["feet"][0], frame["feet"][1]])
        M = T.tr(*c) @ body @ local @ T.ry(math.pi) @ T.sc(0.9375, 0.9375, 0.9375)
        kind = name.split("_")[0]
        for a, b, tint in BOXES[kind]:
            T.cuboid(M, a[0] - 8, a[1] - 8, a[2] - 8, b[0] - a[0], b[1] - a[1], b[2] - a[2], COLORS[kind][tint], polys)


def vanilla_back_polys(polys, lift, arms_out=0.0):
    """바닐라 누운 자세 (침대 없는 SLEEPING 마네킹, 몸 방향 φ = -yaw - 90, yaw 0) + lift 만큼 띄움"""
    phi = -90
    root = T.tr(0, lift, 0) @ T.ry(math.radians(phi)) @ T.rz(math.radians(90)) @ T.ry(math.radians(270)) \
        @ T.sc(-1, -1, 1) @ T.sc(0.9375, 0.9375, 0.9375) @ T.tr(0, -1.501, 0)
    T.cuboid(root @ T.part(0, 0, 0), -4, -8, -4, 8, 8, 8, SKIN, polys)
    T.cuboid(root @ T.part(0, 0, 0), -4, -8.01, -4.01, 8, 2.5, 8.02, HAIR, polys)
    T.cuboid(root @ T.part(0, 0, 0), -4, 0, -2, 8, 12, 4, SHIRT, polys)
    T.cuboid(root @ T.part(-5, 2, 0), -3, -2, -2, 4, 12, 4, SHIRT, polys)
    T.cuboid(root @ T.part(5, 2, 0), -1, -2, -2, 4, 12, 4, SHIRT, polys)
    T.cuboid(root @ T.part(-1.9, 12, 0), -2, 0, -2, 4, 12, 4, PANTS, polys)
    T.cuboid(root @ T.part(1.9, 12, 0), -2, 0, -2, 4, 12, 4, PANTS, polys)


def vanilla_lying_polys(polys, color=None):
    """바닐라 엎드린 자세 (실제 몸) — 개체가 +Z 를 봄, 정지 상태"""
    root = T.ry(math.pi) @ T.rx(math.radians(-90)) @ T.tr(0, -1, 0.3) @ T.sc(-1, -1, 1) @ T.sc(0.9375, 0.9375, 0.9375) @ T.tr(0, -1.501, 0)
    col = lambda c: color or c  # noqa: E731
    T.cuboid(root @ T.part(0, 0, 0, -math.pi / 4, 0, 0), -4, -8, -4, 8, 8, 8, col(SKIN), polys)
    T.cuboid(root @ T.part(0, 0, 0), -4, 0, -2, 8, 12, 4, col(SHIRT), polys)
    T.cuboid(root @ T.part(-5, 2, 0, 0, math.pi, math.pi), -3, -2, -2, 4, 12, 4, col(SHIRT), polys)
    T.cuboid(root @ T.part(5, 2, 0, 0, math.pi, math.pi), -1, -2, -2, 4, 12, 4, col(SHIRT), polys)
    T.cuboid(root @ T.part(-1.9, 12, 0), -2, 0, -2, 4, 12, 4, col(PANTS), polys)
    T.cuboid(root @ T.part(1.9, 12, 0), -2, 0, -2, 4, 12, 4, col(PANTS), polys)


def floor_polys(polys):
    for i in range(-3, 3):
        for j in range(-3, 3):
            c = (70, 62, 58) if (i + j) % 2 == 0 else (60, 54, 50)
            polys.append(([(i, 0, j), (i + 1, 0, j), (i + 1, 0, j + 1), (i, 0, j + 1)], c))


def draw(polys, cam, size, label="", look=(0, 0.6, 0.2), wire=None):
    eye = np.array(cam, dtype=float)
    fwd = np.array(look) - eye
    fwd /= np.linalg.norm(fwd)
    rt = np.cross(fwd, [0, 1, 0])
    rt /= np.linalg.norm(rt)
    up = np.cross(rt, fwd)
    f = (size / 2) / math.tan(math.radians(30))

    def proj(p):
        d = np.array(p, dtype=float) - eye
        z = d @ fwd
        return (size / 2 + (d @ rt) / z * f, size / 2 - (d @ up) / z * f), z

    drawn = []
    for pts, col in polys:
        pp = [proj(p) for p in pts]
        drawn.append((sum(z for _, z in pp) / len(pp), [q for q, _ in pp], col))
    drawn.sort(key=lambda t: -t[0])
    img = Image.new("RGB", (size, size), (34, 30, 40))
    d = ImageDraw.Draw(img)
    for _, pts, col in drawn:
        d.polygon(pts, fill=col)
    if wire:
        for pts, _ in wire:
            q = [proj(p)[0] for p in pts]
            d.line(q + [q[0]], fill=(255, 80, 80), width=1)
    if label:
        d.text((8, 6), label, font=ImageFont.truetype(FONT, 16), fill=(255, 220, 90))
    return img


def scene(frame=None, end=None, lift=0.14, standing=False):
    polys = []
    floor_polys(polys)
    if standing:
        puppet_polys({"pitch": 0, "feet": [0, 0]}, polys)
    elif end == "face_down":
        vanilla_lying_polys(polys)
    elif end == "face_up":
        vanilla_back_polys(polys, lift)
    else:
        puppet_polys(frame, polys)
    return polys


LABELS = {"forward": "뒤에서 맞음: 앞으로", "back": "앞에서 맞음: 뒤로", "blast": "샷건: 팔 벌리고 뒤로"}


if __name__ == "__main__":
    data = load()
    lift = data["back_lift"]
    side, quarter = (3.6, 1.2, 0.2), (2.6, 2.2, 2.8)
    S = 240
    rows = []
    for name, kind in data["kinds"].items():
        frames = kind["frames"]
        # 뒤로 넘어지는 동작은 팔 벌림이 보이도록 비스듬히 앞에서
        cam = side if name == "forward" else (2.6, 2.3, 1.9)
        row = [draw(scene(standing=True), cam, S, LABELS[name])]
        for k, fr in enumerate(frames[:6]):
            row.append(draw(scene(fr), cam, S, f"{k + 1}프레임"))
        # 마지막 프레임 위에 바닐라 자세(마네킹 대역) 윤곽을 겹쳐서 확인
        wire = []
        (vanilla_lying_polys if kind["end"] == "face_down" else lambda p: vanilla_back_polys(p, lift))(wire)
        over = []
        floor_polys(over)
        puppet_polys(frames[-1], over)
        row.append(draw(over, cam, S, "끝 + 대역(빨간 선)", wire=wire))
        row.append(draw(scene(end=kind["end"], lift=lift), quarter, S, "대역 (바닐라 자세)"))
        rows.append(row)
    sheet = Image.new("RGB", (len(rows[0]) * S, len(rows) * S))
    for j, r in enumerate(rows):
        for i, t in enumerate(r):
            sheet.paste(t, (i * S, j * S))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "images", "fall.png")
    sheet.save(out)
    print(out)
    # GIF (20fps): 세 가지를 차례로. 3/4 시점과 옆 시점을 나란히
    gif_frames = []
    for name, kind in data["kinds"].items():
        frames = kind["frames"]
        seq = [("stand", None)] * 8 + [("f", fr) for fr in frames] + [("f", frames[-1])] * (kind["hold_ticks"] - len(frames)) + [("end", None)] * 14
        for what, fr in seq:
            sc = scene(fr, end=kind["end"] if what == "end" else None, lift=lift, standing=what == "stand")
            im = Image.new("RGB", (640, 320))
            im.paste(draw(sc, quarter, 320), (0, 0))
            im.paste(draw(sc, side, 320), (320, 0))
            ImageDraw.Draw(im).text((8, 6), LABELS[name] + ("  (인형)" if what == "f" else "  (대역)" if what == "end" else ""),
                                   font=ImageFont.truetype(FONT, 16), fill=(255, 220, 90))
            gif_frames.append(im)
    gdir = os.path.join(ROOT, "build-out", "fall")
    os.makedirs(gdir, exist_ok=True)
    gif = os.path.join(gdir, "fall.gif")
    gif_frames[0].save(gif, save_all=True, append_images=gif_frames[1:], duration=50, loop=0)
    print(gif)
