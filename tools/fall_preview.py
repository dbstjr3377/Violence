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

import puppet_rig as RIG  # noqa: E402

# FallPose.Part: 관절(px), 관절→중심(px) — 팔다리는 두 마디 (puppet_rig.PARTS)
PARTS = {k: (v[1], v[2]) for k, v in RIG.PARTS.items()}
# build_pack.PUPPET_PARTS 와 같은 상자 (16 단위, 중심 8) — 색 번호 0/1
BOXES = {
    "head": [([4, 4, 4], [12, 12, 12], 0), ([3.9, 10, 3.9], [12.1, 12.1, 12.1], 1), ([3.9, 7.5, 11.9], [12.1, 10, 12.1], 1)],
    "body": [([4, 2, 6], [12, 14, 10], 0)],
    "arm_upper": [([6, 7, 6], [10, 11, 10], 0), ([6, 5, 6], [10, 7, 10], 1)],
    "forearm": [([6, 5, 6], [10, 11, 10], 1)],
    "leg_upper": [([6, 5, 6], [10, 11, 10], 0)],
    "shin": [([6, 7, 6], [10, 11, 10], 0), ([6, 5, 6], [10, 7, 10], 1)],
}
SKIN, HAIR, SHIRT, PANTS, SHOES = (200, 154, 122), (59, 42, 30), (60, 140, 150), (50, 50, 120), (34, 34, 34)


def set_colors(skin, hair, shirt, pants, shoes):
    global SKIN, HAIR, SHIRT, PANTS, SHOES, COLORS
    SKIN, HAIR, SHIRT, PANTS, SHOES = skin, hair, shirt, pants, shoes
    COLORS = {"head": (SKIN, HAIR), "body": (SHIRT, SHIRT), "arm_upper": (SHIRT, SKIN), "forearm": (SHIRT, SKIN),
              "leg_upper": (PANTS, SHOES), "shin": (PANTS, SHOES)}


set_colors(SKIN, HAIR, SHIRT, PANTS, SHOES)


def rot_xyz(a):
    return T.rx(math.radians(a[0])) @ T.ry(math.radians(a[1])) @ T.rz(math.radians(a[2]))


def load():
    return json.load(open(FALL, encoding="utf-8"))


MASK_SCALE = 0.625   # FallService.MASK_SCALE
_MASKS = {}


