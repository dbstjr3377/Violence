#!/usr/bin/env python3
"""
근접 무기로 적을 쓰러뜨리는 인게임 시뮬레이션 (1인칭 | 3인칭 나란히, 20fps, 게임 캡처 아님).

교도소 홀에서 몽둥이를 든 플레이어가 NPC 에게 다가가
 1) 마주 보는 NPC A 를 오른쪽→왼쪽으로 휘둘러 처치 → 앞에서 맞았으므로 뒤로 넘어짐 (인형 6프레임 → 누운 대역)
 2) 이어서(연속 공격) 등을 돌린 NPC B 를 왼쪽→오른쪽으로 휘둘러 처치 → 맞은 쪽으로 돌아서며 뒤로 넘어짐
게임과 같은 계산을 씀:
 - 배경: 실제 생성된 교도소 맵 복셀 광선 추적 + 벅샷 룰렛 쉐이더 (grim_preview, gameplay_preview)
 - 1인칭: 리소스팩 모델과 쿨다운 프레임 (몽둥이 휘두르기 10틱, 연속 공격은 "<id>_b" 왼→오 프레임)
 - 3인칭: 바닐라 플레이어 모델 + 근접 대기/휘두르기 키프레임 (melee_tp.py: 왼손 주 손, 오른손 위, 오른팔 휘두르기)
 - 넘어짐: fall.json (FallPose 와 같은 계산) → 마지막 프레임 다음에 바닐라 자세의 대역
 - 베기 궤적: Fx.slash 와 같은 판 (1.7×1.0, 5틱)
화면: 1인칭 | 3인칭(바닐라 F5) | 옆에서 본 관찰 카메라
결과: build-out/melee_kill/melee_kill.gif, melee_kill.mp4, still_*.png
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_animations as EA  # noqa: E402
import fall_preview as FPV  # noqa: E402
import fp_sim  # noqa: E402
import gameplay_preview as G  # noqa: E402
import grim_preview as GP  # noqa: E402
import melee_tp as MT  # noqa: E402
import melee_tp_preview as MP  # noqa: E402
import models_melee  # noqa: E402
import render_maps  # noqa: E402
import tp_sim as T  # noqa: E402

ROOT = G.ROOT
OUT = os.path.join(ROOT, "build-out", "melee_kill")
OW, OH = G.OW, G.OH
FLOOR = G.FLOOR
WEAPON = "bat"
WEAPON_NAME = "몽둥이"
TP_DIST = 4.0                 # 바닐라 3인칭(뒤) 카메라 거리

# 시간표 (틱, 20fps)
T_WALK = (0, 12)
T_SWING1 = 15                 # 오→왼, NPC A (마주 봄)
T_TURN = (18, 25)
T_SWING2 = 27                 # 연속 공격 → 왼→오, NPC B (등을 돌림)
TOTAL = 58

START = np.array([-27.2, FLOOR, 2.5])
STOP = np.array([-24.8, FLOOR, 2.5])
NPC_A = {"feet": np.array([-23.15, FLOOR, 2.55]), "yaw": 90.0}      # 플레이어를 봄 (-X)
NPC_B = {"feet": np.array([-23.2, FLOOR, 4.1]), "yaw": -90.0}     # 등을 돌림 (+X 를 봄)

NPC_COL = {"skin": (226, 176, 136), "hair": (226, 176, 136), "shirt": (236, 236, 236), "pants": (30, 30, 34), "shoes": (20, 20, 20)}
ME_COL = {"skin": (226, 176, 136), "hair": (244, 242, 234), "shirt": (40, 70, 140), "pants": (54, 54, 64), "shoes": (30, 30, 30)}


# ───────────────────────── 장면 상태 ─────────────────────────

def ease(a, b, t):
    t = min(1.0, max(0.0, t))
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def look_at(eye, target):
    return G.look_angles(eye, target)


def player_state(tk):
    """(발 위치, yaw, pitch, 걷기 흔들림)"""
    k = (tk - T_WALK[0]) / (T_WALK[1] - T_WALK[0])
    feet = START + (STOP - START) * min(1.0, max(0.0, k))
    walking = T_WALK[0] <= tk < T_WALK[1]
    eye = feet + [0, 1.62, 0]
    ya, pa = look_at(eye, NPC_A["feet"] + [0, 1.2, 0])
    yb, pb = look_at(eye, NPC_B["feet"] + [0, 1.25, 0])
    if tk < T_TURN[0]:
        yaw, pitch = ya, pa
    else:
        t = (tk - T_TURN[0]) / (T_TURN[1] - T_TURN[0])
        yaw, pitch = ease(ya, yb, t), ease(pa, pb, t)
    bob = math.sin(tk * 0.9) * 0.035 if walking else 0.0
    return feet, yaw, pitch, bob


def cameras(tk):
    """(1인칭 눈, yaw, pitch), (3인칭 카메라, yaw, pitch) — 같은 자세면 배경을 다시 그리지 않음"""
    feet, yaw, pitch, bob = player_state(tk)
    eye = feet + [0, 1.62 + bob, 0]
    f, _, _ = G.basis(yaw, pitch)
    tp = feet + [0, 1.62, 0] - f * TP_DIST
    r = lambda v: tuple(round(float(x), 4) for x in v)  # noqa: E731
    return (r(eye), round(yaw, 3), round(pitch, 3)), (r(tp), round(yaw, 3), round(pitch, 3)), SIDE_CAM


# 옆에서 보는 관찰 카메라 (고정): 넘어지는 방향(X축)을 옆에서
_SIDE_EYE = np.array([-22.6, FLOOR + 1.9, -1.4])
_SIDE_LOOK = G.look_angles(_SIDE_EYE, np.array([-23.4, FLOOR + 0.75, 3.2]))
SIDE_CAM = (tuple(float(v) for v in _SIDE_EYE), round(_SIDE_LOOK[0], 3), round(_SIDE_LOOK[1], 3))


# ───────────────────────── 배경 (병렬) ─────────────────────────

_WORLD = None


def _init():
    global _WORLD
    _, _, bounds, grid, *_ = render_maps.load(os.path.join(ROOT, "build-out", "maps", "prison.txt"))
    _WORLD = GP.World(bounds, grid)


def _render(cam):
    eye, yaw, pitch = cam
    d, col, depth, _ = G.render_world(_WORLD, np.array(eye), yaw, pitch, 3.0)
    img = (np.clip(col, 0, 1).reshape(GP.H, GP.W, 3) * 255).astype(np.uint8)
    return cam, img, depth.reshape(GP.H, GP.W).astype(np.float32)


# ───────────────────────── 인물 (다각형) ─────────────────────────

def world_of(polys, feet, yaw, scale=1.0):
    M = T.tr(*feet) @ T.ry(math.radians(-yaw)) @ T.sc(scale, scale, scale)
    out = []
    for pts, col in polys:
        out.append(([(M @ np.array([*p, 1.0]))[:3] for p in pts], col))
    return out


def humanoid(col, arms=None, attack=0.0, charge=1.0, item=None, head_extra=True, mask="npc"):
    """서 있는 사람 (바닐라 모델 좌표, +Z 를 봄). arms=None 이면 팔을 내림, "melee" 면 근접 대기/휘두르기 자세"""
    root = T.entity_root(0)
    polys = []
    if arms == "melee":
        right, left, body_y, rpiv, lpiv = MT.arm_pose(True, attack, charge, attack_off=True)
    else:
        right, left, body_y, rpiv, lpiv = {"x": 0.05, "y": 0, "z": 0.03}, {"x": -0.05, "y": 0, "z": -0.03}, 0.0, (-5, 0), (5, 0)
    head = root @ T.part(0, 0, 0, 0, body_y, 0)
    body = root @ T.part(0, 0, 0, 0, body_y, 0)
    T.cuboid(head, -4, -8, -4, 8, 8, 8, col["skin"], polys)
    if mask == "npc":
        T.cuboid(head, -4.05, -5.2, -4.06, 8.1, 1.4, 0.3, (18, 18, 22), polys)          # 선글라스
    else:
        T.cuboid(head, -4.1, -8.1, -4.1, 8.2, 8.2, 8.2, (244, 242, 234), polys)        # 닭 가면
        T.cuboid(head, -0.8, -10.5, -3, 1.6, 2.6, 5, (220, 32, 38), polys)
        T.cuboid(head, -1, -4.2, -6.3, 2, 1.6, 2.3, (250, 196, 40), polys)
    T.cuboid(body, -4, 0, -2, 8, 12, 4, col["shirt"], polys)
    if mask == "npc":
        T.cuboid(body, -0.5, 0.2, -2.05, 1, 5, 0.1, (20, 20, 24), polys)               # 넥타이
    ra = root @ T.part(rpiv[0], 2, rpiv[1], right["x"], right["y"], right["z"])
    la = root @ T.part(lpiv[0], 2, lpiv[1], left["x"], left["y"], left["z"])
    T.cuboid(ra, -3, -2, -2, 4, 9, 4, col["shirt"], polys)
    T.cuboid(la, -1, -2, -2, 4, 9, 4, col["shirt"], polys)
    T.cuboid(ra, -3, 7, -2, 4, 3, 4, col["skin"], polys)
    T.cuboid(la, -1, 7, -2, 4, 3, 4, col["skin"], polys)
    T.cuboid(root @ T.part(-1.9, 12, 0), -2, 0, -2, 4, 10, 4, col["pants"], polys)
    T.cuboid(root @ T.part(1.9, 12, 0), -2, 0, -2, 4, 10, 4, col["pants"], polys)
    T.cuboid(root @ T.part(-1.9, 12, 0), -2, 10, -2, 4, 2, 4, col["shoes"], polys)
    T.cuboid(root @ T.part(1.9, 12, 0), -2, 10, -2, 4, 2, 4, col["shoes"], polys)
    if item:
        model, tex, disp = item
        polys += MP.item_polys(MT.hand_matrix(True, attack, charge, attack_off=True), model, tex, disp["thirdperson_lefthand"], True)
    return polys


def set_fall_colors(col):
    FPV.set_colors(col["skin"], col["hair"], col["shirt"], col["pants"], col["shoes"])


def fallen(npc, tk, kind, data):
    """처치된 NPC: 인형 프레임 → (마지막 한 틱 겹침) → 바닐라 자세 대역"""
    k = tk - npc["dead"]
    fall = data["kinds"][kind]
    frames, hold = fall["frames"], fall["hold_ticks"]
    polys = []
    set_fall_colors(NPC_COL)
    yaw = npc["fall_yaw"]
    if k < hold:
        FPV.puppet_polys(frames[min(k, len(frames) - 1)], polys)
        # 처음 3프레임에 걸쳐 맞은 쪽으로 돌아섬 (FallPose.spinYaw)
        t = min(1.0, k / 3.0)
        d = ((npc["fall_yaw"] - npc["yaw"]) % 360 + 540) % 360 - 180
        yaw = npc["yaw"] + d * t * t * (3 - 2 * t)
    elif fall["end"] == "face_up":
        FPV.vanilla_back_polys(polys, data["back_lift"])
    else:
        FPV.vanilla_lying_polys(polys)
    return world_of(polys, npc["feet"], yaw)


def char_layer(img, polys, eye, b, depth_fn, tint=(0.82, 0.86, 0.8)):
    """다각형 인물을 배경 깊이로 가려 그림 (화가 알고리즘 + 면 밝기)"""
    d = ImageDraw.Draw(img)
    light = np.array([0.35, 0.85, 0.4])
    light /= np.linalg.norm(light)
    items = []
    for pts, col in polys:
        v = [G.to_view(p, eye, b) for p in pts]
        if any(p[2] > -0.05 for p in v):
            continue
        sp = [fp_sim.project(p) for p in v]
        cen = np.mean(pts, axis=0)
        cx, cy = np.mean(sp, axis=0)
        if float(np.linalg.norm(cen - eye)) > depth_fn(cx, cy) + 0.15:
            continue
        n = np.cross(np.subtract(pts[1], pts[0]), np.subtract(pts[2], pts[0]))
        nn = np.linalg.norm(n)
        sh = 0.62 + 0.38 * abs(float(n @ light) / nn) if nn > 1e-9 else 0.8
        c = tuple(int(min(255, col[i] * sh * tint[i])) for i in range(3))
        items.append((float(np.mean([p[2] for p in v])), sp, c))
    items.sort(key=lambda t: t[0])
    for _, sp, c in items:
        d.polygon(sp, fill=c)


def slash_layer(img, eye_cam, b, origin, look, age, left_to_right):
    """Fx.slash: 시선 앞 1블록에 1.7×1.0 판, 3틱에 걸쳐 커지며 쓸고 5틱에 사라짐"""
    if age < 0 or age >= 5:
        return
    f, r, u = G.basis(*look)
    m = -1 if left_to_right else 1
    k = min(1.0, age / 3)
    center = origin + f * 1.0 - u * 0.1 + r * (-0.35 + 0.65 * k) * -m
    w, h = 1.7 * (0.45 + 0.55 * k), 1.0 * (0.8 + 0.2 * k)
    pts = []
    for i in range(13):
        a = math.pi * (0.1 + 0.8 * i / 12)
        pts.append(center + r * (-math.cos(a) * w / 2) * m + u * (math.sin(a) * h / 2 - h * 0.25))
    for i in range(12, -1, -1):
        a = math.pi * (0.1 + 0.8 * i / 12)
        pts.append(center + r * (-math.cos(a) * w / 2 * 0.86) * m + u * (math.sin(a) * h / 2 * 0.7 - h * 0.25))
    v = [G.to_view(p, eye_cam, b) for p in pts]
    if any(p[2] > -0.05 for p in v):
        return
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    alpha = int(170 * (1 - age / 5))
    ImageDraw.Draw(over).polygon([fp_sim.project(p) for p in v], fill=(255, 255, 255, alpha))
    img.alpha_composite(over)


def blood_burst(img, eye_cam, b, depth_fn, hit_point, push, age, seed):
    """맞은 자리에서 튀는 피 (중력, 8틱)"""
    if age < 0 or age > 8:
        return
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img)
    for _ in range(26):
        v0 = push * rng.uniform(0.08, 0.2) + rng.normal(0, 0.06, 3) + [0, rng.uniform(0.02, 0.12), 0]
        p = hit_point + v0 * age + np.array([0, -0.5 * 0.04 * age * age, 0])
        if p[1] < FLOOR + 0.02:
            continue
        vv = G.to_view(p, eye_cam, b)
        if vv[2] > -0.05:
            continue
        x, y = fp_sim.project(vv)
        if np.linalg.norm(p - eye_cam) > depth_fn(x, y) + 0.1:
            continue
        s = max(1.2, 8 / -vv[2])
        d.rectangle([x - s, y - s, x + s, y + s], fill=(150, 8, 14))


# ───────────────────────── 시나리오 ─────────────────────────

def main():
    os.makedirs(OUT, exist_ok=True)
    data = FPV.load()
    model, tex = MP.load(WEAPON)
    grip = models_melee.GRIP[WEAPON]
    stance = {False: MT.stance(grip), True: MT.stance(grip, left=True)}
    swings = {"r2l": MT.swing_frames(grip, "r2l"), "l2r": MT.swing_frames(grip, "l2r")}
    fp_frames = {"r2l": EA.anim_of(WEAPON), "l2r": EA.anim_of(WEAPON + "_b")}
    anim_ticks = EA.melee_ticks()[WEAPON]
    hud = G.Hud()

    # 배경: 서로 다른 카메라 자세만 병렬로 그림
    cams = set()
    for tk in range(TOTAL):
        cams.update(cameras(tk))
    print(f"배경 {len(cams)}장 광선 추적 (4코어)...", flush=True)
    with Pool(4, initializer=_init) as pool:
        bg = {cam: (img, dep) for cam, img, dep in pool.map(_render, sorted(cams))}

    a_state = dict(NPC_A, dead=None)
    b_state = dict(NPC_B, dead=None)
    swing = None          # (시작 틱, 종류)
    stance_left = False
    kills, score = 3, 4200
    decals = []
    bursts = []
    out_frames = []
    font = ImageFont.truetype(G.FONT_KR, 14)
    for tk in range(TOTAL):
        feet, yaw, pitch, bob = player_state(tk)
        eye_head = feet + [0, 1.62, 0]
        # ── 공격 (1인칭과 같은 판정: 클릭하는 틱에 바로 맞음, 근접 무기는 즉사) ──
        for t_sw, kind, npc in ((T_SWING1, "r2l", a_state), (T_SWING2, "l2r", b_state)):
            if tk != t_sw:
                continue
            swing = (tk, kind)
            push = npc["feet"] - feet
            push[1] = 0
            push /= np.linalg.norm(push)
            face = np.array([-math.sin(math.radians(npc["yaw"])), 0, math.cos(math.radians(npc["yaw"]))])
            fk = "back"                                                      # FallPose.kindFor: 언제나 뒤로 넘어짐
            fwd_yaw = math.degrees(math.atan2(-push[0], push[2]))
            npc.update(dead=tk, kind=fk, fall_yaw=fwd_yaw + 180)
            kills += 1
            score += 1000
            hit = npc["feet"] + [0, 1.3, 0]
            bursts.append((tk, hit, push, 7 + tk))
            torso = npc["feet"] + push * 0.85 + [0, 0.01, 0]
            decals.append((tk + 4, torso, 0.55, 30 + tk))
        # ── 3인칭 무기 상태 (GameService.tpSwing) ──
        item_disp, attack, charge = stance[stance_left], 0.0, 1.0
        if swing:
            k = tk - swing[0]
            if k < MT.SWING_TICKS:
                item_disp = swings[swing[1]][k]
                attack = (k + 0.5) / MT.SWING_TICKS
                charge = min(1.0, (k + 0.5) / MT.CHARGE_TICKS)
            else:
                stance_left = swing[1] == "r2l"
                item_disp = stance[stance_left]
        # ── 인물 다각형 ──
        npcs = []
        for npc in (a_state, b_state):
            if npc["dead"] is None:
                npcs += world_of(humanoid(NPC_COL), npc["feet"], npc["yaw"], 0.9375)
            else:
                npcs += fallen(npc, tk, npc["kind"], data)
        me = world_of(humanoid(ME_COL, "melee", attack, charge, (model, tex, item_disp), mask="rooster"), feet, yaw, 0.9375)

        views = []
        for which, cam in zip(("1인칭", "3인칭 (F5, 바닐라 거리 4블록)", "옆에서 본 모습"), cameras(tk)):
            img_arr, dep = bg[cam]
            eye = np.array(cam[0])
            b = G.basis(cam[1], cam[2])
            img = Image.fromarray(img_arr).resize((OW, OH), Image.BILINEAR).convert("RGBA")

            def depth_fn(x, y, dep=dep):
                xi = int(min(GP.W - 1, max(0, x * GP.W / OW)))
                yi = int(min(GP.H - 1, max(0, y * GP.H / OH)))
                return float(dep[yi, xi])

            for t0, c, rad, seed in decals:
                if tk >= t0:
                    grow = min(1.0, 0.4 + (tk - t0) / 20)
                    G.draw_decal(img, depth_fn, c, np.array([0, 1.0, 0]), rad * grow, (110, 6, 12, 255), eye, b, seed)
            polys = npcs + (me if which != "1인칭" else [])
            char_layer(img, polys, eye, b, depth_fn)
            for t0, hp, push, seed in bursts:
                blood_burst(img, eye, b, depth_fn, hp, push, tk - t0, seed)
            if swing:
                slash_layer(img, eye, b, eye_head, (yaw, pitch), tk - swing[0], swing[1] == "l2r")
            if which == "1인칭":
                prog = 0.0
                frames = fp_frames["r2l"]
                if swing:
                    prog = max(0.0, (swing[0] + anim_ticks - tk) / anim_ticks)
                    frames = fp_frames[swing[1]]
                img.alpha_composite(G.fp_layer(G.frame_for(frames, prog)))
            hud.draw(img, WEAPON_NAME, None, kills, score, crosshair=which == "1인칭")
            d = ImageDraw.Draw(img)
            d.text((10, 8), which, font=ImageFont.truetype(G.FONT_KR, 20), fill=(255, 220, 90))
            d.text((8, OH - 18), "시뮬레이션 (게임 캡처 아님)", font=font, fill=(255, 255, 255, 140))
            views.append(img.convert("RGB"))
        frame = Image.new("RGB", (OW * 3 + 8, OH), (0, 0, 0))
        for i, v in enumerate(views):
            frame.paste(v, (i * (OW + 4), 0))
        out_frames.append(frame)
    # 저장: MP4(선명), GIF(반 크기), 장면 몇 장
    raw = os.path.join(OUT, "frames")
    os.makedirs(raw, exist_ok=True)
    for i, f in enumerate(out_frames):
        f.save(os.path.join(raw, f"{i:03d}.png"))
    mp4 = os.path.join(OUT, "melee_kill.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "20", "-i", os.path.join(raw, "%03d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4], check=False)
    small = [f.resize((f.width * 2 // 3, f.height * 2 // 3), Image.LANCZOS).quantize(colors=160, method=Image.Quantize.MEDIANCUT,
                                                                                     dither=Image.Dither.NONE) for f in out_frames]
    gif = os.path.join(OUT, "melee_kill.gif")
    small[0].save(gif, save_all=True, append_images=small[1:], duration=50, loop=0, optimize=True)
    for i, k in enumerate((T_SWING1 + 2, T_SWING1 + 5, T_SWING2 + 2, T_SWING2 + 9)):
        out_frames[k].save(os.path.join(OUT, f"still_{i + 1}.png"))
    print(mp4, os.path.getsize(mp4) // 1024 if os.path.exists(mp4) else 0, "KB")
    print(gif, os.path.getsize(gif) // 1024, "KB", len(out_frames), "장")


if __name__ == "__main__":
    main()
