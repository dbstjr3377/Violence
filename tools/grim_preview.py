#!/usr/bin/env python3
"""
벅샷 룰렛 느낌 쉐이더 미리보기 (게임 캡처가 아닌 시뮬레이션).
 - 맵: build-out/maps/<맵>.txt (MapRenderTest 가 만든 실제 생성 결과), 복셀 광선 추적 1인칭 시점
 - 밝기: 마인크래프트처럼 블록 빛(전구 15)과 하늘 빛을 한 칸에 1씩 줄이며 퍼뜨리고, 밤(18000) 라이트맵 근사
 - 쉐이더: tools/shaders/include/violence_grim.glsl 의 grim_grade 를 numpy 로 옮김
결과: docs/images/grim/<맵>_<n>.png (왼쪽 바닐라 / 오른쪽 쉐이더)
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_maps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")
OUT = os.path.join(ROOT, "docs", "images", "grim")
W, H = 800, 450
FOV = 70.0

AIR, SOLID, BARS, LAMP = 0, 1, 2, 3
EMIT = {"lantern": 15, "froglight": 15, "sea_lantern": 15, "glowstone": 15, "shroomlight": 15}
PASS = ("pane", "fence", "carpet", "potted", "trapdoor")

# ── violence_grim.glsl 상수 ──
GRIM_SHADOW = np.array([0.10, 0.15, 0.13])
GRIM_LAMP = np.array([1.20, 0.98, 0.66])
GRIM_AMBIENT = np.array([0.36, 0.46, 0.42])
GRIM_DIM = np.array([0.82, 1.00, 0.90])
GRIM_FOG = np.array([0.07, 0.10, 0.09])
LEVELS = 30.0
BAYER = np.array([0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5], dtype=float)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ghash(px, py):
    return np.modf(np.sin(px * 12.9898 + py * 78.233) * 43758.5453)[0] % 1.0


def grim_grade(lit, albedo, block, dist, fx, fy, s):
    """grim_grade 와 같은 계산. fx, fy: 화면 픽셀 좌표 (OpenGL 처럼 아래에서 위)"""
    flick = 1.0 - 0.25 * float(ghash(math.floor(s * 15.0), 3.7) >= 0.965)
    lamp = (block ** 3.0 * 2.0 * flick)[:, None]
    pool = smoothstep(0.55, 0.95, block)[:, None]
    c = albedo * (GRIM_AMBIENT * (1.0 - 0.35 * pool) + GRIM_LAMP * lamp)
    c = np.maximum(c, lit * GRIM_DIM * 0.55)
    lum = (c @ np.array([0.299, 0.587, 0.114]))[:, None]
    c = lum + (c - lum) * (0.62 + 0.25 * pool)
    c = c + GRIM_SHADOW * 0.08 * (1.0 - pool)
    c = np.clip(c, 0, 1)
    c = c + (c * c * (3 - 2 * c) - c) * 0.35
    c = c + (GRIM_FOG - c) * (smoothstep(14.0, 56.0, dist) * 0.42)[:, None]
    u = fx / W - 0.5
    v = fy / H - 0.5
    vig = 0.74 + 0.26 * smoothstep(0.75, 0.30, np.sqrt((u * 1.15) ** 2 + v ** 2))
    c = c * vig[:, None]
    c = c + ((ghash(fx + math.floor(s * 24.0) * 17.0, fy + 3.0) - 0.5) * 0.045)[:, None]
    b = (BAYER[(np.floor(fx) % 4).astype(int) + (np.floor(fy) % 4).astype(int) * 4] + 0.5) / 16.0
    return np.floor(np.clip(c, 0, 1) * LEVELS + b[:, None]) / LEVELS


def lightmap(block, sky):
    """lightmap.fsh 근사 (밤 18000, 밝기 옵션 기본값)"""
    def bright(l):
        return l / (4.0 - 3.0 * l)
    bb = bright(block)[:, None]
    sb = bright(sky)[:, None]
    par = ((2 * block - 1) ** 2)[:, None]
    tint = np.array([1.0, 0.86, 0.66])
    col = np.array([0.03, 0.03, 0.05]) + np.array([0.55, 0.6, 0.9]) * sb * 0.22 + (tint + (1 - tint) * 0.9 * par) * bb
    col = np.clip(col, 0, 1)
    mx = np.maximum(col.max(axis=1, keepdims=True), 1e-4)
    ng = col * ((1 - (1 - mx) ** 4) / mx)
    return col + (ng - col) * 0.5


def block_color(name):
    """미리보기 색 (render_maps 의 키워드 순서 때문에 석재 벽돌이 붉게 나오는 것 보정)"""
    for key, rgb in (("stone_brick", (118, 118, 122)), ("mud_brick", (137, 104, 79)), ("smooth_stone", (160, 160, 160)),
                     ("polished_andesite", (132, 134, 133)), ("iron_block", (200, 200, 205)), ("white_wool", (225, 225, 225))):
        if key in name:
            return rgb
    return render_maps.color(name)


class World:
    def __init__(self, bounds, grid):
        self.min = np.array(bounds[:3]) - 1
        size = np.array(bounds[3:]) - self.min + 2
        self.kind = np.zeros(size, dtype=np.int8)
        self.col = np.zeros(tuple(size) + (3,), dtype=np.float32)
        self.lamps = []
        emit = np.zeros(size, dtype=np.int16)
        for (x, y, z), name in grid.items():
            i = (x - self.min[0], y - self.min[1], z - self.min[2])
            e = next((v for k, v in EMIT.items() if k in name), 0)
            if name == "lantern" or name.startswith("lantern"):
                self.kind[i] = LAMP
                self.lamps.append(np.array([x, y, z], dtype=float))
                emit[i] = 15
                continue
            if "iron_bars" in name:
                self.kind[i] = BARS
                self.col[i] = (0.33, 0.34, 0.37)
                continue
            if any(p in name for p in PASS):
                continue
            c = block_color(name)
            if c is None:
                continue
            self.kind[i] = SOLID
            self.col[i] = np.array(c) / 255.0
            emit[i] = e
        opaque = self.kind == SOLID
        # 하늘 빛: 위가 뚫린 칸은 15
        sky = np.zeros(size, dtype=np.int16)
        blocked = np.zeros(size[[0, 2]], dtype=bool)
        for y in range(size[1] - 1, -1, -1):
            blocked |= opaque[:, y, :]
            sky[:, y, :] = np.where(blocked, 0, 15)
        self.sky = self.spread(sky, opaque)
        self.block = self.spread(emit, opaque)

    @staticmethod
    def spread(lv, opaque):
        lv = lv.copy()
        for _ in range(15):
            nb = np.zeros_like(lv)
            for ax in range(3):
                for sh in (1, -1):
                    r = np.roll(lv, sh, axis=ax)
                    sl = [slice(None)] * 3
                    sl[ax] = 0 if sh == 1 else -1
                    r[tuple(sl)] = 0
                    nb = np.maximum(nb, r)
            lv = np.where(opaque, lv, np.maximum(lv, nb - 1))
        return lv

    def trace(self, o, d, tmax=80.0):
        n = d.shape[0]
        o = np.broadcast_to(o, d.shape).astype(np.float64)
        cell = np.floor(o).astype(np.int64)
        step = np.where(d > 0, 1, -1)
        with np.errstate(divide="ignore"):
            inv = np.where(np.abs(d) > 1e-12, 1.0 / d, 1e12)
        tm = (cell + (step > 0) - o) * inv
        td = np.abs(inv)
        t = np.zeros(n)
        axis = np.zeros(n, dtype=np.int64)
        hit = np.zeros(n, dtype=bool)
        active = np.ones(n, dtype=bool)
        hcell = np.zeros((n, 3), dtype=np.int64)
        prev = cell.copy()
        rows = np.arange(n)
        for _ in range(500):
            idx = rows[active]
            if idx.size == 0:
                break
            prev[idx] = cell[idx]
            ax = np.argmin(tm[idx], axis=1)
            t[idx] = tm[idx, ax]
            cell[idx, ax] += step[idx, ax]
            tm[idx, ax] += td[idx, ax]
            axis[idx] = ax
            loc = cell[idx] - self.min
            inside = np.all((loc >= 0) & (loc < self.kind.shape), axis=1)
            k = np.zeros(idx.size, dtype=np.int8)
            li = loc[inside]
            k[inside] = self.kind[li[:, 0], li[:, 1], li[:, 2]]
            solid = k == SOLID
            bars = k == BARS
            if bars.any():
                bi = idx[bars]
                p = o[bi] + d[bi] * t[bi][:, None]
                a = axis[bi]
                along = np.where(a == 2, p[:, 0], p[:, 2])
                f = np.modf(along)[0] % 1.0
                rod = np.abs(((f * 4) % 1.0) - 0.5) < 0.2
                solid[bars] = rod & (a != 1)
            done = solid | (t[idx] > tmax) | ~inside
            hit[idx[solid]] = True
            hcell[idx[solid]] = cell[idx[solid]]
            active[idx[done]] = False
        return t, hcell, prev, axis, hit, step


def camera(yaw, pitch):
    yr, pr = math.radians(yaw), math.radians(pitch)
    f = np.array([-math.sin(yr) * math.cos(pr), -math.sin(pr), math.cos(yr) * math.cos(pr)])
    r = np.cross(f, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    th = math.tan(math.radians(FOV / 2))
    ys, xs = np.mgrid[0:H, 0:W]
    px = ((xs + 0.5) / W * 2 - 1) * th * W / H
    py = (1 - (ys + 0.5) / H * 2) * th
    d = f[None, None] + px[..., None] * r + py[..., None] * u
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return d.reshape(-1, 3), xs.reshape(-1) + 0.5, (H - ys.reshape(-1)) - 0.5


def render(world, eye, yaw, pitch, s=3.0):
    eye = np.array(eye, dtype=float)
    d, fx, fy = camera(yaw, pitch)
    t, cell, prev, axis, hit, step = world.trace(eye, d)
    loc = np.clip(cell - world.min, 0, np.array(world.kind.shape) - 1)
    base = world.col[loc[:, 0], loc[:, 1], loc[:, 2]]
    # 빛은 맞은 면 바로 앞(공기) 칸의 값
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
    lit = albedo * lightmap(block, sky)
    # 매단 전구 (작은 발광 상자 + 줄)
    lampcol = np.zeros_like(lit)
    lamphit = np.zeros(len(t), dtype=bool)
    lt = np.where(hit, t, 1e9)
    for lp in world.lamps:
        for lo, hi, col in ((lp + [0.31, 0.0, 0.31], lp + [0.69, 0.5, 0.69], (1.0, 0.86, 0.5)),
                            (lp + [0.47, 0.5, 0.47], lp + [0.53, 1.0, 0.53], (0.12, 0.12, 0.12))):
            with np.errstate(divide="ignore", invalid="ignore"):
                t0 = (lo - eye) / d
                t1 = (hi - eye) / d
            tn = np.nanmax(np.minimum(t0, t1), axis=1)
            tf = np.nanmin(np.maximum(t0, t1), axis=1)
            h = (tn <= tf) & (tn > 0) & (tn < lt)
            lt = np.where(h, tn, lt)
            lampcol[h] = col
            lamphit |= h
    van = np.where(hit[:, None], lit, 0.01)
    van = np.where(lamphit[:, None], lampcol, van)
    shd = grim_grade(lit, albedo, block, t, fx, fy, s)
    shd = np.where(hit[:, None], shd, GRIM_FOG * 0.6)
    shd = np.where(lamphit[:, None], lampcol, shd)

    def img(a):
        return Image.fromarray((np.clip(a, 0, 1).reshape(H, W, 3) * 255).astype(np.uint8))
    return img(van), img(shd)


def openness(world, eye):
    best = None
    for yaw in range(0, 360, 30):
        yr = math.radians(yaw)
        ds = []
        for off in (-20, 0, 20):
            a = math.radians(yaw + off)
            dv = np.array([[-math.sin(a), -0.05, math.cos(a)]])
            t, _cell, prev, _ax, hit, _ = world.trace(np.array(eye, dtype=float), dv, 40.0)
            pl = np.clip(prev[0] - world.min, 0, np.array(world.kind.shape) - 1)
            outdoor = world.sky[pl[0], pl[1], pl[2]] > 3       # 창밖(하늘 빛이 드는 곳)을 보는 시점은 제외
            ds.append(0.0 if (outdoor or not hit[0]) else min(float(t[0]), 40.0))
        score = sorted(ds)[1]
        if best is None or score > best[0]:
            best = (score, yaw)
        _ = yr
    return best


def main():
    os.makedirs(OUT, exist_ok=True)
    font = ImageFont.truetype(FONT, 20)
    maps = [("apartment_a", "아파트 A동"), ("apartment_b", "아파트 B동"), ("prison", "교도소")]
    made = []
    for mid, title in maps:
        _, _, bounds, grid, _doors, _weapons, spawns = render_maps.load(os.path.join(ROOT, "build-out", "maps", mid + ".txt"))
        world = World(bounds, grid)
        # 탁 트인 쪽을 보는 스폰 두 곳 (서로 떨어진 곳)
        cands = []
        for sp in spawns[::max(1, len(spawns) // 40)]:
            eye = (sp[0], sp[1] + 1.62, sp[2])
            sc, yaw = openness(world, eye)
            cands.append((sc, eye, yaw))
        cands.sort(key=lambda c: -c[0])
        views = []
        for c in cands:
            if all(math.dist(c[1], v[1]) > 14 for v in views):
                views.append(c)
            if len(views) == 2:
                break
        for n, (_, eye, yaw) in enumerate(views):
            van, shd = render(world, eye, yaw, 6.0)
            sheet = Image.new("RGB", (W * 2 + 8, H + 34), (0, 0, 0))
            sheet.paste(van, (0, 34))
            sheet.paste(shd, (W + 8, 34))
            d = ImageDraw.Draw(sheet)
            d.text((10, 6), f"{title} · 바닐라 (밤)", font=font, fill=(200, 200, 200))
            d.text((W + 18, 6), f"{title} · 벅샷 룰렛 쉐이더 — 시뮬레이션 (게임 캡처 아님)", font=font, fill=(255, 220, 90))
            path = os.path.join(OUT, f"{mid}_{n + 1}.png")
            sheet.save(path)
            made.append(path)
            print(path, "눈", tuple(round(v, 1) for v in eye), "yaw", yaw)
    return made


if __name__ == "__main__":
    main()