def mask_polys(M, mask):
    """가면 아이템 (FallService: 머리 자리에 HEAD 표시 아이템 디스플레이, 크기 = 인형 배율 × 0.625)"""
    from PIL import Image
    if mask not in _MASKS:
        ns = os.path.join(ROOT, "resourcepack", "assets", "violence")
        m = json.load(open(os.path.join(ns, "models", "item", "mask", mask + ".json"), encoding="utf-8"))
        tex = Image.open(os.path.join(ns, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
        _MASKS[mask] = (m, tex)
    m, tex = _MASKS[mask]
    return T.item_polys(M, m, tex, m.get("display", {}).get("head", {}))


def puppet_polys(frame, polys, mask=None):
    """FallPose.place 와 같은 계산 (puppet_rig) + 아이템 디스플레이의 Y180° (모델 +z 가 뒤쪽).
    mask(가면 모델 이름)가 있으면 머리 대신 가면 (게임과 같음: 머리 놓임 × 0.625, HEAD 표시)"""
    for name in RIG.PARTS:
        c, r = RIG.place(frame, name)
        M = np.eye(4)
        M[:3, :3] = r
        if name == "head" and mask:
            s = 0.9375 * MASK_SCALE
            polys += mask_polys(T.tr(*c) @ M @ T.ry(math.pi) @ T.sc(s, s, s), mask)
            continue
        M = T.tr(*c) @ M @ T.ry(math.pi) @ T.sc(0.9375, 0.9375, 0.9375)
        kind = RIG.PARTS[name][4]
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


def vanilla_sit_polys(polys, seat_y, head_pitch, head_snap=None):
    """바닐라 앉은 자세 (보이지 않는 디스플레이에 탄 마네킹): 다리 xRot -1.4137, yRot ±π/10, zRot ±0.0785, 팔 xRot -π/5"""
    root = T.tr(0, seat_y, 0) @ T.ry(math.pi) @ T.sc(-1, -1, 1) @ T.sc(0.9375, 0.9375, 0.9375) @ T.tr(0, -1.501, 0)
    hp = math.radians(head_pitch if head_snap is None else head_snap)
    head = root @ T.part(0, 0, 0, hp, 0, 0)
    T.cuboid(head, -4, -8, -4, 8, 8, 8, SKIN, polys)
    T.cuboid(head, -4, -8.01, -4.01, 8, 2.5, 8.02, HAIR, polys)
    T.cuboid(root @ T.part(0, 0, 0), -4, 0, -2, 8, 12, 4, SHIRT, polys)
    T.cuboid(root @ T.part(-5, 2, 0, -math.pi / 5, 0, 0), -3, -2, -2, 4, 12, 4, SHIRT, polys)
    T.cuboid(root @ T.part(5, 2, 0, -math.pi / 5, 0, 0), -1, -2, -2, 4, 12, 4, SHIRT, polys)
    T.cuboid(root @ T.part(-1.9, 12, 0, -1.4137167, math.pi / 10, 0.07853982), -2, 0, -2, 4, 12, 4, PANTS, polys)
    T.cuboid(root @ T.part(1.9, 12, 0, -1.4137167, -math.pi / 10, -0.07853982), -2, 0, -2, 4, 12, 4, PANTS, polys)


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


def wall_polys(polys, gap):
    """벽 (앉은 자리 뒤 gap)"""
    T.cuboid(np.eye(4), -24, 0, -gap * 16 - 8, 48, 40, 8, (90, 86, 80), polys)


def end_polys(polys, kind, data):
    fall = data["kinds"][kind]
    last = fall["frames"][-1]
    if fall["end"] == "face_up":
        tmp = []
        vanilla_back_polys(tmp, data["back_lift"])
        M = T.tr(0, 0, last["feet"][1])
        polys += [([(M @ np.array([*p, 1.0]))[:3] for p in pts], c) for pts, c in tmp]
    elif fall["end"] == "sit":
        vanilla_sit_polys(polys, data["seat_y"], data["sit_head_pitch"])
    else:
        puppet_polys({"pitch": 0, "feet": [0, 0]}, polys)


LABELS = {"back": "맞으면 뒤로 (공격 방향으로 밀림)", "blast": "샷건: 팔 벌리고 날아감", "wall": "벽에 부딪혀 기대 기절",
          "wall_death": "벽 기절 상태에서 죽음", "kick": "처형 발차기 (처형자)"}


if __name__ == "__main__":
    data = load()
    S = 230
    rows = []
    for name, kind in data["kinds"].items():
        frames = kind["frames"]
        wall = name in ("wall", "wall_death")
        cam = (2.6, 2.3, 1.9) if not wall else (3.0, 1.9, 2.4)
        look = (0, 0.6, 0.2) if not wall else (0, 0.6, 0.4)

        def scene_of(polys_fn):
            polys = []
            floor_polys(polys)
            if wall:
                wall_polys(polys, data["wall_gap"])
            polys_fn(polys)
            return polys

        def placed(fr):
            def f(polys):
                tmp = []
                puppet_polys(fr, tmp)
                # 벽: travel 로 맞은 자리(앞 1.4) → 앉을 자리
                dz = (1 - fr.get("travel", 1.0)) * 1.4 if name == "wall" else 0.0
                M = T.tr(0, 0, dz)
                polys += [([(M @ np.array([*p, 1.0]))[:3] for p in pts], c) for pts, c in tmp]
            return f

        idx = list(range(len(frames)))
        if len(idx) > 7:
            idx = [round(i * (len(frames) - 1) / 6) for i in range(7)]
        row = [draw(scene_of(placed(frames[0])), cam, S, LABELS[name], look=look)]
        for k in idx[1:]:
            row.append(draw(scene_of(placed(frames[k])), cam, S, f"{k + 1}프레임", look=look))
        while len(row) < 7:
            row.append(Image.new("RGB", (S, S), (34, 30, 40)))
        wire = []
        end_polys(wire, name, data)
        row.append(draw(scene_of(placed(frames[-1])), cam, S, "끝 + 대역(빨간 선)", look=look, wire=wire))
        row.append(draw(scene_of(lambda p: end_polys(p, name, data)), cam, S, "대역/실제 몸", look=look))
        rows.append(row)
    sheet = Image.new("RGB", (len(rows[0]) * S, len(rows) * S))
    for j, r in enumerate(rows):
        for i, t in enumerate(r):
            sheet.paste(t, (i * S, j * S))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "images", "fall.png")
    sheet.save(out)
    print(out)
