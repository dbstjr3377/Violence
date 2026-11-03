#!/usr/bin/env python3
"""
문 시뮬레이션 GIF (게임 캡처가 아님): 문을 몸으로 밀고 지나가기 → Space 발차기로 문 너머 적 쓰러뜨리기.
아파트 A동(벅샷 룰렛 쉐이더): 방 → 복도로 나가는 문(z=3)을 밀고 지나가 맞은편 집 문(z=-3)을 걷어참.
 - 문 물리: DoorPhysics / DoorService 를 틱 단위로 그대로 옮김
   (걸어서 밀기 9°/틱, 열린 문판에 몸이 닿으면 5.4°/틱, 발차기 34°/틱, 마찰 0.8, 최대 105°, 14°/틱 이상이면 부딪힌 사람이 쓰러짐)
 - 발차기: Space → 10틱 행동/이동 고정, 4틱 뒤 문을 참, 화면 흔들림 0.25 → 0.45 (1인칭에서는 다리가 보이지 않음: 바닐라와 같음)
 - 문은 아이템 디스플레이(엔티티)라 쉐이더 색이 입혀지지 않음, NPC 도 마찬가지
결과: build-out/door/door.gif
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gameplay_preview as G  # noqa: E402  (배경·HUD·1인칭·NPC 그리기 재사용, 640x360)
import dialog_preview as DP  # noqa: E402
import export_animations as EA  # noqa: E402
import fp_sim  # noqa: E402
import grim_preview as GP  # noqa: E402
import render_maps  # noqa: E402

ROOT = G.ROOT
NS = G.NS
OUT = os.path.join(ROOT, "build-out", "door")
OW, OH = G.OW, G.OH
rng = random.Random(9)

WALK_PUSH, KICK_PUSH = 9.0, 34.0
MAX_ANGLE, FRICTION, CLOSED_EPS, DANGER = 105.0, 0.80, 12.0, 14.0
SPEED = 0.29                      # 사람 이동 (블록/틱)


def rot_y(v, rad):
    """Vec3.rotateY 와 같은 규약"""
    c, s = math.cos(rad), math.sin(rad)
    return np.array([v[0] * c - v[2] * s, v[1], v[0] * s + v[2] * c])


class Door:
    """arena/Door.java + logic/DoorPhysics.java"""

    def __init__(self, bx, by, bz, along_x, hinge_max=False):
        self.bx, self.by, self.bz, self.along_x, self.hinge_max = bx, by, bz, along_x, hinge_max
        self.angle, self.vel = 0.0, 0.0
        self.last_pusher = None

    def hinge(self):
        if self.along_x:
            return np.array([self.bx + (1 if self.hinge_max else 0), self.by, self.bz + 0.5])
        return np.array([self.bx + 0.5, self.by, self.bz + (1 if self.hinge_max else 0)])

    def base_dir(self):
        return np.array([(-1 if self.hinge_max else 1), 0, 0.0]) if self.along_x else np.array([0, 0, (-1 if self.hinge_max else 1.0)])

    def normal(self):
        return np.array([0, 0, 1.0]) if self.along_x else np.array([1.0, 0, 0])

    def center(self):
        return np.array([self.bx + 0.5, self.by + 1, self.bz + 0.5])

    def dir(self):
        return rot_y(self.base_dir(), math.radians(self.angle))

    def sign_toward(self, side):
        closed_end = self.hinge() + self.base_dir()
        test = self.hinge() + rot_y(self.base_dir(), math.radians(5))
        moved = (test - closed_end) @ self.normal()
        return 1 if moved * side > 0 else -1

    def push_along(self, d, strength, pusher):
        side = 1 if d @ self.normal() >= 0 else -1
        target = self.sign_toward(side) * strength
        self.vel = max(self.vel, target) if target > 0 else min(self.vel, target)
        self.last_pusher = pusher

    def tick(self):
        self.angle += self.vel
        if self.angle > MAX_ANGLE:
            self.angle, self.vel = MAX_ANGLE, -self.vel * 0.2
        if self.angle < -MAX_ANGLE:
            self.angle, self.vel = -MAX_ANGLE, -self.vel * 0.2
        self.vel *= FRICTION
        if abs(self.vel) < 0.05:
            self.vel = 0.0

    def closed(self):
        return abs(self.angle) < CLOSED_EPS

    def dangerous(self):
        return abs(self.vel) >= DANGER

    def plane(self, p):
        return (p - self.center()) @ self.normal()

    def lateral(self, p):
        along = np.array([1.0, 0, 0]) if self.along_x else np.array([0, 0, 1.0])
        return abs((p - self.center()) @ along)

    def overlaps(self, p, r):
        """Obb.overlapsPoint: 문판(0.5, 1.0, 0.09 반크기) 과 점 + 반지름"""
        d = self.dir()
        c = self.hinge() + d * 0.5 + np.array([0, 1.0, 0])
        rel = p - c
        n = np.array([-d[2], 0, d[0]])
        a = abs(rel @ d) - 0.5
        b = abs(rel[1]) - 1.0
        t = abs(rel @ n) - 0.09
        return max(a, b, t) <= r


def turn(boxes, feet, to_z):
    """+x 를 바라보는(눕는) 상자들을 +z(to_z=1) 또는 -z(to_z=-1) 방향으로 90° 돌림"""
    out = []
    for lo, hi, c, tag in boxes:
        pts = []
        for x in (lo[0], hi[0]):
            for z in (lo[2], hi[2]):
                rx, rz = x - feet[0], z - feet[2]
                nx, nz = (-rz, rx) if to_z > 0 else (rz, -rx)
                pts.append((feet[0] + nx, feet[2] + nz))
        xs, zs = [q[0] for q in pts], [q[1] for q in pts]
        out.append((np.array([min(xs), lo[1], min(zs)]), np.array([max(xs), hi[1], max(zs)]), c, tag))
    return out


PASS_SPEED = 12.0


def push_out_of(d, point, r, sign):
    """Door.pushOutOf: 몸과 겹친 문판을 비켜날 때까지 돌리고, 남은 속도는 PASS_SPEED 이하"""
    if not d.overlaps(point, r):
        return False
    start = a = d.angle
    for _ in range(40):
        a = max(-MAX_ANGLE, min(MAX_ANGLE, a + sign * 3))
        d.angle = a
        if not d.overlaps(point, r) or abs(a) >= MAX_ANGLE:
            break
    d.vel = sign * min(PASS_SPEED, max(abs(d.vel), abs(a - start) * 0.5))
    return a != start


DOOR_TEX = None


def draw_door(img, depth_fn, door, eye, b):
    """문판: 경첩에서 dir 방향 1블록, 높이 2, 두께 0.125. 큰 면 두 장은 door.png 텍셀로"""
    global DOOR_TEX
    if DOOR_TEX is None:
        DOOR_TEX = Image.open(os.path.join(NS, "textures", "misc", "door.png")).convert("RGBA")
    tex = DOOR_TEX.load()
    tw, th = DOOR_TEX.size
    h, d = door.hinge(), door.dir()
    n = np.array([-d[2], 0, d[0]])
    up = np.array([0, 1.0, 0])
    polys = []
    for side, shade in ((1, 0.8), (-1, 0.62)):
        off = n * 0.0625 * side
        for j in range(th):
            for i in range(tw):
                c = tex[i, j]
                u0, u1 = i / tw, (i + 1) / tw
                v0, v1 = 2 - j / th * 2, 2 - (j + 1) / th * 2
                quad = [h + d * u0 + up * v0 + off, h + d * u1 + up * v0 + off, h + d * u1 + up * v1 + off, h + d * u0 + up * v1 + off]
                polys.append((quad, tuple(int(c[k] * shade) for k in range(3))))
    # 두께 면 (문 끝)
    end = h + d
    polys.append(([end + n * 0.0625, end - n * 0.0625, end - n * 0.0625 + up * 2, end + n * 0.0625 + up * 2], (60, 38, 22)))
    polys.append(([end + n * 0.0625 + up * 2, end - n * 0.0625 + up * 2, h - n * 0.0625 + up * 2, h + n * 0.0625 + up * 2], (90, 58, 32)))
    drawn = []
    for quad, col in polys:
        v = [G.to_view(p, eye, b) for p in quad]
        if any(p[2] > -0.05 for p in v):
            continue
        sp = [fp_sim.project(p) for p in v]
        cx, cy = np.mean(sp, axis=0)
        dist = float(np.linalg.norm(np.mean(quad, axis=0) - eye))
        if dist > depth_fn(cx, cy) + 0.08:
            continue
        drawn.append((float(np.mean([p[2] for p in v])), sp, col))
    drawn.sort(key=lambda t: t[0])
    dr = ImageDraw.Draw(img)
    for _, sp, col in drawn:
        dr.polygon(sp, fill=col)


def main():
    os.makedirs(OUT, exist_ok=True)
    _, _, bounds, grid, *_ = render_maps.load(os.path.join(ROOT, "build-out", "maps", "apartment_a.txt"))
    world = GP.World(bounds, grid)
    hud = G.Hud()
    fist_frames = EA.anim_of("fist")
    FLOOR = 129.0
    door_a = Door(-26, 129, 3, True)        # 방 → 복도
    door_b = Door(-26, 129, -3, True)       # 맞은편 집 (안에 NPC)
    doors = [door_a, door_b]
    npc = {"feet": np.array([-25.72, FLOOR, -3.45]), "facing": 1, "kind": "npc", "down": None, "slide": np.zeros(3)}

    pos = np.array([-25.5, FLOOR, 7.2])
    yaw, pitch = 180.0, 4.0                 # 북쪽(-z)을 봄
    stop_z = -1.55                          # 발차기 위치 (문 B 앞)
    T_WALK = 6
    T_KICK = 52
    TOTAL = 96
    trauma, last_yoff, last_poff = 0.0, 0.0, 0.0
    lock_until = -1
    kicked = False
    frames = []
    walking = False
    for tk in range(TOTAL):
        # ── 플레이어 이동 (닫힌 문에는 보이지 않는 벽) ──
        walking = tk >= T_WALK and pos[2] > stop_z and tk >= lock_until
        if walking:
            nxt = pos + np.array([0, 0, -SPEED])
            for d in doors:
                blocked = d.closed() and d.vel == 0
                if blocked and d.lateral(nxt) < 0.75:
                    # 문 블록(z: bz..bz+1)에 몸(반폭 0.3)이 들어가지 못함
                    if d.bz - 0.3 < nxt[2] < d.bz + 1 + 0.3 and pos[2] >= d.bz + 1 + 0.3 - 1e-6:
                        nxt[2] = d.bz + 1 + 0.3
            pos = nxt if nxt[2] >= stop_z else np.array([pos[0], pos[1], stop_z])
        # ── 문 (DoorService.tick) ──
        for d in doors:
            for who, p, alive in (("player", pos, True), ("npc", npc["feet"], npc["down"] is None)):
                if not alive:
                    continue
                if abs(p[1] - d.by) > 1.2 or d.lateral(p) > 0.75:
                    continue
                plane = d.plane(p)
                if abs(plane) > 1.0:
                    continue
                pushing = who == "player" and walking
                if d.closed():
                    if pushing and abs(plane) < 0.95:
                        d.push_along(-d.normal() * np.sign(plane), WALK_PUSH, who)
                elif d.overlaps(p + np.array([0, 0.9, 0]), 0.32):
                    if d.dangerous() and d.last_pusher != who:
                        if who == "npc":
                            npc["down"] = tk
                            away = p - d.hinge()
                            away[1] = 0
                            npc["slide"] = away / max(1e-6, np.linalg.norm(away)) * 0.8
                            d.vel *= 0.5
                    else:
                        away = p - d.hinge()
                        tangent = np.array([-d.dir()[2], 0, d.dir()[0]])
                        side = -1 if away @ tangent >= 0 else 1
                        pd = tangent * side
                        toward = 1 if pd @ d.normal() >= 0 else -1
                        if push_out_of(d, p + np.array([0, 0.9, 0]), 0.32, d.sign_toward(toward)):
                            d.last_pusher = who
            d.tick()
        # ── 발차기 (CombatService.kick) ──
        if tk == T_KICK:
            lock_until = tk + 10
            trauma = min(1.0, trauma + 0.25)
        if tk == T_KICK + 4 and not kicked:
            kicked = True
            dv = door_b.center() - pos
            dv[1] = 0
            door_b.push_along(dv / np.linalg.norm(dv), KICK_PUSH, "player")
            trauma = min(1.0, trauma + 0.45)
        # 쓰러진 NPC 밀려남 (applySlide: 0.7 감쇠)
        if npc["down"] is not None and np.linalg.norm(npc["slide"]) > 0.02:
            npc["feet"] = npc["feet"] + npc["slide"] * 0.3
            npc["slide"] = npc["slide"] * 0.7
        # ── 흔들림 (Shake.tick) ──
        mag = trauma * trauma
        yoff = (rng.random() * 2 - 1) * mag * 5.0 if mag > 0.0005 else 0.0
        poff = (rng.random() * 2 - 1) * mag * 3.5 if mag > 0.0005 else 0.0
        trauma = max(0.0, trauma - 0.06)

        # ── 그리기 ──
        bob = math.sin(tk * 0.9) * 0.04 if walking else 0.0
        eye = pos + np.array([0, 1.62 + bob, 0])
        cy, cp = yaw + yoff, pitch + poff
        b = G.basis(cy, cp)
        s = 3.0 + tk / 20.0
        d_rays, col, depth, _ = G.render_world(world, eye, cy, cp, s)
        small = np.clip(col, 0, 1)
        # NPC (서 있음 → 쓰러짐)
        if npc["down"] is None:
            boxes = turn(DP.npc_boxes(npc["feet"], 1, npc["kind"]), npc["feet"], 1)       # 문 쪽(+z)을 보고 서 있음
        else:
            boxes = turn(G.lying_boxes(npc["feet"], 1, npc["kind"]), npc["feet"], -1)     # 뒤(-z)로 넘어짐
        nt, ncol = DP.trace_boxes(eye, d_rays, boxes)
        front = nt < depth
        small[front] = ncol[front] * 0.95
        img = Image.fromarray((small.reshape(GP.H, GP.W, 3) * 255).astype(np.uint8)).resize((OW, OH), Image.BILINEAR).convert("RGBA")
        dep = np.minimum(depth, np.where(front, nt, 1e9)).reshape(GP.H, GP.W)

        def depth_fn(x, y):
            xi = int(min(GP.W - 1, max(0, x * GP.W / OW)))
            yi = int(min(GP.H - 1, max(0, y * GP.H / OH)))
            return float(dep[yi, xi])

        if npc["down"] is not None:
            G.draw_decal(img, depth_fn, npc["feet"] + np.array([0.0, 0.0, -0.9]), np.array([0, 1.0, 0]), 0.35, (110, 6, 12, 255), eye, b, 21)
        for d in doors:
            draw_door(img, depth_fn, d, eye, b)
        # 1인칭 맨주먹 (발차기는 다리가 보이지 않음)
        layer = G.fp_layer(G.frame_for(fist_frames, 0.0))
        img.alpha_composite(layer, (0, int(bob * 120)))
        hud.draw(img, "맨주먹", None, 3, 4200)
        dd = ImageDraw.Draw(img)
        label = "Space 발차기!" if T_KICK <= tk < T_KICK + 14 else ("문을 밀고 지나감" if T_WALK <= tk < 34 else "")
        if label:
            dd.text((OW // 2 - 40, OH // 2 + 30), label, font=ImageFont.truetype(G.FONT_KR, 16), fill=(255, 225, 77, 230))
        dd.text((8, OH - 18), "시뮬레이션 (게임 캡처 아님)", font=ImageFont.truetype(G.FONT_KR, 13), fill=(255, 255, 255, 140))
        frames.append(img.convert("RGB"))
        print(f"\r{tk + 1}/{TOTAL} 문A {door_a.angle:5.1f}° 문B {door_b.angle:5.1f}° 속도 {door_b.vel:5.1f} NPC {'쓰러짐' if npc['down'] is not None else '서 있음'}", end="", flush=True)
    print()
    pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    path = os.path.join(OUT, "door.gif")
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=50, loop=0, optimize=True)
    for i, k in enumerate((20, 50, 60)):
        frames[k].save(os.path.join(OUT, f"still_{i + 1}.png"))
    print(path, os.path.getsize(path) // 1024, "KB", len(frames), "장")


if __name__ == "__main__":
    main()
