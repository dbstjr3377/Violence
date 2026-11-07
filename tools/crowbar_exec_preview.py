#!/usr/bin/env python3
"""
크로우바(빠루) 처형 인게임 시뮬레이션 (왼쪽: 플레이어 화면, 오른쪽: 관찰 카메라, 20fps, 게임 캡처 아님).

교도소 홀에서
 1) 들고 있던 크로우바를 NPC 에게 던짐(우클릭) → 근접 무기를 맞은 NPC 가 뒤로 넘어짐, 크로우바는 옆 바닥에 떨어짐
 2) 걸어가며 바닥 무기를 조준: 탄이 빈 M16 은 빨간 테두리, 크로우바는 흰 테두리 + 오른쪽 정보 카드
    (왼쪽 위 무기 종류, 이름, 오른쪽 아래 현재/최대 탄수 — GroundWeaponService 와 같은 배치)
 3) 크로우바를 주움(우클릭) → 쓰러진 NPC 에게 Space → 올라타 둔기 처형(왼클릭 3번)
게임과 같은 계산: 넘어짐(fall.json), 처형 동작·무기 위치(execution.json, ExecutionAnims.weapon), 처형 카메라·피(CombatService),
핏방울 탄도와 혈흔(BloodService), 처치 흑백 깜빡임.
결과: build-out/crowbar_exec/crowbar_exec.mp4, .gif, still_*.png
"""
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_animations as EA  # noqa: E402
import fall_preview as FPV  # noqa: E402
import fp_sim  # noqa: E402
import gameplay_preview as G  # noqa: E402
import grim_preview as GP  # noqa: E402
import kill_combo_preview as KC  # noqa: E402
import melee_kill_preview as MK  # noqa: E402
import tp_sim as T  # noqa: E402

ROOT = G.ROOT
NS = G.NS
OUT = os.path.join(ROOT, "build-out", "crowbar_exec")
OW, OH = G.OW, G.OH
FLOOR = G.FLOOR
EXEC = json.load(open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "execution.json"), encoding="utf-8"))
ANIM = EXEC["anims"]["blunt"]
GRIP = EXEC["grips"]["crowbar"]
ease, yaw_of, fwd = KC.ease, KC.yaw_of, KC.fwd

P_START = np.array([-24.0, FLOOR, 1.0])
NPC_START = np.array([-30.0, FLOOR, 1.5])
M16_POS = np.array([-26.4, FLOOR, 2.3])          # 탄이 빈 M16 (빨간 테두리)

T_THROW = 6
T_HIT = T_THROW + 5
T_LOOK_M16 = (18, 30)
T_WALK1 = (16, 40)
T_PICK = 44
T_WALK2 = (47, 58)
T_MOUNT = 61
T_CLICKS = (67, 78, 89)
TOTAL = 128
PICK_RANGE = 3.2

# 정보 카드 (GroundWeaponService 와 같음)
CARD_WIDTH, CARD_SCALE = 104, 0.3
CARD_BG = (20, 20, 22, 224)


def ray_box(eye, d, center, half, max_t):
    lo, hi = center - half, center + half
    t0, t1 = 0.0, max_t
    for i in range(3):
        if abs(d[i]) < 1e-9:
            if eye[i] < lo[i] or eye[i] > hi[i]:
                return -1
            continue
        a, b = (lo[i] - eye[i]) / d[i], (hi[i] - eye[i]) / d[i]
        a, b = min(a, b), max(a, b)
        t0, t1 = max(t0, a), min(t1, b)
        if t0 > t1:
            return -1
    return t0


def aimed(eye, f, pos):
    """GroundWeaponService.target: 조준선이 줍기 상자(0.9×0.6×0.9)를 지나는가"""
    return ray_box(eye, f, pos + np.array([0, 0.15, 0]), np.array([0.45, 0.3, 0.45]), PICK_RANGE) >= 0


def card_pos(item, look):
    """GroundWeaponService.cardPos: 무기 오른쪽(보는 사람 기준) + 조금 위"""
    f = np.array([look[0], 0, look[2]])
    f /= np.linalg.norm(f)
    right = np.array([-f[2], 0, f[0]])
    half = (CARD_WIDTH + 4) * 0.025 * CARD_SCALE / 2
    return item + right * (0.28 + half) + [0, 0.08, 0], right, half


