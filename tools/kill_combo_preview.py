#!/usr/bin/env python3
"""
세 명을 처치하는 인게임 시뮬레이션 (왼쪽: 플레이어 화면, 오른쪽: 관찰 카메라, 20fps, 게임 캡처 아님).

교도소 홀에서
 1) 매그넘으로 NPC A 를 쏨: 몸통 → 뒤로 넘어짐(공격 방향으로 밀림), 쓰러진 적을 한 발 더 → 처치
 2) 매그넘을 NPC B 에게 던짐 → 뒤로 넘어짐 → 다가가 Space 로 올라타 맨손 처형(왼클릭 4번) → 머리에서 피가 흐름
 3) NPC C 를 주먹으로 침 → 뒤쪽 벽에 부딪혀 벽에 기대 기절 → Space 로 머리 발차기 처형 → 벽 아래로 미끄러져 누움(전용 사망 모션)
게임과 같은 계산: 넘어짐/벽 기절/발차기(fall.json, FallService), 핏방울 탄도와 표면 혈흔·5초 뒤 사라짐(BloodService),
히트마커(총으로 맞히면 조준점), 처치 흑백 깜빡임(terrain 쉐이더: 블록만 흑백, 인물은 그대로), 처형 카메라(CombatService).
결과: build-out/kill_combo/kill_combo.mp4, kill_combo.gif, still_*.png
"""
import json
import math
import os
import random
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
import melee_kill_preview as MK  # noqa: E402
import tp_sim as T  # noqa: E402

ROOT = G.ROOT
NS = G.NS
OUT = os.path.join(ROOT, "build-out", "kill_combo")
OW, OH = G.OW, G.OH
FLOOR = G.FLOOR
DATA = FPV.load()
CFG = DATA
rng = random.Random(11)

NPC_COL = MK.NPC_COL
ME_COL = MK.ME_COL

# ───────────────────────── 장면 배치 (교도소 홀, 서쪽 벽 x=-37) ─────────────────────────
P_START = np.array([-24.0, FLOOR, 1.0])
NPC_POS = {"A": np.array([-30.5, FLOOR, 4.5]), "B": np.array([-31.0, FLOOR, -0.5]), "C": np.array([-35.55, FLOOR, 1.0])}

T_SHOT1, T_SHOT2 = 5, 13
T_TURN1 = (17, 26)
T_THROW = 28
T_WALK1 = (36, 62)
T_MOUNT = 64
T_PUNCHES = (70, 76, 82, 88)
T_TURN2 = (92, 100)
T_WALK2 = (100, 110)
T_PUNCH = 112
T_KICK = 127
TOTAL = 236


def ease(a, b, t):
    t = min(1.0, max(0.0, t))
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def yaw_of(v):
    return math.degrees(math.atan2(-v[0], v[2]))


def fwd(yaw):
    r = math.radians(yaw)
    return np.array([-math.sin(r), 0.0, math.cos(r)])


def lerp_angle(a, b, t):
    d = ((b - a) % 360 + 540) % 360 - 180
    return a + d * t


# ───────────────────────── 넘어짐 (FallService 와 같은 순서) ─────────────────────────

class Lying:
    """kind, 시작/끝 위치, 몸 방향 (startYaw → yaw), 시작 틱. 끝나기 한 틱 전부터 대역(바닐라 자세)"""

    def __init__(self, kind, start, end, start_yaw, yaw, t0, follow=None):
        self.kind, self.start, self.end, self.start_yaw, self.yaw, self.t0 = kind, start, end, start_yaw, yaw, t0
        self.fall = DATA["kinds"][kind]
        self.follow = follow      # 살아서 뒤로 넘어지면 실제 몸(밀려나는 위치)을 따라감: 함수(tick) → 위치
        self.head_snap = None

    def frames(self):
        return self.fall["frames"]

    def anchor(self, k, tk):
        if self.follow:
            return self.follow(tk)
        t = self.frames()[k].get("travel", 1.0)
        return self.start + (self.end - self.start) * t

    def yaw_at(self, k):
        if self.kind in ("wall_death", "kick"):
            return self.yaw
        t = min(1.0, k / 3.0)
        return lerp_angle(self.start_yaw, self.yaw, t * t * (3 - 2 * t))

    def polys(self, tk, col):
        k = tk - self.t0
        hold = self.fall["hold_ticks"]
        FPV_set(col)
        out = []
        if k < hold:
            fi = min(k, len(self.frames()) - 1)
            p = []
            FPV.puppet_polys(self.frames()[fi], p)
            out += MK.world_of(p, self.anchor(fi, tk), self.yaw_at(fi))
        if k >= hold - 1 and self.fall["end"] != "stand":
            p = []
            end = self.anchor(len(self.frames()) - 1, tk)
            if self.fall["end"] == "face_up":
                FPV.vanilla_back_polys(p, DATA["back_lift"])
                M = T.tr(0, 0, self.frames()[-1]["feet"][1])
                p = [([(M @ np.array([*q, 1.0]))[:3] for q in pts], c) for pts, c in p]
            else:
                FPV.vanilla_sit_polys(p, DATA["seat_y"], DATA["sit_head_pitch"], self.head_snap)
            out += MK.world_of(p, end, self.yaw)
        return out

    def head_world(self, tk):
        last = len(self.frames()) - 1
        fr = self.frames()[last]
        a = self.anchor(last, tk)
        # FallPose 머리 관절 (0,24px) + 회전 → 대략: 누우면 발에서 뒤로 1.64, 높이 lift
        if self.fall["end"] == "face_up":
            return a + fwd(self.yaw) * (fr["feet"][1] - 28 * FPV.PX) + [0, DATA["back_lift"], 0]
        return a + [0, DATA["seat_y"] + 28 * FPV.PX, 0]


