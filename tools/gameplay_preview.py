#!/usr/bin/env python3
"""
인게임 1인칭 플레이 시뮬레이션 GIF (게임 캡처가 아님).
교도소 복도(벅샷 룰렛 쉐이더)에서: 바닥의 M16 을 조준(하얀 테두리) → 우클릭으로 줍기 → NPC 에게 연사(몸통 명중 → 쓰러짐)
→ 다른 NPC 에게 우클릭으로 던지기(맞으면 쓰러짐) 순서로 진행한다.
 - 배경: 실제 생성된 교도소 맵 복셀 광선 추적 + violence_grim.glsl 계산 (grim_preview)
 - 1인칭 손/총: 리소스팩 모델과 쿨다운 프레임 그대로 (fp_sim), 연사 애니메이션 3틱(WeaponType.fireAnimTicks)
 - 연사: FireAccumulator 와 같은 누적 방식 860rpm, 탄 퍼짐 1.6°, 궤적은 Fx.tracer 시간표
 - 화면 흔들림: 연사 중 Shake.atLeast(0.3)
결과: build-out/gameplay/gameplay.gif
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dialog_preview as DP  # noqa: E402  (NPC 상자)
import export_animations as EA  # noqa: E402
import fp_gallery as FG  # noqa: E402
import fp_sim  # noqa: E402
import grim_preview as GP  # noqa: E402
import render_maps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
OUT = os.path.join(ROOT, "build-out", "gameplay")
FONT_KR = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")
OW, OH = 640, 360
GP.W, GP.H = 640, 360           # 배경 광선 추적 해상도
fp_sim.W, fp_sim.H = OW, OH     # 1인칭 모델/월드 물체 투영
GUI = 1.5                        # GUI 배율 (427x240)
FLOOR = 129.0

rng = random.Random(4)


# ───────────────────────── 카메라 ─────────────────────────

def basis(yaw, pitch):
    yr, pr = math.radians(yaw), math.radians(pitch)
    f = np.array([-math.sin(yr) * math.cos(pr), -math.sin(pr), math.cos(yr) * math.cos(pr)])
    r = np.cross(f, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return f, r, u


def to_view(p, eye, b):
    f, r, u = b
    d = np.asarray(p) - eye
    return [float(d @ r), float(d @ u), float(-(d @ f))]


def look_angles(eye, target):
    v = np.asarray(target) - eye
    return math.degrees(math.atan2(-v[0], v[2])), math.degrees(math.atan2(-v[1], math.hypot(v[0], v[2])))


# ───────────────────────── 배경 (맵 + 쉐이더) ─────────────────────────

def render_world(world, eye, yaw, pitch, s):
    d, fx, fy = GP.camera(yaw, pitch)
    t, cell, prev, axis, hit, step = world.trace(eye, d)
    loc = np.clip(cell - world.min, 0, np.array(world.kind.shape) - 1)
    base = world.col[loc[:, 0], loc[:, 1], loc[:, 2]]
    pl = np.clip(prev - world.min, 0, np.array(world.kind.shape) - 1)
    block = world.block[pl[:, 0], pl[:, 1], pl[:, 2]] / 15.0
    sky = world.sky[pl[:, 0], pl[:, 1], pl[:, 2]] / 15.0
    rows = np.arange(len(axis))
    up = (axis == 1) & (step[rows, 1] < 0)
    shade = np.where(axis == 0, 0.6, np.where(axis == 2, 0.8, np.where(up, 1.0, 0.5)))
    p = eye + d * t[:, None]
    q = np.floor(p * 4 + d * 1e-3)
    noise = 0.86 + 0.28 * (np.modf(np.sin(q @ np.array([12.99, 78.23, 37.71])) * 43758.5)[0] % 1.0)
    albedo = base * (shade * noise)[:, None]
    lit = albedo * GP.lightmap(block, sky)
    col = GP.grim_grade(lit, albedo, block, t, fx, fy, s)
    col = np.where(hit[:, None], col, GP.GRIM_FOG * 0.6)
    depth = np.where(hit, t, 1e9)
    # 매단 전구
    for lp in world.lamps:
        for lo, hi, c in ((lp + [0.31, 0.0, 0.31], lp + [0.69, 0.5, 0.69], (1.0, 0.86, 0.5)),
                          (lp + [0.47, 0.5, 0.47], lp + [0.53, 1.0, 0.53], (0.12, 0.12, 0.12))):
            with np.errstate(divide="ignore", invalid="ignore"):
                t0 = (lo - eye) / d
                t1 = (hi - eye) / d
            tn = np.nanmax(np.minimum(t0, t1), axis=1)
            tf = np.nanmin(np.maximum(t0, t1), axis=1)
            h = (tn <= tf) & (tn > 0) & (tn < depth)
            depth = np.where(h, tn, depth)
            col[h] = c
    return d, col, depth, (t, cell, axis, step, hit)


def world_hit(world, eye, direction, maxd=60.0):
    t, cell, prev, axis, hit, step = world.trace(eye, direction[None], maxd)
    if not hit[0]:
        return None
    p = eye + direction * float(t[0])
    n = np.zeros(3)
    n[axis[0]] = -step[0, axis[0]]
    return p, n, float(t[0])


# ───────────────────────── 월드 물체 (아이템 모델, 데칼) ─────────────────────────

MODEL_CACHE = {}


def item_quads(name):
    """아이템 모델 → 텍셀 단위 사각형 목록 (모델 좌표 /16 - 0.5)"""
    if name in MODEL_CACHE:
        return MODEL_CACHE[name]
    m = FG.load_model(name)
    tex_ref = m["textures"]["t"].split(":")[1]
    tex = Image.open(os.path.join(NS, "textures", tex_ref + ".png")).convert("RGBA")
    items = []
    ident = {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]}
    # render_items 를 원점 기준으로 돌려 사각형만 얻음 (뒷면 제거 전 단계가 필요해 직접 계산)
    tw, th = tex.size
    px = tex.load()
    quads = []
    for el in m["elements"]:
        a, b = el["from"], el["to"]
        for f, fd in el["faces"].items():
            tl, tr, bl = fp_sim.CORNERS[f](a, b)
            tl, tr, bl = (fp_sim.element_rot(list(p), el.get("rotation")) for p in (tl, tr, bl))
            u0, v0, u1, v1 = fd["uv"]
            x0, y0 = int(round(u0 / 16 * tw)), int(round(v0 / 16 * th))
            x1, y1 = int(round(u1 / 16 * tw)), int(round(v1 / 16 * th))
            nu, nv = max(1, x1 - x0), max(1, y1 - y0)
            # 큰 면은 2텍셀씩 묶어 속도 확보
            step_ = 2 if nu * nv > 64 else 1
            du = [(tr[k] - tl[k]) / nu for k in range(3)]
            dv = [(bl[k] - tl[k]) / nv for k in range(3)]
            light = fp_sim.LIGHT[f]
            for j in range(0, nv, step_):
                for i in range(0, nu, step_):
                    c = px[x0 + i, y0 + j]
                    if c[3] < 10:
                        continue
                    p0 = [tl[k] + du[k] * i + dv[k] * j for k in range(3)]
                    q = [p0, [p0[k] + du[k] * step_ for k in range(3)],
                         [p0[k] + du[k] * step_ + dv[k] * step_ for k in range(3)], [p0[k] + dv[k] * step_ for k in range(3)]]
                    quads.append((np.array(q) / 16.0 - 0.5, tuple(int(c[k] * light) for k in range(3))))
    _ = items, ident
    MODEL_CACHE[name] = quads
    return quads


def rot_matrix(rx, ry, rz):
    return np.array(fp_sim.mm(fp_sim.mm(fp_sim.rx(math.radians(rx)), fp_sim.ry(math.radians(ry))), fp_sim.rz(math.radians(rz))))


def draw_world_model(img, depth_fn, name, pos, M, scale, eye, b, mask=None):
    """월드에 놓인 아이템 모델을 그림 (배경 깊이로 가림 처리). mask 가 있으면 실루엣도 기록"""
    d = ImageDraw.Draw(img)
    polys = []
    for q, col in item_quads(name):
        w = (q * scale) @ M.T + pos
        v = [to_view(p, eye, b) for p in w]
        if any(p[2] > -0.05 for p in v):
            continue
        e1 = np.subtract(v[1], v[0])
        e2 = np.subtract(v[3], v[0])
        n = np.cross(e1, e2)
        cen = np.mean(v, axis=0)
        if n @ cen < 0:
            continue
        sp = [fp_sim.project(p) for p in v]
        dist = float(np.linalg.norm(np.mean(w, axis=0) - eye))
        cx, cy = np.mean(sp, axis=0)
        if dist > depth_fn(cx, cy) + 0.05:
            continue
        polys.append((cen[2], sp, col))
    polys.sort(key=lambda t: t[0])
    md = ImageDraw.Draw(mask) if mask is not None else None
    for _, sp, col in polys:
        d.polygon(sp, fill=col)
        if md:
            md.polygon(sp, fill=255)


def draw_decal(img, depth_fn, center, normal, radius, color, eye, b, seed, blobs=6):
    """표면에 납작한 얼룩 (혈흔/탄흔)"""
    n = normal / np.linalg.norm(normal)
    a = np.cross(n, [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0])
    a /= np.linalg.norm(a)
    c2 = np.cross(n, a)
    r = random.Random(seed)
    d = ImageDraw.Draw(img)
    for k in range(blobs):
        off = (a * r.uniform(-1, 1) + c2 * r.uniform(-1, 1)) * radius * (0.0 if k == 0 else 0.6)
        rad = radius * (1.0 if k == 0 else r.uniform(0.25, 0.5))
        pts = []
        for i in range(10):
            ang = i / 10 * math.tau
            w = center + n * 0.01 + off + (a * math.cos(ang) + c2 * math.sin(ang)) * rad * r.uniform(0.75, 1.15)
            v = to_view(w, eye, b)
            if v[2] > -0.05:
                break
            pts.append(fp_sim.project(v))
        if len(pts) < 10:
            continue
        cx, cy = np.mean(pts, axis=0)
        if np.linalg.norm(center - eye) > depth_fn(cx, cy) + 0.15:
            continue
        d.polygon(pts, fill=color)


def draw_tracer(img, start, end, age, eye, b):
    """Fx.tracer: 1틱째 총구에서 3블록 길이, 다음 틱에 끝 쪽으로 날아가 사라짐"""
    if age < 0 or age >= 3:
        return
    dirv = end - start
    ln = float(np.linalg.norm(dirv))
    dirv /= ln
    if age < 1:
        a0, a1, w = 0.0, min(3.0, ln), 0.035
    else:
        k = min(1.0, age - 1)
        a0, a1, w = (ln - 1.2) * k, 3.0 + (ln - 3.0) * k, 0.035 * (1 - 0.4 * k)
    p0, p1 = start + dirv * a0, start + dirv * a1
    v0, v1 = to_view(p0, eye, b), to_view(p1, eye, b)
    if v0[2] > -0.05 or v1[2] > -0.05:
        return
    s0, s1 = fp_sim.project(v0), fp_sim.project(v1)
    f = (OH / 2) / math.tan(math.radians(35))
    width = max(1, int(w * f / -v0[2]))
    d = ImageDraw.Draw(img)
    d.line([s0, s1], fill=(255, 205, 40), width=width)
    d.line([s0, s1], fill=(255, 250, 200), width=max(1, width // 3))


# ───────────────────────── NPC ─────────────────────────

def lying_boxes(feet, along, kind):
    """쓰러진 NPC: 등을 대고 누움 (along = 머리가 가는 방향 +x/-x)"""
    fx, fy, fz = feet
    s = 1 if along > 0 else -1
    bx = []

    def box(x0, y0, z0, x1, y1, z1, col, tag=""):
        xa, xb = fx + s * x0, fx + s * x1
        bx.append((np.array([min(xa, xb), fy + y0, fz + z0]), np.array([max(xa, xb), fy + y1, fz + z1]), np.array(col) / 255.0, tag))

    suit = (236, 236, 236) if kind == "npc" else (40, 70, 140)
    pants = (30, 30, 34) if kind == "npc" else (54, 54, 64)
    box(0.0, 0.0, -0.25, 0.75, 0.25, 0.0, pants)
    box(0.0, 0.0, 0.0, 0.75, 0.25, 0.25, pants)
    box(0.75, 0.0, -0.25, 1.5, 0.25, 0.25, suit)
    box(0.8, 0.0, -0.5, 1.5, 0.25, -0.25, suit)
    box(0.8, 0.0, 0.25, 1.5, 0.25, 0.5, suit)
    box(1.5, 0.0, -0.25, 2.0, 0.5, 0.25, DP.SKIN if kind == "npc" else (244, 242, 234), "face" if kind == "npc" else "")
    return bx


# ───────────────────────── HUD ─────────────────────────

class Hud:
    def __init__(self):
        g = lambda v: max(1, round(v * GUI))
        self.font = ImageFont.truetype(FONT_KR, g(10))
        self.bullet = Image.open(os.path.join(NS, "textures", "font", "bullet.png")).convert("RGBA").resize((g(5), g(8)), Image.NEAREST)
        self.skull = Image.open(os.path.join(NS, "textures", "font", "skull.png")).convert("RGBA").resize((g(8), g(8)), Image.NEAREST)
        self.star = Image.open(os.path.join(NS, "textures", "font", "star.png")).convert("RGBA").resize((g(9), g(9)), Image.NEAREST)

    def text_w(self, s):
        return self.font.getlength(s)

    def draw(self, img, weapon, ammo, kills, score):
        d = ImageDraw.Draw(img)
        cx = OW // 2
        # 보스바 상태 줄 (시간, 목표, 1위, 내 킬/점수)
        parts = [("02:41", (255, 255, 255)), ("   목표 30킬   ", (170, 170, 170)), (f"1위 Jacket {kills}", (255, 225, 77)),
                 ("   ", None), ("SKULL", None), (f" {kills}   ", (90, 230, 255)), ("STAR", None), (f" {score:,}", (90, 230, 255))]
        widths = [self.text_w(t) if c else (8 * GUI if t == "SKULL" else 9 * GUI) for t, c in parts]
        x = cx - sum(widths) / 2
        y = int(4 * GUI)
        for (t, c), w in zip(parts, widths):
            if t == "SKULL":
                img.alpha_composite(self.skull, (int(x), int(y + GUI)))
            elif t == "STAR":
                img.alpha_composite(self.star, (int(x), int(y)))
            elif c:
                d.text((x + GUI, y + GUI), t, font=self.font, fill=(40, 40, 40))
                d.text((x, y), t, font=self.font, fill=c)
            x += w
        # 액션바: 무기 + 탄약 (핫바 위)
        label = weapon
        bw = self.text_w(label) + (self.text_w(f"   {ammo}") + 6 * GUI if ammo is not None else 0)
        x = cx - bw / 2
        y = int(OH - 68 * GUI)
        d.text((x + GUI, y + GUI), label, font=self.font, fill=(40, 40, 40))
        d.text((x, y), label, font=self.font, fill=(255, 255, 255))
        if ammo is not None:
            x += self.text_w(label + "  ")
            img.alpha_composite(self.bullet, (int(x), int(y + GUI)))
            col = (255, 80, 80) if ammo == 0 else ((255, 225, 77) if ammo <= 6 else (255, 255, 255))
            d.text((x + 7 * GUI + GUI, y + GUI), str(ammo), font=self.font, fill=(40, 40, 40))
            d.text((x + 7 * GUI, y), str(ammo), font=self.font, fill=col)
        # 핫바 (첫 칸 선택)
        hw = 182 * GUI
        hx, hy = cx - hw // 2, OH - 22 * GUI
        d.rectangle([hx, hy, hx + hw, hy + 22 * GUI], fill=(20, 20, 20, 150), outline=(90, 90, 90, 200), width=max(1, round(GUI)))
        for i in range(1, 9):
            d.line([(hx + i * 20 * GUI, hy + GUI), (hx + i * 20 * GUI, hy + 21 * GUI)], fill=(70, 70, 70, 200), width=max(1, round(GUI)))
        d.rectangle([hx - GUI, hy - GUI, hx + 22 * GUI, hy + 23 * GUI], outline=(235, 235, 235, 255), width=max(1, round(GUI)))
        # 조준점
        c2 = (cx, OH // 2)
        d.line([(c2[0] - 9, c2[1]), (c2[0] + 9, c2[1])], fill=(255, 255, 255), width=2)
        d.line([(c2[0], c2[1] - 9), (c2[0], c2[1] + 9)], fill=(255, 255, 255), width=2)


# ───────────────────────── 1인칭 모델 ─────────────────────────

FP_CACHE = {}


def fp_layer(name):
    if name not in FP_CACHE:
        m = FG.load_model(name)
        tex_ref = m["textures"]["t"].split(":")[1]
        tex = Image.open(os.path.join(NS, "textures", tex_ref + ".png")).convert("RGBA")
        layer = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        items = []
        fp_sim.render_items(items, m, tex, m["display"]["firstperson_righthand"])
        items.sort(key=lambda t: t[0])
        for _, vq, col in items:
            d.polygon([fp_sim.project(v) for v in vq], fill=col + (255,))
        FP_CACHE[name] = layer
    return FP_CACHE[name]


def frame_for(frames, progress):
    for name, hi, lo in frames:
        if progress >= lo and progress > 0:
            return name
    return frames[-1][0]


# ───────────────────────── 시나리오 ─────────────────────────

def main():
    os.makedirs(OUT, exist_ok=True)
    _, _, bounds, grid, *_ = render_maps.load(os.path.join(ROOT, "build-out", "maps", "prison.txt"))
    world = GP.World(bounds, grid)
    hud = Hud()
    gun_frames = EA.anim_of("m16")
    fist_frames = EA.anim_of("fist")
    gun_anim = 3                                    # WeaponType.fireAnimTicks (860rpm)

    start_eye = np.array([-27.5, FLOOR + 1.62, 2.5])
    gun_pos = np.array([-23.0, FLOOR + 0.06, 2.6])
    gun_rot = rot_matrix(0, 35, 0) @ rot_matrix(0, 0, 90)       # 옆으로 눕힘 (GroundWeapon 표시)
    npc_a = {"feet": np.array([-17.0, FLOOR, 2.8]), "facing": -1, "kind": "npc", "down": None}
    npc_b = {"feet": np.array([-20.5, FLOOR, 5.6]), "facing": -1, "kind": "rooster", "down": None}

    # 시간표 (틱)
    T_WALK = (4, 22)          # 걸어가며 내려다봄
    T_PICK = 30               # 우클릭 줍기
    T_AIM = (33, 44)          # NPC A 조준
    T_FIRE = (46, 64)         # 연사
    T_TURN = (68, 82)         # NPC B 쪽으로
    T_THROW = 86
    TOTAL = 118

    eye = start_eye.copy()
    yaw, pitch = -90.0, 6.0
    holding = "fist"
    ammo = 24
    fire_start = None
    fist_start = None
    equip_start = -100
    acc_budget, last_shot = 0.0, -100
    tracers, holes, blood = [], [], []
    trauma, last_yaw_off, last_pitch_off = 0.0, 0.0, 0.0
    thrown = None
    kills, score = 3, 4200            # 게임 중반 느낌의 상태 표시
    frames = []

    def ease(a, b, t):
        t = min(1.0, max(0.0, t))
        t = t * t * (3 - 2 * t)
        return a + (b - a) * t

    look_gun = look_angles(np.array([-25.0, FLOOR + 1.62, 2.5]), gun_pos)
    for tk in range(TOTAL):
        # ── 플레이어 움직임 ──
        if T_WALK[0] <= tk <= T_WALK[1]:
            k = (tk - T_WALK[0]) / (T_WALK[1] - T_WALK[0])
            eye = start_eye + np.array([2.5 * k, 0, 0])
            pitch = ease(6.0, look_gun[1], k * 1.2)
        bob = math.sin(tk * 0.9) * 0.035 if T_WALK[0] <= tk <= T_WALK[1] else 0.0
        if T_AIM[0] <= tk <= T_AIM[1]:
            k = (tk - T_AIM[0]) / (T_AIM[1] - T_AIM[0])
            ty, tp = look_angles(eye, npc_a["feet"] + [0, 1.25, 0])
            yaw, pitch = ease(-90.0, ty, k), ease(look_gun[1], tp, k)
        if T_TURN[0] <= tk <= T_TURN[1]:
            k = (tk - T_TURN[0]) / (T_TURN[1] - T_TURN[0])
            ty0, tp0 = look_angles(eye, npc_a["feet"] + [0, 1.25, 0])
            ty, tp = look_angles(eye, npc_b["feet"] + [0, 1.2, 0])
            yaw, pitch = ease(ty0, ty, k), ease(tp0, tp, k)

        # ── 줍기 ──
        if tk == T_PICK:
            holding = "m16"
            equip_start = tk
        # ── 연사 (FireAccumulator: 860rpm) ──
        if T_FIRE[0] <= tk <= T_FIRE[1] and ammo > 0:
            per = 860 / 1200.0
            if tk - last_shot > math.ceil(1 / per) + 1:
                acc_budget = max(acc_budget, 1.0)
            else:
                acc_budget += per
            shots = int(acc_budget)
            if shots > 0:
                acc_budget -= shots
                last_shot = tk
                fire_start = tk
                trauma = max(trauma, 0.3)
                for _ in range(shots):
                    ammo -= 1
                    f, r, u = basis(yaw + last_yaw_off, pitch + last_pitch_off)
                    sp = math.radians(1.6) * 0.5
                    dirv = f + r * rng.gauss(0, sp) + u * rng.gauss(0, sp)
                    dirv /= np.linalg.norm(dirv)
                    muzzle = eye + f * 0.6 + r * 0.15 - u * 0.13
                    # NPC A 몸통 판정 (서 있을 때)
                    end = None
                    if npc_a["down"] is None:
                        boxes = DP.npc_boxes(npc_a["feet"], npc_a["facing"], npc_a["kind"])
                        nt, _ = DP.trace_boxes(eye, dirv[None], boxes)
                        wh = world_hit(world, eye, dirv)
                        if np.isfinite(nt[0]) and (wh is None or nt[0] < wh[2]):
                            end = eye + dirv * nt[0]
                            npc_a["down"] = tk
                            npc_a["feet"] = npc_a["feet"] + np.array([0.5, 0, 0])     # 뒤로 밀려남
                            blood.append((npc_a["feet"] + np.array([0.9, 0.0, 0.0]), np.array([0, 1.0, 0]), 0.45, 11))
                            blood.append((npc_a["feet"] + np.array([1.8, 0.0, 0.2]), np.array([0, 1.0, 0]), 0.3, 12))
                    if end is None:
                        wh = world_hit(world, eye, dirv)
                        if wh:
                            end = wh[0]
                            holes.append((wh[0], wh[1]))
                        else:
                            end = eye + dirv * 40
                    tracers.append((tk, muzzle, end))
        # ── 던지기 ──
        if tk == T_THROW:
            holding = "fist"
            fist_start = tk
            equip_start = -100
            f, r, u = basis(yaw, pitch)
            start = eye + f * 0.5 + r * 0.25 - u * 0.25
            target = npc_b["feet"] + np.array([0, 1.2, 0])
            thrown = {"start": start, "end": target, "t0": tk, "dur": max(3, int(np.linalg.norm(target - start) / 0.9))}
        if thrown and tk == thrown["t0"] + thrown["dur"] and npc_b["down"] is None:
            npc_b["down"] = tk
            npc_b["feet"] = npc_b["feet"] + np.array([0.4, 0, 0.2])
            thrown["landed"] = npc_b["feet"] + np.array([-0.8, 0.05, -0.6])
            kills += 0
            score += 0
        if npc_a["down"] == tk:
            score += 0

        # ── 흔들림 (Shake.tick) ──
        mag = trauma * trauma
        yoff = (rng.random() * 2 - 1) * mag * 5.0 if mag > 0.0005 else 0.0
        poff = (rng.random() * 2 - 1) * mag * 3.5 if mag > 0.0005 else 0.0
        last_yaw_off, last_pitch_off = yoff, poff
        trauma = max(0.0, trauma - 0.06)

        # ── 그리기 (시뮬레이션은 매 틱, 그림은 2틱마다 = 10fps) ──
        if tk % 2:
            continue
        cam_eye = eye + np.array([0, bob, 0])
        cy, cp = yaw + yoff, pitch + poff
        b = basis(cy, cp)
        s = 3.0 + tk / 20.0
        d, col, depth, _ = render_world(world, cam_eye, cy, cp, s)
        img = Image.fromarray((np.clip(col, 0, 1).reshape(GP.H, GP.W, 3) * 255).astype(np.uint8)).resize((OW, OH), Image.BILINEAR).convert("RGBA")
        dep = depth.reshape(GP.H, GP.W)

        def depth_fn(x, y):
            xi = int(min(GP.W - 1, max(0, x * GP.W / OW)))
            yi = int(min(GP.H - 1, max(0, y * GP.H / OH)))
            return float(dep[yi, xi])

        # NPC (엔티티: 쉐이더 색 없음)
        allboxes = []
        for n in (npc_a, npc_b):
            allboxes += DP.npc_boxes(n["feet"], n["facing"], n["kind"]) if n["down"] is None else lying_boxes(n["feet"], 1, n["kind"])
        nt, ncol = DP.trace_boxes(cam_eye, d, allboxes)
        arr = np.asarray(img.convert("RGB")).astype(float) / 255.0
        small = np.asarray(img.convert("RGB").resize((GP.W, GP.H), Image.BILINEAR)).reshape(-1, 3).astype(float) / 255.0
        front = nt < depth
        small[front] = ncol[front] * 0.95
        mask_npc = Image.fromarray((front.reshape(GP.H, GP.W) * 255).astype(np.uint8)).resize((OW, OH), Image.NEAREST)
        npc_img = Image.fromarray((np.clip(small, 0, 1).reshape(GP.H, GP.W, 3) * 255).astype(np.uint8)).resize((OW, OH), Image.NEAREST)
        img = Image.fromarray((arr * 255).astype(np.uint8)).convert("RGBA")
        img.paste(npc_img, (0, 0), mask_npc)
        dep_npc = np.minimum(dep, np.where(front, nt, 1e9).reshape(GP.H, GP.W))

        def depth_fn2(x, y):
            xi = int(min(GP.W - 1, max(0, x * GP.W / OW)))
            yi = int(min(GP.H - 1, max(0, y * GP.H / OH)))
            return float(dep_npc[yi, xi])

        # 혈흔, 탄흔
        for i, (c, n, rad, seed) in enumerate(blood):
            draw_decal(img, depth_fn, c, n, rad, (110, 6, 12, 255), cam_eye, b, seed)
        for i, (p, n) in enumerate(holes):
            draw_decal(img, depth_fn, p, n, 0.05, (20, 16, 14, 255), cam_eye, b, 100 + i, blobs=1)
        # 바닥 무기 (조준하면 하얀 테두리)
        if holding == "fist" and tk < T_PICK:
            m = Image.new("L", (OW, OH), 0)
            draw_world_model(img, depth_fn2, "m16", gun_pos, gun_rot, 0.9, cam_eye, b, m)
            f, _, _ = b
            to = gun_pos - cam_eye
            aimed = np.linalg.norm(np.cross(f, to)) / np.linalg.norm(to) < 0.35 and (to @ f) > 0
            if aimed:
                edge = Image.fromarray(np.where(np.asarray(m.filter(ImageFilter.MaxFilter(5))) > 0, 255, 0).astype(np.uint8))
                ring = Image.fromarray(((np.asarray(edge) > 0) & (np.asarray(m) == 0)).astype(np.uint8) * 255)
                white = Image.new("RGBA", (OW, OH), (255, 255, 255, 255))
                img.paste(white, (0, 0), ring)
        # 던진 총 (날아가며 회전)
        if thrown:
            k = (tk - thrown["t0"]) / thrown["dur"]
            if k < 1:
                pos = thrown["start"] + (thrown["end"] - thrown["start"]) * k + np.array([0, 0.25 * math.sin(math.pi * k), 0])
                M = rot_matrix(0, -yaw, 0) @ rot_matrix(tk * 55.0, 0, 0)
                draw_world_model(img, depth_fn2, "m16", pos, M, 0.9, cam_eye, b)
            elif "landed" in thrown:
                draw_world_model(img, depth_fn2, "m16", thrown["landed"], gun_rot, 0.9, cam_eye, b)
        # 궤적
        for t0, st, en in tracers:
            draw_tracer(img, st, en, tk - t0, cam_eye, b)
        # 1인칭 손/총 (쿨다운 프레임)
        if holding == "m16":
            prog = 0.0 if fire_start is None else max(0.0, (fire_start + gun_anim - tk) / gun_anim)
            layer = fp_layer(frame_for(gun_frames, prog))
            weapon, ammo_show = "M16", ammo
        else:
            prog = 0.0 if fist_start is None else max(0.0, (fist_start + 6 - tk) / 6)
            layer = fp_layer(frame_for(fist_frames, prog))
            weapon, ammo_show = "맨주먹", None
        # 손에 든 아이템이 바뀔 때 내려갔다 올라오는 동작 (바닐라)
        lower = 0
        if 0 <= tk - equip_start < 6:
            lower = int(OH * 0.35 * (1 - (tk - equip_start) / 6))
        img.alpha_composite(layer, (0, lower))
        hud.draw(img, weapon, ammo_show, kills, score)
        d2 = ImageDraw.Draw(img)
        d2.text((8, OH - 18), "시뮬레이션 (게임 캡처 아님)", font=ImageFont.truetype(FONT_KR, 13), fill=(255, 255, 255, 140))
        frames.append(img.convert("RGB"))
        print(f"\r{tk + 1}/{TOTAL}", end="", flush=True)
    print()
    pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    path = os.path.join(OUT, "gameplay.gif")
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=100, loop=0, optimize=True)
    for i, k in enumerate((10, 26, 46)):
        if k < len(frames):
            frames[k].save(os.path.join(OUT, f"still_{i + 1}.png"))
    print(path, os.path.getsize(path) // 1024, "KB", len(frames), "장")


if __name__ == "__main__":
    main()