def weapon_polys(fr):
    """exec_anims.preview 와 같음: 오른손 무기 (ExecutionAnims.weapon)"""
    m = json.load(open(os.path.join(NS, "models", "item", "weapon", "crowbar.json"), encoding="utf-8"))
    tex = Image.open(os.path.join(NS, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
    rx = lambda a: T.rx(math.radians(a[0])) @ T.ry(math.radians(a[1])) @ T.rz(math.radians(a[2]))
    body = T.rx(math.radians(fr["pitch"]))
    joint, _ = FPV.PARTS["arm_r"]
    local = np.array(joint) * FPV.PX + (rx(fr["arm_r"]) @ np.array([-FPV.PX, -10 * FPV.PX, 0, 1.0]))[:3]
    fist = (body @ np.array([*local, 1.0]))[:3] + np.array([0, fr["feet"][0], fr["feet"][1]])
    Rw = body @ rx(fr["arm_r"]) @ T.rx(math.pi) @ T.rx(math.radians(fr["wrist"])) @ T.ry(math.radians(fr["twist"]))
    s = 0.85 * 0.9375
    g = np.array(GRIP) / 16 - 0.5
    M = T.tr(*(fist - (Rw[:3, :3] @ (g * s)))) @ Rw @ T.sc(s, s, s)
    return T.item_polys(M, m, tex, {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]})


def puppet(fr, col, weapon=False):
    MK.set_fall_colors(col)
    p = []
    FPV.puppet_polys(fr, p)
    if weapon:
        p += weapon_polys(fr)
    return p


def draw_card(img, item, f_cam, eye, b, kind, name, ammo, empty):
    c, right, half = card_pos(item, f_cam)
    v0, v1 = G.to_view(c - right * half, eye, b), G.to_view(c + right * half, eye, b)
    if v0[2] > -0.1 or v1[2] > -0.1:
        return
    p0, p1 = fp_sim.project(v0), fp_sim.project(v1)
    w = abs(p1[0] - p0[0])
    if w < 8:
        return
    # 글자 px 단위로 그린 뒤 화면 크기로 줄임 (텍스트 디스플레이: 1px = 0.025블록 × 배율)
    k = 4
    cw, ch = (CARD_WIDTH + 4) * k, 46 * k
    card = Image.new("RGBA", (cw, ch), CARD_BG)
    d = ImageDraw.Draw(card)
    d.text((2 * k, 1 * k), kind, font=ImageFont.truetype(G.FONT_KR, 9 * k), fill=(184, 184, 200, 255))
    d.text((2 * k, 11 * k), name, font=ImageFont.truetype(G.FONT_KR, 14 * k), fill=(255, 255, 255, 255))
    if ammo:
        fnt = ImageFont.truetype(G.FONT_KR, 9 * k)
        tw = d.textlength(ammo, font=fnt)
        d.text((cw - 2 * k - tw, 35 * k), ammo, font=fnt, fill=(255, 48, 48, 255) if empty else (255, 255, 255, 255))
    h = int(round(w * ch / cw))
    card = card.resize((max(1, int(round(w))), max(1, h)), Image.LANCZOS)
    # 아래쪽 가운데가 카드 위치
    cx = (p0[0] + p1[0]) / 2
    cy = (p0[1] + p1[1]) / 2
    img.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height)))


def outline(img, mask, color):
    edge = np.asarray(mask.filter(ImageFilter.MaxFilter(5))) > 0
    ring = Image.fromarray((edge & (np.asarray(mask) == 0)).astype(np.uint8) * 255)
    img.paste(Image.new("RGBA", (OW, OH), color), (0, 0), ring)