def FPV_set(col):
    MK.set_fall_colors(col)


def wall_seat(world, start, push):
    d = push / np.linalg.norm(push)
    dist = 1e9
    for h in (0.45, 1.0):
        dd = d + [0, 1e-4, 0]           # 미리보기 광선 추적기는 완전 수평 광선에서 오류 → 아주 살짝 기울임
        r = G.world_hit(world, start + [0, h, 0], dd / np.linalg.norm(dd), 1.7)
        if r is None or r[2] < 0 or float(r[1] @ d) > -0.7:
            return None
        dist = min(dist, r[2])
    sit = start + d * (dist - DATA["wall_gap"])
    sit[1] = FLOOR
    return sit


# ───────────────────────── 피 (BloodService 와 같은 계산) ─────────────────────────

BLOOD_TEX = {}


def blood_tex(name, step):
    key = (name, step)
    if key not in BLOOD_TEX:
        BLOOD_TEX[key] = Image.open(os.path.join(NS, "textures", "fx", f"{name}_a{step}.png")).convert("RGBA")
    return BLOOD_TEX[key]


class Blood:
    def __init__(self, world):
        self.world = world
        self.drops = []       # [pos, vel, size, age]
        self.decals = []      # dict(center, along, normal, sx, sz, name, born, life, grow)

    def spray(self, point, d, intensity):
        bias = d / max(1e-6, np.linalg.norm(d))
        for _ in range(5 + intensity * 4):
            r = np.array([rng.gauss(0, 1), rng.gauss(0, 0.6), rng.gauss(0, 1)])
            r /= np.linalg.norm(r)
            v = bias * (1.4 + intensity * 0.2) + r + [0, 0.25, 0]
            v /= np.linalg.norm(v)
            speed = 0.18 + rng.random() * (0.18 + intensity * 0.06)
            size = 0.22 + rng.random() * (0.22 + intensity * 0.07)
            self.drops.append([point + r * 0.05, v * speed, size, 0])

    def decal(self, point, normal, along, name, sx, sz, tk, life, grow=None):
        n = normal / np.linalg.norm(normal)
        if along is None:
            ref = np.array([1.0, 0, 0]) if abs(n[1]) > 0.9 else np.array([0, 1.0, 0])
            along = np.cross(ref, n)
            a = rng.random() * math.tau
            along = along * math.cos(a) + np.cross(n, along) * math.sin(a)
        along = along - n * (along @ n)
        along /= np.linalg.norm(along)
        self.decals.append(dict(center=point + n * (0.011 + rng.random() * 0.008), along=along, normal=n, sx=sx, sz=sz,
                                name=name, born=tk, life=life, grow=grow))

    def pool(self, feet, size, tk):
        self.decal(np.array([feet[0], FLOOR, feet[2]]), np.array([0, 1.0, 0]), None, "blood_pool", size, size, tk, 18 * 20,
                   grow=(0.3, 40))

    def head_flow(self, head, direction, tk):
        f = np.array([direction[0], 0, direction[2]])
        f /= np.linalg.norm(f)
        self.decal(np.array([head[0], FLOOR, head[2]]), np.array([0, 1.0, 0]), f, "blood_flow", 1.5, 0.62, tk, 16 * 20,
                   grow=("flow", 70))

    def tick(self, tk):
        keep = []
        for d in self.drops:
            pos, vel, size, age = d
            age += 1
            if age > 50:
                continue
            ln = float(np.linalg.norm(vel))
            hit = G.world_hit(self.world, pos, vel / ln, ln) if ln > 1e-4 else None
            if hit is None and pos[1] + vel[1] <= FLOOR:
                t = (FLOOR - pos[1]) / vel[1] if vel[1] < 0 else 0
                hit = (pos + vel * t, np.array([0, 1.0, 0]), t)
            if hit is not None:
                p, n, _ = hit
                tang = vel - n * (vel @ n)
                glance = min(1.0, float(np.linalg.norm(tang)) / max(1e-4, ln))
                stretch = 1.0 + glance * glance * 2.4
                along = tang / np.linalg.norm(tang) if np.linalg.norm(tang) > 1e-6 else None
                c = p + (along * size * stretch * 0.28 if along is not None else 0)
                self.decal(c, n, along, f"blood_splat_{rng.randrange(4)}", size * stretch, size, tk, 100)
                continue
            keep.append([pos + vel, vel * 0.98 + [0, -0.045, 0], size, age])
        self.drops = keep

    def visible(self, tk):
        out = []
        for d in self.decals:
            age = tk - d["born"]
            if age < 0:
                continue
            step = 0 if age < d["life"] else (age - d["life"]) // 4 + 1
            if step >= 6:
                continue
            sx, sz, center = d["sx"], d["sz"], d["center"]
            g = d["grow"]
            if g == "flow" or (isinstance(g, tuple) and g[0] == "flow"):
                k = min(1.0, max(0.0, (age - 2) / g[1]))
                sx, sz = 0.18 + (d["sx"] - 0.18) * k, 0.12 + (d["sz"] - 0.12) * k
                center = d["center"] + d["along"] * (d["sx"] * 0.42 * k)
            elif g:
                k = min(1.0, age / g[1])
                s = g[0] + (1 - g[0]) * k
                sx, sz = d["sx"] * s, d["sz"] * s
            out.append((center, d["along"], d["normal"], sx, sz, d["name"], step))
        return out


