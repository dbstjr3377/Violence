#!/usr/bin/env python3
"""
공격 상체 애니메이션 → plugin-src/src/main/resources/attack.json (플러그인 FallService 의 공격 인형이 읽음)

바닐라는 서버가 플레이어 팔 각도를 정할 수 없어서, 공격하는 동안만 실제 몸을 숨기고 10부위 스킨 인형
(넘어짐·처형과 같은 FallPose 좌표, 두 마디 팔)이 상체 동작을 대신 한다. 다리·머리는 플러그인이 틱마다
실제 몸의 걸음과 시선을 따라 덮어쓴다.

 - 총 (총마다): 두 손으로 겨눈 자세에서 쏠 때 총구가 들리며 뒤로 밀렸다 돌아옴. 권총은 두 손 감싸 쥠.
   무기 회전: 총 모델 +Z(총열)가 몸 앞(+Z). 오른손 = 손잡이(HAND_POS 오른쪽), 왼손 = 총열 아래(HAND_POS 왼쪽)
 - 근접 (묶음별): A = 오른쪽 위로 젖혔다 왼쪽 아래로 (오→왼), B = 왼쪽 위로 젖혔다 오른쪽 아래로 (왼→오),
   찌르기. 둔기·중량 무기는 두 손, 가벼운 무기·칼은 한 손 (왼손은 몸 앞 가드).
   무기 회전은 exec_anims.weapon_rot: [θ(0 위, 90 앞, 180 아래), 좌우(+ 왼쪽), 굴림]
 - 프레임 w = [x, y, z, qx, qy, qz, qw]: 오른손이 쥐는 곳(몸 기준 블록)과 무기 회전
사용: python3 tools/attack_anims.py  (미리보기: --preview → build-out/attack_anims.png)
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exec_anims as E  # noqa: E402
import models_guns  # noqa: E402
import models_melee  # noqa: E402
import puppet_rig as R  # noqa: E402

OUT = os.path.join(E.ROOT, "plugin-src", "src", "main", "resources", "attack.json")
W = E.W_SCALE
ONE_HAND_GUNS = {"magnum", "silenced_pistol"}
TWO_HAND_GROUPS = {"blunt", "heavy"}


def rx(a):
    return R.rx(math.radians(a))


def realize(keys, length, left=None):
    """키 [(틱, {p: 쥐는 곳, rot: 무기 회전 행렬 또는 a: 각도, hand_l: 왼손 목표})] → 프레임"""
    out = []
    for k in E.track(keys, length):
        fr = E.pose()
        rot = np.asarray(k["rot"]) if "rot" in k else E.weapon_rot(k["a"])
        g = np.asarray(k["p"], float)
        R.ik_arm(fr, "r", g, k.get("pole_r", E.POLE_R))
        if left == "gun":
            R.ik_arm(fr, "l", g + rot @ np.asarray(k["lh"], float), k.get("pole_l", (0.6, -1.0, -0.2)))
        elif left == "both":
            R.ik_arm(fr, "l", g - rot @ np.array([0, E.LEFT_GAP, 0]), k.get("pole_l", E.POLE_L))
        else:
            R.ik_arm(fr, "l", k.get("guard", [0.12, 1.05, 0.28]), (1.0, -1.0, 0.0))
        fr["w"] = [*g, *E.quat(rot)]
        out.append(fr)
    return E.rnd(out)


# ───────────────────────── 총 ─────────────────────────

def gun_clip(gid):
    right, left = models_guns.HAND_POS[gid]
    lh = (np.array(left, float) - np.array(right, float)) / 16 * W   # 오른손 → 왼손 (무기 축)
    if gid in ONE_HAND_GUNS:
        aim = np.array([-0.10, 1.36, 0.50])     # 팔을 쭉 뻗은 두 손 권총 자세
        lh = np.array([0.03, -0.03, -0.02])      # 왼손이 오른손을 감쌈
        kick = (-16, 0.07)
    else:
        aim = np.array([-0.17, 1.24, 0.30])     # 개머리를 어깨에, 손잡이는 가슴 오른쪽 앞
        kick = (-9, 0.06) if gid not in ("shotgun", "double_barrel") else (-15, 0.10)
    keys = []
    for t, k in ((0, 1.0), (1, 0.75), (3, 0.3), (5, 0.08), (7, 0.0)):
        keys.append((t, {"p": list(aim + np.array([0, 0.02 * k, -kick[1] * k])), "rot": rx(kick[0] * k).tolist(), "lh": list(lh)}))
    return {"grip": list(right), "frames": realize(keys, 8, "gun")}


# ───────────────────────── 근접 ─────────────────────────

READY = ([-0.24, 1.10, 0.30], [25, -15, 0])


def swing_keys(side):
    """side=+1: 오→왼 (A), -1: 왼→오 (B)"""
    s = side
    rp, ra = READY
    if s < 0:
        rp, ra = [-rp[0] * 0.2, rp[1], rp[2]], [ra[0], -ra[1], 0]
    return [
        (0, {"p": rp, "a": ra}),
        (2, {"p": [-0.36 * s, 1.50, 0.02], "a": [-25, -55 * s, 0]}),     # 예비: 어깨 위로 젖힘
        (4, {"p": [-0.10 * s, 1.30, 0.55], "a": [85, -5 * s, 0]}),       # 타격: 정면
        (6, {"p": [0.28 * s, 1.00, 0.40], "a": [125, 65 * s, 0]}),       # 따라가기: 반대쪽 아래
        (9, {"p": rp, "a": ra}),
    ]


def stab_keys():
    return [
        (0, {"p": [-0.20, 1.15, 0.25], "a": [80, -5, 0]}),
        (2, {"p": [-0.22, 1.18, 0.10], "a": [78, -5, 0]}),
        (4, {"p": [-0.10, 1.30, 0.80], "a": [90, 0, 0]}),
        (6, {"p": [-0.10, 1.30, 0.78], "a": [90, 0, 0]}),
        (9, {"p": [-0.20, 1.15, 0.25], "a": [80, -5, 0]}),
    ]


def melee_clips():
    out = {}
    for group in set(E.GROUPS) | {"blunt"}:
        left = "both" if group in TWO_HAND_GROUPS else None
        out[group] = {"A": realize(swing_keys(+1), 10, left), "B": realize(swing_keys(-1), 10, left),
                      "STAB": realize(stab_keys(), 10, None)}
    return out


def build():
    groups = {}
    for g, ids in E.GROUPS.items():
        for i in ids:
            groups[i] = g
    data = {"_comment": "공격 상체 애니메이션 (tools/attack_anims.py 가 만듦 — 직접 고치지 말 것). 틱 단위 프레임.",
            "guns": {gid: gun_clip(gid) for gid in models_guns.HAND_POS},
            "melee": melee_clips(),
            "melee_group": groups,
            "melee_grips": {k: list(v) for k, v in models_melee.GRIP.items()}}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


if __name__ == "__main__":
    d = build()
    print("guns", len(d["guns"]), "melee groups", list(d["melee"]))


def preview(data):
    """앞 사선·옆에서 본 프레임 시트 → build-out/attack_anims.png"""
    from PIL import Image, ImageFont
    import fall_preview as FPV
    import melee_kill_preview as MK
    import tp_sim as T
    orig = T.item_polys

    def item_polys(M, model, tex, disp):   # 원소 x/y/z 회전(26.x)은 근사로 무시
        m = json.loads(json.dumps(model))
        for el in m["elements"]:
            if el.get("rotation") and "angle" not in el["rotation"]:
                el["rotation"] = None
        return orig(M, m, tex, disp)

    T.item_polys = item_polys
    S = 260
    grips = dict(data["melee_grips"])
    grips.update({g: v["grip"] for g, v in data["guns"].items()})
    rows = [("m16", data["guns"]["m16"]["frames"], [0, 1, 3, 7]),
            ("shotgun", data["guns"]["shotgun"]["frames"], [0, 1, 3, 7]),
            ("magnum", data["guns"]["magnum"]["frames"], [0, 1, 3, 7]),
            ("crowbar", data["melee"]["blunt"]["A"], [0, 2, 4, 6, 9]),
            ("crowbar", data["melee"]["blunt"]["B"], [0, 2, 4, 6, 9]),
            ("dagger", data["melee"]["blade"]["A"], [0, 2, 4, 6, 9])]
    sheet = Image.new("RGB", (6 * S, len(rows) * S), (34, 30, 40))
    for j, (wid, frames, picks) in enumerate(rows):
        for i, k in enumerate(picks):
            fr = frames[k]
            polys = []
            FPV.floor_polys(polys)
            MK.set_fall_colors(MK.ME_COL)
            ep = []
            FPV.puppet_polys(fr, ep)
            ep += E.weapon_polys(fr, wid, grips)
            polys += MK.world_of(ep, np.array([0.0, 0, 0]), 0)
            sheet.paste(FPV.draw(polys, (-2.4, 2.1, 2.9), S, f"{wid} {k}틱", look=(0, 0.9, 0.2)), (i * S, j * S))
        fr = frames[picks[1]]
        polys = []
        FPV.floor_polys(polys)
        ep = []
        FPV.puppet_polys(fr, ep)
        ep += E.weapon_polys(fr, wid, grips)
        polys += MK.world_of(ep, np.array([0.0, 0, 0]), 0)
        sheet.paste(FPV.draw(polys, (3.2, 1.5, 0.3), S, "옆", look=(0, 1.1, 0.3)), (5 * S, j * S))
    out = os.path.join(E.ROOT, "build-out", "attack_anims.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == "__main__" and "--preview" in sys.argv:
    preview(json.load(open(OUT, encoding="utf-8")))