def main():
    os.makedirs(OUT, exist_ok=True)
    _, _, bounds, grid, *_ = __import__("render_maps").load(os.path.join(ROOT, "build-out", "maps", "prison.txt"))
    world = GP.World(bounds, grid)
    blood = KC.Blood(world)
    hud = G.Hud()
    font = ImageFont.truetype(G.FONT_KR, 14)
    big = ImageFont.truetype(G.FONT_KR, 18)
    fist_frames = EA.anim_of("fist")
    bar_frames = EA.anim_of("crowbar")
    cb_model = json.load(open(os.path.join(NS, "models", "item", "weapon", "crowbar.json"), encoding="utf-8"))
    cb_tex = Image.open(os.path.join(NS, "textures", cb_model["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
    cb_disp = cb_model["display"]["thirdperson_righthand"]

    me, me_yaw, me_pitch = P_START.copy(), 0.0, 0.0
    npc = dict(feet=NPC_START.copy(), yaw=yaw_of(P_START - NPC_START), lying=None, dead=False)
    holding = "crowbar"
    thrown, ground_bar = None, None
    ex = None             # 처형: dict(at, yaw, face, cam, mode, t0, ...)
    flash, kills, score = -100, 6, 7400
    fp_anim = None
    states = []
    walk_from = None

    for tk in range(TOTAL):
        eye = me + [0, 1.62, 0]
        # ── 플레이어 이동·시선 ──
        if tk <= T_THROW:
            me_yaw, me_pitch = G.look_angles(eye, npc["feet"] + [0, 1.2, 0])
        elif T_WALK1[0] <= tk <= T_WALK1[1] and ground_bar is not None:
            if walk_from is None:
                walk_from = me.copy()
            to = ground_bar - walk_from
            to[1] = 0
            stop = ground_bar - to / np.linalg.norm(to) * 1.55
            stop[1] = FLOOR
            me = walk_from + (stop - walk_from) * ease(0, 1, (tk - T_WALK1[0]) / (T_WALK1[1] - T_WALK1[0]))
            eye = me + [0, 1.62, 0]
            if T_LOOK_M16[0] <= tk <= T_LOOK_M16[1]:
                me_yaw, me_pitch = G.look_angles(eye, M16_POS + [0, 0.1, 0])
            else:
                ty, tp = G.look_angles(eye, ground_bar + [0, 0.1, 0])
                if tk < T_LOOK_M16[0]:
                    ty, tp = G.look_angles(eye, npc["feet"] + [0, 0.3, 0])
                k = 0.45
                me_yaw, me_pitch = KC.lerp_angle(me_yaw, ty, k), me_pitch + (tp - me_pitch) * k
        elif T_WALK1[1] < tk < T_PICK:
            me_yaw, me_pitch = G.look_angles(eye, ground_bar + [0, 0.1, 0])
        elif T_WALK2[0] <= tk <= T_WALK2[1]:
            if tk == T_WALK2[0]:
                walk_from = me.copy()
            l = npc["lying"]
            vf = l.anchor(len(l.frames()) - 1, tk)
            head = l.head_world(tk)
            face = head - vf
            face[1] = 0
            face /= np.linalg.norm(face)
            goal = vf - face * 0.9
            goal[1] = FLOOR
            me = walk_from + (goal - walk_from) * ease(0, 1, (tk - T_WALK2[0]) / (T_WALK2[1] - T_WALK2[0]))
            eye = me + [0, 1.62, 0]
            me_yaw, me_pitch = G.look_angles(eye, vf + face * 0.9 + [0, 0.2, 0])

        # ── 1) 던지기 → 넘어짐 ──
        if tk == T_THROW:
            f, r, u = G.basis(me_yaw, me_pitch)
            holding = "fist"
            thrown = dict(start=eye + f * 0.5 + r * 0.25 - u * 0.25, end=npc["feet"] + [0, 1.2, 0], t0=tk, dur=T_HIT - T_THROW)
            fp_anim = (fist_frames, tk, 6)
        if tk == T_HIT:
            d = npc["feet"] - me
            d[1] = 0
            d /= np.linalg.norm(d)
            blood.spray(npc["feet"] + [0, 1.45, 0], d, 1)
            start = npc["feet"].copy()
            slide = start + d * 0.75

            def follow(t, s=start, e=slide, t0=tk):
                return s + (e - s) * ease(0, 1, (t - t0) / 6)
            npc["lying"] = KC.Lying("back", start, slide, npc["yaw"], yaw_of(-d), tk, follow)
            npc["feet"] = slide
            side = np.array([-d[2], 0, d[0]])
            ground_bar = start + d * 0.2 + side * 0.85
            ground_bar[1] = FLOOR
            thrown = None
        if tk == T_HIT + 7 and npc["lying"] is not None:
            npc["lying"].follow = None
            l = npc["lying"]
            l.start = l.end = npc["feet"].copy()

        # ── 2) 줍기 ──
        if tk == T_PICK:
            ground_bar = None
            holding = "crowbar"
            fp_anim = (bar_frames, tk, 5)

        # ── 3) 처형 (CombatService.startExecution) ──
        if tk == T_MOUNT:
            l = npc["lying"]
            vf = l.anchor(len(l.frames()) - 1, tk)
            head = l.head_world(tk)
            face = head - vf
            face[1] = 0
            face /= np.linalg.norm(face)
            at = vf + face * ANIM["anchor"]
            right = np.cross(face, [0, 1.0, 0])
            right /= np.linalg.norm(right)
            # CombatService: 처형 동작은 오른쪽 옆 위에서 처형자와 머리 사이를 봄
            mid = (at + head) / 2
            mid[1] = at[1]
            cam = mid + right * 2.4 - face * 0.5 + [0, 1.9, 0]
            ly, lp = G.look_angles(cam, mid + [0, 0.45, 0])
            ex = dict(at=at, yaw=yaw_of(face), face=face, vf=vf, vyaw=l.yaw, head=head, mode="ready", t0=tk, hits=3,
                      cam=(tuple(round(float(x), 4) for x in cam), round(ly, 3), round(lp, 3)), done=None)
            me = at.copy()
            me_yaw, me_pitch = ex["yaw"], 55
        if ex and tk in T_CLICKS:
            ex["mode"], ex["t0"] = "strike", tk
            ex["hits"] -= 1
        if ex and ex["mode"] == "strike" and tk == ex["t0"] + ANIM["strike"]["impact"]:
            last = ex["hits"] == 0
            head = ex["head"]
            out = head - ex["at"]
            out[1] = 0
            out /= np.linalg.norm(out)
            blood.spray(head, out * 0.8 + [0, 0.45, 0], 4 if last else 3)
            blood.decal(np.array([head[0], FLOOR, head[2]]), np.array([0, 1.0, 0]), None, f"blood_splat_{tk % 3}", 0.6, 0.6, tk, 160)
            if last:
                npc["dead"] = True
                l = npc["lying"]
                blood.pool(l.end, 1.6, tk)
                blood.head_flow(head, -fwd(l.yaw), tk)
                flash, kills, score = tk, kills + 1, score + 500
                ex["done"] = tk          # 처형 카메라는 끝나고, 인형은 치는 동작을 마저 함
        if ex and ex["mode"] == "strike" and tk >= ex["t0"] + len(ANIM["strike"]["exec"]) - 1:
            if ex["done"] is not None:
                ex["mode"] = "over"
            else:
                ex["mode"], ex["t0"] = "ready", tk
        blood.tick(tk)

        # ── 그릴 것 ──
        polys = []
        victim_only = []
        exec_cam = ex is not None and ex["done"] is None
        if ex and ex["mode"] != "over":
            if ex["mode"] == "ready":
                fe, fv = ANIM["ready"]["exec"], ANIM["ready"]["victim"]
            else:
                i = min(tk - ex["t0"], len(ANIM["strike"]["exec"]) - 1)
                fe, fv = ANIM["strike"]["exec"][i], ANIM["strike"]["victim"][i]
            if npc["dead"]:
                victim_only = npc["lying"].polys(tk, KC.NPC_COL)
            else:
                victim_only = MK.world_of(puppet(fv, KC.NPC_COL), ex["vf"], ex["vyaw"])
            polys += MK.world_of(puppet(fe, KC.ME_COL, weapon=True), ex["at"], ex["yaw"]) + victim_only
        else:
            if npc["lying"] is None:
                polys += MK.world_of(KC.figure(KC.NPC_COL, {"x": 0.05, "y": 0, "z": 0.03}, {"x": -0.05, "y": 0, "z": -0.03}),
                                     npc["feet"], npc["yaw"], 0.9375)
            else:
                polys += npc["lying"].polys(tk, KC.NPC_COL)
        me_polys = []
        if not (ex and ex["mode"] != "over"):
            item = (cb_model, cb_tex, cb_disp) if holding == "crowbar" else None
            right = {"x": -0.35, "y": -0.1, "z": 0.0} if holding == "crowbar" else {"x": 0.05, "y": 0, "z": 0.03}
            me_polys = MK.world_of(KC.figure(KC.ME_COL, right, {"x": -0.05, "y": 0, "z": -0.03}, item=item, rooster=True,
                                             head_pitch=min(40, me_pitch)), me, me_yaw, 0.9375)
        tpos = None
        if thrown:
            k = (tk - thrown["t0"]) / thrown["dur"]
            tpos = thrown["start"] + (thrown["end"] - thrown["start"]) * k + [0, 0.25 * math.sin(math.pi * k), 0]
        states.append(dict(tk=tk, eye=(me + [0, 1.62, 0]).copy(), yaw=me_yaw, pitch=me_pitch,
                           exec_cam=ex["cam"] if exec_cam else None, polys=polys, me=me_polys,
                           decals=blood.visible(tk), drops=[list(d) for d in blood.drops], thrown=tpos,
                           ground_bar=None if ground_bar is None else ground_bar.copy(), holding=holding,
                           flash=flash, kills=kills, score=score, fp_anim=fp_anim,
                           hits=ex["hits"] if exec_cam else None, victim_only=victim_only,
                           own_puppet=ex is not None and ex["mode"] != "over",
                           moving=(T_WALK1[0] <= tk <= T_WALK1[1]) or (T_WALK2[0] <= tk <= T_WALK2[1])))

    # ── 배경 광선 추적 ──
    def obs_cam(tk):
        if tk < T_WALK2[0]:
            e, t = np.array([-25.6, FLOOR + 2.7, -2.8]), np.array([-28.4, FLOOR + 0.4, 1.6])
        else:
            l = states[tk]
            e, t = np.array([-27.4, FLOOR + 2.0, -1.4]), np.array([-30.2, FLOOR + 0.4, 1.6])
        ly, lp = G.look_angles(e, t)
        return (tuple(float(x) for x in e), round(ly, 3), round(lp, 3))

    def main_cam(st):
        if st["exec_cam"]:
            return st["exec_cam"]
        bob = math.sin(st["tk"] * 0.9) * 0.035 if st["moving"] else 0.0
        return (tuple(round(float(x), 4) for x in st["eye"] + [0, bob, 0]), round(st["yaw"], 3), round(st["pitch"], 3))

    cams = set()
    for st in states:
        cams.add(main_cam(st))
        cams.add(obs_cam(st["tk"]))
    print(f"배경 {len(cams)}장 광선 추적 (4코어)...", flush=True)
    with Pool(4, initializer=MK._init) as pool:
        bg = {cam: (img, dep) for cam, img, dep in pool.map(MK._render, sorted(cams))}

    frames = []
    for st in states:
        tk = st["tk"]
        views = []
        for which, cam in (("main", main_cam(st)), ("obs", obs_cam(tk))):
            img_arr, dep = bg[cam]
            eye = np.array(cam[0])
            b = G.basis(cam[1], cam[2])
            img = Image.fromarray(img_arr).resize((OW, OH), Image.BILINEAR).convert("RGBA")

            def depth_fn(x, y, dep=dep):
                xi = int(min(GP.W - 1, max(0, x * GP.W / OW)))
                yi = int(min(GP.H - 1, max(0, y * GP.H / OH)))
                return float(dep[yi, xi])

            KC.draw_decals(img, st["decals"], eye, b, depth_fn)
            # 바닥 무기: 탄이 빈 M16, 떨어진 크로우바 (플레이어 화면에서 조준하면 테두리 + 정보 카드)
            f_me = G.basis(st["yaw"], st["pitch"])[0]
            target = None
            if which == "main" and not st["exec_cam"] and tk > T_HIT:
                cands = [("m16", M16_POS)] + ([("crowbar", st["ground_bar"])] if st["ground_bar"] is not None else [])
                for nm, pos in cands:
                    if aimed(st["eye"], f_me, pos):
                        target = (nm, pos)
            floor_items = [("m16", M16_POS, 25.0)]
            if st["ground_bar"] is not None:
                floor_items.append(("crowbar", st["ground_bar"], 70.0))
            for nm, pos, yw in floor_items:
                m = Image.new("L", (OW, OH), 0)
                M = G.rot_matrix(0, yw, 0) @ G.rot_matrix(-90, 0, 0)
                G.draw_world_model(img, depth_fn, nm, pos + [0, 0.06, 0], M, 0.6, eye, b, m)
                if target and target[0] == nm:
                    outline(img, m, (255, 50, 50, 255) if nm == "m16" else (255, 255, 255, 255))
            # 처형 카메라가 끝난 처형자 화면에는 자기 인형을 숨김 (FallService.finishExec)
            polys = (st["polys"] if which == "obs" or st["exec_cam"] or not st["own_puppet"] else st["victim_only"]) \
                + (st["me"] if which == "obs" else [])
            MK.char_layer(img, polys, eye, b, depth_fn)
            KC.draw_drops(img, st["drops"], eye, b, depth_fn)
            if st["thrown"] is not None:
                M = G.rot_matrix(0, -st["yaw"], 0) @ G.rot_matrix(tk * 55.0, 0, 0)
                G.draw_world_model(img, depth_fn, "crowbar", st["thrown"], M, 0.9, eye, b)
            if target:
                if target[0] == "m16":
                    draw_card(img, target[1], f_me, eye, b, "소총", "M16", "0 / 24", True)
                else:
                    draw_card(img, target[1], f_me, eye, b, "둔기", "크로우바", None, False)
            d = ImageDraw.Draw(img)
            if which == "main":
                if not st["exec_cam"]:
                    fa = st["fp_anim"]
                    fl = bar_frames if st["holding"] == "crowbar" else fist_frames
                    prog = max(0.0, (fa[1] + fa[2] - tk) / fa[2]) if fa and fa[0] is fl else 0.0
                    img.alpha_composite(G.fp_layer(G.frame_for(fl, prog)))
                if 0 <= tk - st["flash"] < 6:
                    arr = np.asarray(img.convert("RGB")).astype(np.float32) @ np.array([0.299, 0.587, 0.114])
                    arr = np.clip((arr - 70) * 1.35 + 110, 0, 255).astype(np.uint8)
                    img = Image.fromarray(np.repeat(arr[..., None], 3, axis=2)).convert("RGBA")
                    d = ImageDraw.Draw(img)
                label = "크로우바" if st["holding"] == "crowbar" else "맨손"
                if st["exec_cam"]:
                    label = f"왼클릭: 공격 ({st['hits']})   우클릭: 내리기"
                hud.draw(img, label, None, st["kills"], st["score"], crosshair=not st["exec_cam"])
                title = "플레이어 화면" + (" (처형 카메라)" if st["exec_cam"] else " (1인칭)")
            else:
                title = "관찰 카메라"
            d.text((10, 8), title, font=big, fill=(255, 220, 90))
            d.text((8, OH - 18), "시뮬레이션 (게임 캡처 아님)", font=font, fill=(255, 255, 255, 140))
            views.append(img.convert("RGB"))
        frame = Image.new("RGB", (OW * 2 + 4, OH))
        frame.paste(views[0], (0, 0))
        frame.paste(views[1], (OW + 4, 0))
        frames.append(frame)
        print(f"\r{tk + 1}/{TOTAL}", end="", flush=True)
    print()
    raw = os.path.join(OUT, "frames")
    os.makedirs(raw, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(os.path.join(raw, f"{i:03d}.png"))
    mp4 = os.path.join(OUT, "crowbar_exec.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "20", "-i", os.path.join(raw, "%03d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4], check=False)
    small = [f.resize((f.width // 2, f.height // 2), Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT,
                                                                              dither=Image.Dither.NONE) for f in frames]
    gif = os.path.join(OUT, "crowbar_exec.gif")
    small[0].save(gif, save_all=True, append_images=small[1:], duration=50, loop=0, optimize=True)
    stills = (T_HIT + 3, T_LOOK_M16[0] + 6, T_WALK1[1] + 2, T_MOUNT + 3, T_CLICKS[0] + 2, T_CLICKS[0] + 4, T_CLICKS[2] + 4, TOTAL - 8)
    for i, k in enumerate(stills):
        frames[k].save(os.path.join(OUT, f"still_{i + 1}.png"))
    print(mp4, os.path.getsize(mp4) // 1024 if os.path.exists(mp4) else 0, "KB")
    print(gif, os.path.getsize(gif) // 1024, "KB", len(frames), "장")


if __name__ == "__main__":
    main()