def perspective_coeffs(dst, src):
    """dst(화면 4점) → src(텍스처 4점) PIL PERSPECTIVE 계수"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        B += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(B, float))


def draw_decals(img, decals, eye, b, depth_fn, tint=0.78):
    for center, along, normal, sx, sz, name, step in decals:
        z = np.cross(along, normal)
        corners = [center + along * (u - 0.5) * sx + z * (v - 0.5) * sz for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))]
        vv = [G.to_view(p, eye, b) for p in corners]
        if any(p[2] > -0.08 for p in vv):
            continue
        sp = [fp_sim.project(p) for p in vv]
        cx, cy = np.mean(sp, axis=0)
        if float(np.linalg.norm(center - eye)) > depth_fn(cx, cy) + 0.2:
            continue
        x0, y0 = int(max(0, min(p[0] for p in sp))), int(max(0, min(p[1] for p in sp)))
        x1, y1 = int(min(OW, max(p[0] for p in sp) + 1)), int(min(OH, max(p[1] for p in sp) + 1))
        if x1 - x0 < 1 or y1 - y0 < 1 or x1 - x0 > OW * 2:
            continue
        tex = blood_tex(name, step)
        W, H = tex.size
        src = [(0, 0), (W, 0), (W, H), (0, H)]
        try:
            co = perspective_coeffs([(p[0] - x0, p[1] - y0) for p in sp], src)
        except np.linalg.LinAlgError:
            continue
        patch = tex.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(co), Image.NEAREST)
        arr = np.asarray(patch).astype(np.float32)
        arr[..., :3] *= tint
        img.alpha_composite(Image.fromarray(arr.astype(np.uint8)), (x0, y0))


def draw_drops(img, drops, eye, b, depth_fn):
    d = ImageDraw.Draw(img)
    for pos, vel, size, age in drops:
        for p in (pos, pos + vel * 0.5):
            v = G.to_view(p, eye, b)
            if v[2] > -0.05:
                continue
            x, y = fp_sim.project(v)
            if np.linalg.norm(p - eye) > depth_fn(x, y) + 0.1:
                continue
            s = max(1.2, (0.9 + size) * 3.2 / -v[2])
            d.rectangle([x - s, y - s, x + s, y + s], fill=(150, 8, 14))


# ───────────────────────── 인물 ─────────────────────────

def whack(a):
    """맨손 주 손 휘두르기 (바닐라 WHACK, 오른팔). (오른팔, 왼팔, 몸통 yRot, 피벗)"""
    right, left = {"x": 0.0, "y": 0.0, "z": 0.0}, {"x": 0.0, "y": 0.0, "z": 0.0}
    body_y, rp, lp = 0.0, (-5.0, 0.0), (5.0, 0.0)
    if a > 0:
        body_y = math.sin(math.sqrt(a) * math.tau) * 0.2
        rp = (-math.cos(body_y) * 5, math.sin(body_y) * 5)
        lp = (math.cos(body_y) * 5, -math.sin(body_y) * 5)
        right["y"] += body_y
        left["y"] += body_y
        left["x"] += body_y
        g = math.sin((1 - (1 - a) ** 4) * math.pi)
        right["x"] -= g * 1.2 + math.sin(a * math.pi) * 0.7 * 0.75
        right["y"] += body_y * 2
        right["z"] += math.sin(a * math.pi) * -0.4
    return right, left, body_y, rp, lp


def figure(col, right, left, body_y=0.0, rp=(-5, 0), lp=(5, 0), item=None, rooster=False, head_pitch=0.0):
    root = T.entity_root(0)
    polys = []
    head = root @ T.part(0, 0, 0, math.radians(head_pitch), body_y, 0)
    body = root @ T.part(0, 0, 0, 0, body_y, 0)
    T.cuboid(head, -4, -8, -4, 8, 8, 8, col["skin"], polys)
    if rooster:
        T.cuboid(head, -4.1, -8.1, -4.1, 8.2, 8.2, 8.2, (244, 242, 234), polys)
        T.cuboid(head, -0.8, -10.5, -3, 1.6, 2.6, 5, (220, 32, 38), polys)
        T.cuboid(head, -1, -4.2, -6.3, 2, 1.6, 2.3, (250, 196, 40), polys)
    else:
        T.cuboid(head, -4.05, -5.2, -4.06, 8.1, 1.4, 0.3, (18, 18, 22), polys)
    T.cuboid(body, -4, 0, -2, 8, 12, 4, col["shirt"], polys)
    ra = root @ T.part(rp[0], 2, rp[1], right["x"], right["y"], right["z"])
    la = root @ T.part(lp[0], 2, lp[1], left["x"], left["y"], left["z"])
    T.cuboid(ra, -3, -2, -2, 4, 9, 4, col["shirt"], polys)
    T.cuboid(la, -1, -2, -2, 4, 9, 4, col["shirt"], polys)
    T.cuboid(ra, -3, 7, -2, 4, 3, 4, col["skin"], polys)
    T.cuboid(la, -1, 7, -2, 4, 3, 4, col["skin"], polys)
    for x in (-1.9, 1.9):
        T.cuboid(root @ T.part(x, 12, 0), -2, 0, -2, 4, 10, 4, col["pants"], polys)
        T.cuboid(root @ T.part(x, 12, 0), -2, 10, -2, 4, 2, 4, col["shoes"], polys)
    if item:
        model, tex, disp = item
        hand = ra @ T.rx(math.radians(-90)) @ T.ry(math.radians(180)) @ T.tr(1 / 16, 0.125, -0.625)
        polys += T.item_polys(hand, model, tex, disp)
    return polys


# ───────────────────────── 시나리오 ─────────────────────────

class Scene:
    def __init__(self, world):
        self.world = world
        self.blood = Blood(world)
        self.npc = {k: dict(feet=v.copy(), yaw=yaw_of(P_START - v), state="alive", lying=None, slide=None) for k, v in NPC_POS.items()}
        self.npc["C"]["yaw"] = -90.0       # 동쪽(플레이어 쪽)을 봄
        self.tracers = []
        self.hitmarks = []                  # (틱, 처치?)
        self.flash = -100
        self.kills, self.score = 3, 4200
        self.thrown = None
        self.landed = None
        self.exec = None                    # (종류, 시작 틱, 카메라)
        self.kick = None                    # Lying (처형자 발차기 인형)
        self.punch = None                   # 맨손 휘두르기 시작 틱 (3인칭)
        self.fp_anim = None                 # (프레임 목록, 시작, 길이)
        self.holding = "magnum"
        self.ammo = 6
        self.me = P_START.copy()
        self.me_yaw, self.me_pitch = 0.0, 0.0

    def knockdown(self, key, push, tk, strong=False):
        n = self.npc[key]
        push = np.array([push[0], 0, push[2]])
        push /= np.linalg.norm(push)
        start = n["feet"].copy()
        sit = wall_seat(self.world, start, push)
        yaw = yaw_of(-push)
        if sit is not None:
            n["lying"] = Lying("wall", start, sit, n["yaw"], yaw, tk)
            n["feet"] = sit
            n["state"] = "wall"
        else:
            kind = "blast" if strong else "back"
            slide_to = start + push * 0.75

            def follow(t, s=start, e=slide_to, t0=tk):
                return s + (e - s) * ease(0, 1, (t - t0) / 6)
            n["lying"] = Lying(kind, start, slide_to, n["yaw"], yaw, tk, follow)
            n["feet"] = slide_to
            n["state"] = "downed"

    def kill(self, key, tk, execution=False):
        n = self.npc[key]
        l = n["lying"]
        if l and l.kind == "wall":
            d = Lying("wall_death", l.end, l.end, l.yaw, l.yaw, tk)
            n["lying"] = d
        elif l:
            l.follow = None
            l.start = l.end = l.anchor(len(l.frames()) - 1, tk)
        n["state"] = "dead"
        n["dead_tick"] = tk
        n["exec"] = execution
        self.blood.pool(n["feet"] if not (l and l.kind == "wall") else l.end, 1.6 if execution else 1.1, tk)
        self.kills += 1
        self.score += 1000
        self.flash = tk

    def npc_polys(self, tk):
        out = []
        for key, n in self.npc.items():
            if n["lying"] is None:
                out += MK.world_of(figure(NPC_COL, {"x": 0.05, "y": 0, "z": 0.03}, {"x": -0.05, "y": 0, "z": -0.03}), n["feet"], n["yaw"], 0.9375)
            else:
                out += n["lying"].polys(tk, NPC_COL)
        return out


def main():
    os.makedirs(OUT, exist_ok=True)
    _, _, bounds, grid, *_ = __import__("render_maps").load(os.path.join(ROOT, "build-out", "maps", "prison.txt"))
    world = GP.World(bounds, grid)
    sc = Scene(world)
    hud = G.Hud()
    magnum_frames = EA.anim_of("magnum")
    fist_frames = EA.anim_of("fist")
    magnum_model = json.load(open(os.path.join(NS, "models", "item", "weapon", "magnum.json"), encoding="utf-8"))
    magnum_tex = Image.open(os.path.join(NS, "textures", magnum_model["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
    magnum_disp = {"rotation": [0, 150, 0], "translation": [0, 0, 0], "scale": [0.75, 0.75, 0.75]}
    hm_img = {k: Image.open(os.path.join(NS, "textures", "font", f"hitmarker{'_kill' if k else ''}.png")).convert("RGBA").resize((36, 36), Image.LANCZOS)
              for k in (False, True)}
    font = ImageFont.truetype(G.FONT_KR, 14)
    big = ImageFont.truetype(G.FONT_KR, 18)

    # ── 1) 시뮬레이션: 매 틱 상태 기록 ──
    states = []
    for tk in range(TOTAL):
        # 플레이어 움직임
        A, B, C = (sc.npc[k] for k in "ABC")
        if tk < T_TURN1[0]:
            tgt = A["feet"] + ([0, 1.1, 0] if tk < T_SHOT1 + 2 else [0, 0.35, 0])
            sc.me_yaw, sc.me_pitch = G.look_angles(sc.me + [0, 1.62, 0], tgt)
        elif tk < T_THROW + 1:
            t = (tk - T_TURN1[0]) / (T_TURN1[1] - T_TURN1[0])
            ya, pa = G.look_angles(sc.me + [0, 1.62, 0], A["feet"] + [0, 0.35, 0])
            yb, pb = G.look_angles(sc.me + [0, 1.62, 0], B["feet"] + [0, 1.2, 0])
            sc.me_yaw, sc.me_pitch = lerp_angle(ya, yb, ease(0, 1, t)), ease(pa, pb, t)
        elif T_WALK1[0] <= tk <= T_WALK1[1]:
            t = (tk - T_WALK1[0]) / (T_WALK1[1] - T_WALK1[0])
            goal = B["feet"] + (P_START - B["feet"]) / np.linalg.norm(P_START - B["feet"]) * 1.25
            goal[1] = FLOOR
            sc.me = P_START + (goal - P_START) * t
            sc.me_yaw, sc.me_pitch = G.look_angles(sc.me + [0, 1.62, 0], B["feet"] + [0, 0.2, 0])
        elif T_TURN2[0] <= tk <= T_WALK2[1]:
            stand = np.array([-33.75, FLOOR, 1.0])
            if tk == T_TURN2[0]:
                sc.walk2_from = sc.me.copy()
            t = (tk - T_TURN2[0]) / (T_WALK2[1] - T_TURN2[0])
            sc.me = sc.walk2_from + (stand - sc.walk2_from) * ease(0, 1, t)
            sc.me_yaw, sc.me_pitch = G.look_angles(sc.me + [0, 1.62, 0], C["feet"] + [0, 1.2, 0])
        elif tk > T_KICK + 13 and tk <= T_KICK + 24:
            # 처형 뒤 한 걸음 물러나 내려다봄
            if tk == T_KICK + 14:
                sc.back_from = sc.me.copy()
            l = C["lying"]
            sc.me = sc.back_from + fwd(l.yaw) * 1.2 * ease(0, 1, (tk - T_KICK - 14) / 10)
            sc.me_yaw, sc.me_pitch = G.look_angles(sc.me + [0, 1.62, 0], l.end + fwd(l.yaw) * 0.9 + [0, 0.2, 0])
        elif tk > T_KICK + 24:
            l = C["lying"]
            sc.me_yaw, sc.me_pitch = G.look_angles(sc.me + [0, 1.62, 0], l.end + fwd(l.yaw) * 0.9 + [0, 0.2, 0])
        elif tk > T_PUNCH and (sc.exec is None):
            tgt = (C["lying"].anchor(0, tk) + [0, 0.5, 0]) if C["lying"] else C["feet"] + [0, 1.0, 0]
            sc.me_yaw, sc.me_pitch = G.look_angles(sc.me + [0, 1.62, 0], tgt)
        eye = sc.me + [0, 1.62, 0]

        # 1) 총
        for ts in (T_SHOT1, T_SHOT2):
            if tk == ts:
                f, r, u = G.basis(sc.me_yaw, sc.me_pitch)
                hit = A["feet"] + ([0, 1.1, 0] if A["state"] == "alive" else [0, 0.3, 0])
                if A["state"] != "alive" and A["lying"]:
                    hit = A["lying"].anchor(5, tk) + fwd(A["lying"].yaw) * -0.8 + [0, 0.3, 0]
                d = hit - eye
                d /= np.linalg.norm(d)
                sc.tracers.append((tk, eye + f * 0.6 + r * 0.15 - u * 0.13, hit + d * 0.6))
                sc.blood.spray(hit, d, 2)
                sc.fp_anim = (magnum_frames, tk, 4)
                sc.ammo -= 1
                if A["state"] == "alive":
                    sc.knockdown("A", d, tk)
                    sc.hitmarks.append((tk, False))
                else:
                    sc.kill("A", tk)
                    sc.hitmarks.append((tk, True))
        # 2) 던지기 → 처형
        if tk == T_THROW:
            f, r, u = G.basis(sc.me_yaw, sc.me_pitch)
            sc.holding = "fist"
            sc.thrown = dict(start=eye + f * 0.5 + r * 0.25 - u * 0.25, end=B["feet"] + [0, 1.2, 0], t0=tk, dur=5)
            sc.fp_anim = (fist_frames, tk, 6)
            sc.punch = tk
        if sc.thrown and tk == sc.thrown["t0"] + sc.thrown["dur"]:
            d = B["feet"] - sc.me
            sc.blood.spray(B["feet"] + [0, 1.2, 0], d / np.linalg.norm(d), 1)
            sc.knockdown("B", d, tk)
            sc.landed = B["feet"] + np.array([1.0, 0.05, 0.4])
        if tk == T_MOUNT:
            vf = B["feet"]
            face = vf - sc.me
            face[1] = 0
            face /= np.linalg.norm(face)
            sc.me = vf - face * 0.25 + [0, 0.05, 0]
            sc.me_yaw, sc.me_pitch = yaw_of(face), 55
            cam = vf - face * 1.9 + [0, 2.5, 0]
            ly, lp = G.look_angles(cam, vf + [0, 0.4, 0])
            sc.exec = ("mount", tk, (tuple(round(float(x), 4) for x in cam), round(ly, 3), round(lp, 3)), 4)
        if sc.exec and sc.exec[0] == "mount" and tk in T_PUNCHES:
            sc.punch = tk
            vf = B["feet"]
            sc.blood.spray(vf + [0, 0.35, 0], np.array([0, -1.0, 0]) + fwd(sc.me_yaw) * 0.3, 4 if tk == T_PUNCHES[-1] else 2)
            sc.exec = (sc.exec[0], sc.exec[1], sc.exec[2], 4 - (T_PUNCHES.index(tk) + 1))
            if tk == T_PUNCHES[-1]:
                sc.kill("B", tk, execution=True)
                l = B["lying"]
                sc.blood.head_flow(l.head_world(tk), -fwd(l.yaw), tk)
                sc.exec_end = tk + 1
        if sc.exec and sc.exec[0] == "mount" and tk == getattr(sc, "exec_end", -1):
            sc.exec = None
        # 3) 주먹 → 벽 기절 → 발차기 처형
        if tk == T_PUNCH:
            sc.punch = tk
            sc.fp_anim = (fist_frames, tk, 8)
            d = C["feet"] - sc.me
            sc.blood.spray(C["feet"] + [0, 1.3, 0], d / np.linalg.norm(d), 1)
            sc.knockdown("C", d, tk)
        if tk == T_KICK:
            l = C["lying"]
            out = fwd(l.yaw)
            vf = l.end
            sc.me = vf + out * 0.6
            sc.me_yaw, sc.me_pitch = yaw_of(-out), 25
            sc.kick = Lying("kick", sc.me.copy(), sc.me.copy(), sc.me_yaw, sc.me_yaw, tk)
            side = np.cross(out, [0, 1.0, 0])
            side /= np.linalg.norm(side)
            mid = vf + out * 0.5
            cam = mid + side * 2.4 + out * 0.9 + [0, 1.3, 0]
            ly, lp = G.look_angles(cam, mid + [0, 0.8, 0])
            sc.exec = ("kick", tk, (tuple(round(float(x), 4) for x in cam), round(ly, 3), round(lp, 3)), None)
        contact = DATA["kinds"]["kick"]["contact"]
        if sc.kick and tk == T_KICK + contact:
            l = C["lying"]
            l.head_snap = -25
            head = l.head_world(tk) + [0, 0.15, 0]
            sc.blood.spray(head, -fwd(l.yaw) + [0, 0.15, 0], 4)
        if sc.kick and tk == T_KICK + contact + 1:
            sc.kill("C", tk, execution=True)
            sc.exec = None
        lc = C["lying"]
        if lc and lc.kind == "wall_death" and tk == lc.t0 + lc.fall["hold_ticks"] - 1:
            sc.blood.head_flow(lc.head_world(tk), -fwd(lc.yaw), tk)
        if sc.kick and tk >= sc.kick.t0 + sc.kick.fall["hold_ticks"]:
            sc.kick = None
        sc.blood.tick(tk)

        # 그릴 것 기록
        npcs = sc.npc_polys(tk)
        if sc.kick:
            me_polys = sc.kick.polys(tk, ME_COL)
        else:
            a = (tk - sc.punch) / 6 if sc.punch is not None and 0 <= tk - sc.punch < 6 else 0.0
            if sc.holding == "magnum":
                right, left = {"x": -1.4835 + math.radians(sc.me_pitch), "y": -math.pi / 6, "z": 0}, {"x": 0.0, "y": 0, "z": 0}
                fig = figure(ME_COL, right, left, item=(magnum_model, magnum_tex, magnum_disp), rooster=True, head_pitch=sc.me_pitch)
            else:
                right, left, by, rp, lp = whack(a)
                fig = figure(ME_COL, right, left, by, rp, lp, rooster=True, head_pitch=min(40, sc.me_pitch))
            me_polys = MK.world_of(fig, sc.me, sc.me_yaw, 0.9375)
        thrown_pos = None
        if sc.thrown:
            k = (tk - sc.thrown["t0"]) / sc.thrown["dur"]
            if k < 1:
                thrown_pos = sc.thrown["start"] + (sc.thrown["end"] - sc.thrown["start"]) * k + [0, 0.25 * math.sin(math.pi * k), 0]
        states.append(dict(
            tk=tk, eye=(sc.me + [0, 1.62, 0]).copy(), yaw=sc.me_yaw, pitch=sc.me_pitch, exec=sc.exec,
            npcs=npcs, me=me_polys, decals=sc.blood.visible(tk), drops=[list(d) for d in sc.blood.drops],
            tracers=list(sc.tracers), hitmarks=list(sc.hitmarks), flash=sc.flash, kills=sc.kills, score=sc.score,
            thrown=thrown_pos, landed=sc.landed, holding=sc.holding, ammo=sc.ammo, fp_anim=sc.fp_anim))

    # ── 2) 배경: 서로 다른 카메라만 병렬 광선 추적 ──
    def obs_cam(tk):
        if tk < 34:
            e = np.array([-34.0, FLOOR + 2.6, 6.2])
            t = np.array([-27.8, FLOOR + 0.6, 1.4])
        elif tk < 96:
            e = np.array([-27.2, FLOOR + 2.3, -2.6])
            t = np.array([-31.4, FLOOR + 0.5, -0.4])
        else:
            e = np.array([-34.2, FLOOR + 1.9, -1.9])
            t = np.array([-36.2, FLOOR + 0.7, 1.0])
        ly, lp = G.look_angles(e, t)
        return (tuple(float(x) for x in e), round(ly, 3), round(lp, 3))

    def main_cam(st):
        if st["exec"]:
            return st["exec"][2]
        bob = 0.0
        if T_WALK1[0] <= st["tk"] <= T_WALK1[1] or T_TURN2[0] <= st["tk"] <= T_WALK2[1] or T_KICK + 14 <= st["tk"] <= T_KICK + 24:
            bob = math.sin(st["tk"] * 0.9) * 0.035
        e = st["eye"] + [0, bob, 0]
        return (tuple(round(float(x), 4) for x in e), round(st["yaw"], 3), round(st["pitch"], 3))

    cams = set()
    for st in states:
        cams.add(main_cam(st))
        cams.add(obs_cam(st["tk"]))
    print(f"배경 {len(cams)}장 광선 추적 (4코어)...", flush=True)
    with Pool(4, initializer=MK._init) as pool:
        bg = {cam: (img, dep) for cam, img, dep in pool.map(MK._render, sorted(cams))}

    # ── 3) 합성 ──
    frames = []
    for st in states:
        tk = st["tk"]
        views = []
        for which, cam in (("main", main_cam(st)), ("obs", obs_cam(tk))):
            img_arr, dep = bg[cam]
            eye = np.array(cam[0])
            b = G.basis(cam[1], cam[2])
            base = img_arr
            flash = which == "main" and 0 <= tk - st["flash"] < 6
            if flash:
                # 처치 흑백 깜빡임: 블록(배경)만 흑백 — 인물은 엔티티라 색 그대로
                g = base.astype(np.float32) @ np.array([0.299, 0.587, 0.114])
                g = np.clip((g - 70) * 1.35 + 110, 0, 255)
                base = np.repeat(g[..., None], 3, axis=2).astype(np.uint8)
            img = Image.fromarray(base).resize((OW, OH), Image.BILINEAR).convert("RGBA")

            def depth_fn(x, y, dep=dep):
                xi = int(min(GP.W - 1, max(0, x * GP.W / OW)))
                yi = int(min(GP.H - 1, max(0, y * GP.H / OH)))
                return float(dep[yi, xi])

            draw_decals(img, st["decals"], eye, b, depth_fn)
            if st["landed"] is not None:
                G.draw_world_model(img, depth_fn, "magnum", st["landed"], G.rot_matrix(0, 35, 0) @ G.rot_matrix(0, 0, 90), 0.9, eye, b)
            polys = st["npcs"] + (st["me"] if (which == "obs" or st["exec"]) else [])
            MK.char_layer(img, polys, eye, b, depth_fn)
            draw_drops(img, st["drops"], eye, b, depth_fn)
            if st["thrown"] is not None:
                M = G.rot_matrix(0, -st["yaw"], 0) @ G.rot_matrix(tk * 55.0, 0, 0)
                G.draw_world_model(img, depth_fn, "magnum", st["thrown"], M, 0.9, eye, b)
            for t0, s0, e0 in st["tracers"]:
                G.draw_tracer(img, s0, e0, tk - t0, eye, b)
            d = ImageDraw.Draw(img)
            if which == "main":
                if not st["exec"]:
                    fa = st["fp_anim"]
                    frames_list = magnum_frames if st["holding"] == "magnum" else fist_frames
                    prog = 0.0
                    if fa and fa[0] is frames_list:
                        prog = max(0.0, (fa[1] + fa[2] - tk) / fa[2])
                    img.alpha_composite(G.fp_layer(G.frame_for(frames_list, prog)))
                label = "매그넘" if st["holding"] == "magnum" else "맨손"
                ammo = st["ammo"] if st["holding"] == "magnum" else None
                if st["exec"] and st["exec"][0] == "mount":
                    label, ammo = f"왼클릭: 공격 ({st['exec'][3]})   우클릭: 내리기", None
                elif st["exec"]:
                    label, ammo = "처형 중", None
                hud.draw(img, label, ammo, st["kills"], st["score"], crosshair=not st["exec"])
                for t0, kill in st["hitmarks"]:
                    if 0 <= tk - t0 < (5 if kill else 3) + 3:
                        age = tk - t0
                        hm = hm_img[kill]
                        if age >= (5 if kill else 3):
                            hm = hm.copy()
                            hm.putalpha(hm.getchannel("A").point(lambda v: v // 2))
                        img.alpha_composite(hm, (OW // 2 - 18, OH // 2 - 18))
                title = "플레이어 화면" + (" (처형 카메라)" if st["exec"] else " (1인칭)")
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
    mp4 = os.path.join(OUT, "kill_combo.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "20", "-i", os.path.join(raw, "%03d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4], check=False)
    small = [f.resize((f.width // 2, f.height // 2), Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT,
                                                                              dither=Image.Dither.NONE) for f in frames]
    gif = os.path.join(OUT, "kill_combo.gif")
    small[0].save(gif, save_all=True, append_images=small[1:], duration=50, loop=0, optimize=True)
    for i, k in enumerate((T_SHOT1 + 3, T_SHOT2 + 1, T_THROW + 7, T_PUNCHES[1], T_PUNCHES[-1] + 1, T_PUNCH + 12, T_KICK + 3, T_KICK + 14, 225)):
        frames[k].save(os.path.join(OUT, f"still_{i + 1}.png"))
    print(mp4, os.path.getsize(mp4) // 1024 if os.path.exists(mp4) else 0, "KB")
    print(gif, os.path.getsize(gif) // 1024, "KB", len(frames), "장")


if __name__ == "__main__":
    main()
