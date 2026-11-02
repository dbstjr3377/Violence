#!/usr/bin/env python3
"""
클럽 조명 미리보기 (게임 캡처가 아닌 시뮬레이션).
 - 맵: build-out/maps/club.txt (MapRenderTest 가 만든 실제 생성 결과)를 복셀 광선 추적으로 1인칭 시점 렌더
 - 표면 조명: tools/shaders/include/violence_club.glsl 의 club_light 를 numpy 로 그대로 옮김
 - 공중 빛줄기: 플러그인 ClubBeams 와 같은 공식 (무빙 라이트 원뿔, 레이저 부채꼴, 미러볼)
결과: docs/images/club_lights.png (장면 4컷), build-out/club/club_lights.gif
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
W, H = 640, 360
FOV = 70.0

# ── violence_club.glsl 과 같은 상수 ──
Y0 = 192.0
BPM = 128.0
TAU = math.tau
CLUB_MIN = np.array([-37.0, 190.0, -31.0])
CLUB_MAX = np.array([38.0, 215.0, 32.0])
HALL_MIN = np.array([-21.0, 192.0, -15.0])
HALL_MAX = np.array([22.0, 203.0, 16.0])
BALL = np.array([0.5, 200.5, 0.5])
LASER = np.array([0.5, 196.0, -12.5])
SPOT_Y = 201.6
COLORS = np.array([[1.0, 0.10, 0.70], [0.10, 0.80, 1.00], [0.55, 0.20, 1.00], [1.00, 0.45, 0.10], [0.20, 1.00, 0.40]])
EMISSIVE = ("froglight", "sea_lantern", "glowstone", "lantern", "shroomlight", "redstone_lamp", "crying_obsidian")


def beat_of(s):
    return s * BPM / 60.0


def spot_pos(i):
    return np.array([-14.5 + 6.0 * i, SPOT_Y, -5.5 if i % 2 == 0 else 6.5])


def spot_dir(i, s):
    pan = i * 1.7 + 1.1 * math.sin(TAU * 48.0 / 1200.0 * s + i * 1.3)
    tilt = 0.55 + 0.35 * math.sin(TAU * 70.0 / 1200.0 * s + i * 2.1)
    return np.array([math.sin(tilt) * math.cos(pan), -math.cos(tilt), math.sin(tilt) * math.sin(pan)])


def spot_color(i, s):
    return (i + int(math.floor(beat_of(s) / 8.0))) % 5


def lasers_on(s):
    return int(math.floor(beat_of(s) / 16.0)) % 2 == 1


def laser_normal(j, s):
    tilt = -0.18 + 0.16 * math.sin(TAU * 90.0 / 1200.0 * s + j * 2.0) + 0.12 * (j - 1.0)
    yaw = 0.45 * math.sin(TAU * 40.0 / 1200.0 * s + j * 1.7)
    nx, ny, nz = 0.0, math.cos(tilt), -math.sin(tilt)
    return np.array([nx * math.cos(yaw) + nz * math.sin(yaw), ny, -nx * math.sin(yaw) + nz * math.cos(yaw)])


def laser_beam(j, k, s):
    n = laser_normal(j, s)
    fwd = np.array([0.0, 0.0, 1.0])
    f = fwd - n * fwd.dot(n)
    f /= np.linalg.norm(f)
    side = np.cross(n, f)
    side /= np.linalg.norm(side)
    a = -0.6 + 1.2 * k / 4
    return f * math.cos(a) + side * math.sin(a)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hash2(p):
    return np.modf(np.sin(p[..., 0] * 12.9898 + p[..., 1] * 78.233) * 43758.5453)[0] % 1.0


def club_light(lit, albedo, p, s):
    """violence_club.glsl club_light 와 같은 계산 (배열 버전)"""
    out = lit.copy()
    inclub = np.all((p >= CLUB_MIN) & (p <= CLUB_MAX), axis=-1)
    beat = beat_of(s)
    kick = math.exp(-(beat % 1.0) * 5.0)
    hall = np.all((p >= HALL_MIN) & (p <= HALL_MAX), axis=-1)
    dark = lit * 0.42
    add = np.zeros_like(lit)
    add[~hall] += np.array([0.45, 0.12, 0.75]) * (0.10 + 0.05 * kick)
    for i in range(6):
        to = p - spot_pos(i)
        d = np.linalg.norm(to, axis=-1)
        c = (to / np.maximum(d, 1e-3)[..., None]) @ spot_dir(i, s)
        cone = smoothstep(0.975, 0.992, c)
        add += (COLORS[spot_color(i, s)] * (cone * (2.4 / (1.0 + d * d / 160.0)))[..., None]) * hall[..., None]
    v = p - BALL
    vl = np.linalg.norm(v, axis=-1)
    vn = v / np.maximum(vl, 1e-3)[..., None]
    az = np.arctan2(vn[..., 2], vn[..., 0]) + TAU * 30.0 / 1200.0 * s
    el = np.arcsin(np.clip(vn[..., 1], -1, 1))
    g = np.stack([az / TAU * 72.0, el / math.pi * 36.0], axis=-1)
    cell = np.floor(g)
    tw = hash2(cell)
    fr = g - cell - 0.5
    dotv = smoothstep(0.24, 0.10, np.linalg.norm(fr, axis=-1)) * (tw >= 0.35) * (vl > 1.0)
    add += (np.array([0.85, 0.9, 1.0]) * (dotv * (0.55 + 0.45 * tw))[..., None]) * hall[..., None]
    add += (COLORS[int(math.floor(beat / 16.0)) % 5] * 0.12 * (0.5 + kick)) * hall[..., None]
    if beat % 32.0 >= 30.0:
        add += math.exp(-(beat % 1.0) * 14.0) * 0.55 * hall[..., None]
    res = dark + albedo * add
    # LED 댄스 플로어
    fl = hall & (np.abs(p[..., 1] - (Y0 + 1.0)) < 0.02) & (p[..., 0] >= -16) & (p[..., 0] <= 17) & (p[..., 2] >= -10) & (p[..., 2] <= 11)
    if fl.any():
        tile = np.floor(p[..., [0, 2]] / 2.0)
        h = hash2(tile + math.floor(beat / 2.0) * 0.25)
        on = (h >= 0.3).astype(float)
        idx = (np.floor(h * 5.0).astype(int) + int(math.floor(beat / 4.0))) % 5
        tc = COLORS[idx]
        f = np.abs(np.modf(p[..., [0, 2]] / 2.0)[0] % 1.0 - 0.5)
        edge = smoothstep(0.5, 0.44, np.max(f, axis=-1))
        flc = res * 0.35 + tc * (on * edge * (0.35 + 0.75 * kick))[..., None]
        res = np.where(fl[..., None], flc, res)
    if lasers_on(s):
        front = hall & (p[..., 2] > LASER[2] + 0.5)
        for j in range(3):
            dd = np.abs((p - LASER) @ laser_normal(j, s))
            line = smoothstep(0.07, 0.0, dd) * front
            lc = np.array([1.0, 0.15, 0.2]) if j == 1 else np.array([0.25, 1.0, 0.3])
            res += lc * (line * 1.2)[..., None]
    return np.where(inclub[..., None], res, out)


# ───────────────────────── 복셀 광선 추적 ─────────────────────────

class Voxels:
    def __init__(self, bounds, grid):
        self.min = np.array(bounds[:3])
        size = np.array(bounds[3:]) - self.min + 1
        self.occ = np.zeros(size, dtype=bool)
        self.col = np.zeros(tuple(size) + (3,), dtype=np.float32)
        self.emit = np.zeros(size, dtype=bool)
        for (x, y, z), name in grid.items():
            c = render_maps.color(name)
            if c is None or "pane" in name or "fence" in name or "carpet" in name:
                continue
            i = (x - self.min[0], y - self.min[1], z - self.min[2])
            self.occ[i] = True
            self.col[i] = np.array(c) / 255.0
            self.emit[i] = any(k in name for k in EMISSIVE)

    def trace(self, o, d, tmax=80.0):
        """반환: 거리, 맞은 블록 인덱스, 면 축(0/1/2), 맞음 여부"""
        n = d.shape[0]
        o = np.broadcast_to(o, d.shape).astype(np.float64)
        cell = np.floor(o).astype(np.int64)
        step = np.where(d > 0, 1, -1)
        with np.errstate(divide="ignore"):
            inv = np.where(np.abs(d) > 1e-12, 1.0 / d, 1e12)
        tmax_v = (cell + (step > 0) - o) * inv
        tdel = np.abs(inv)
        t = np.zeros(n)
        axis = np.zeros(n, dtype=np.int64)
        hit = np.zeros(n, dtype=bool)
        active = np.ones(n, dtype=bool)
        hcell = np.zeros((n, 3), dtype=np.int64)
        rows = np.arange(n)
        for _ in range(400):
            idx = rows[active]
            if idx.size == 0:
                break
            ax = np.argmin(tmax_v[idx], axis=1)
            t[idx] = tmax_v[idx, ax]
            cell[idx, ax] += step[idx, ax]
            tmax_v[idx, ax] += tdel[idx, ax]
            axis[idx] = ax
            loc = cell[idx] - self.min
            inside = np.all((loc >= 0) & (loc < self.occ.shape), axis=1)
            solid = np.zeros(idx.size, dtype=bool)
            li = loc[inside]
            solid[inside] = self.occ[li[:, 0], li[:, 1], li[:, 2]]
            done = solid | (t[idx] > tmax)
            hit[idx[solid]] = True
            hcell[idx[solid]] = cell[idx[solid]]
            active[idx[done]] = False
        return t, hcell, axis, hit, step


def camera_rays(eye, yaw, pitch):
    """마인크래프트 방향: yaw 0 = 남(+z), 90 = 서(-x); pitch + = 아래"""
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
    return d.reshape(-1, 3)


class Scene:
    def __init__(self, vox, eye, yaw, pitch):
        self.vox, self.eye = vox, np.array(eye, dtype=float)
        self.d = camera_rays(self.eye, yaw, pitch)
        t, cell, axis, hit, step = vox.trace(self.eye, self.d)
        self.t, self.hit = t, hit
        self.p = self.eye + self.d * t[:, None]
        loc = cell - vox.min
        loc = np.clip(loc, 0, np.array(vox.occ.shape) - 1)
        base = vox.col[loc[:, 0], loc[:, 1], loc[:, 2]]
        emit = vox.emit[loc[:, 0], loc[:, 1], loc[:, 2]]
        # 바닐라처럼 면마다 밝기 (위 1.0, 아래 0.5, 동서 0.6, 남북 0.8)
        face_up = (axis == 1) & (step[np.arange(len(step)), 1] < 0)
        face_dn = (axis == 1) & ~face_up
        shade = np.where(axis == 0, 0.6, np.where(axis == 2, 0.8, np.where(face_up, 1.0, 0.5)))
        # 블록 무늬 (텍스처 대신 위치 노이즈)
        q = np.floor(self.p * 4 + self.d * 1e-3)
        noise = 0.88 + 0.24 * (np.modf(np.sin(q @ np.array([12.99, 78.23, 37.71])) * 43758.5)[0] % 1.0)
        self.albedo = base * (shade * noise)[:, None]
        light = np.where(emit, 1.0, 0.82)
        self.lit = self.albedo * light[:, None]
        self.albedo = np.where(hit[:, None], self.albedo, 0)
        self.lit = np.where(hit[:, None], self.lit, 0)
        # 표면에서 살짝 띄운 좌표 (면 위 판정용): 정확히 면 위에 있도록 반올림
        on_face = self.p.copy()
        rows = np.arange(len(axis))
        on_face[rows, axis] = np.round(on_face[rows, axis])
        self.p = np.where(hit[:, None], on_face, self.p)
        _ = face_dn
        # 공중 빛줄기 샘플 지점
        self.samples = np.linspace(0.04, 1.0, 40)

    def laser_len(self, j, k, s):
        dv = laser_beam(j, k, s)[None]
        t, _, _, hit, _ = self.vox.trace(LASER, dv, 40.0)
        return float(t[0]) if hit[0] else 40.0

    def spot_len(self, i, s):
        dv = spot_dir(i, s)[None]
        t, _, _, hit, _ = self.vox.trace(spot_pos(i), dv, 26.0)
        return float(t[0]) if hit[0] else 26.0

    def frame(self, s):
        col = club_light(self.lit, self.albedo, self.p, s)
        col = np.where(self.hit[:, None], col, 0.02)
        tmax = np.where(self.hit, self.t, 40.0)
        # 무빙 라이트 원뿔 (ClubBeams: 광원에서 멀수록 넓고 옅음)
        glow = np.zeros_like(col)
        for i in range(6):
            sp, sd, L = spot_pos(i), spot_dir(i, s), self.spot_len(i, s)
            acc = np.zeros(len(tmax))
            for f in self.samples:
                q = self.eye + self.d * (tmax * f)[:, None]
                to = q - sp
                along = to @ sd
                radial = np.linalg.norm(to - along[:, None] * sd, axis=-1)
                v = np.clip(along / L, 0, 1)
                width = (0.10 + 0.90 * v) * L * math.tan(math.acos(0.975))
                k = radial / np.maximum(width, 1e-3)
                a = 0.45 * (1 - 0.7 * v) * np.clip(1 - k, 0, 1) ** 0.8 * (along > 0) * (along < L)
                acc += a * (tmax * (self.samples[1] - self.samples[0])) * 0.9
            glow += COLORS[spot_color(i, s)] * np.clip(acc, 0, 1.2)[:, None] * 0.55
        col = col + glow
        # 레이저 빛줄기 (광선과 선분 사이 거리)
        if lasers_on(s):
            for j in range(3):
                lc = np.array([1.0, 0.25, 0.3]) if j == 1 else np.array([0.35, 1.0, 0.4])
                for k in range(5):
                    bd = laser_beam(j, k, s)
                    L = self.laser_len(j, k, s)
                    w0 = self.eye - LASER
                    b = self.d @ bd
                    dd = self.d @ w0
                    e = w0 @ bd
                    den = np.maximum(1 - b * b, 1e-6)
                    tc = (b * e - dd) / den
                    sc = np.clip((e - b * dd) / den, 0, L)
                    tc = np.clip(tc, 0, tmax)
                    gap = np.linalg.norm(self.eye + self.d * tc[:, None] - (LASER + bd * sc[:, None]), axis=-1)
                    px = np.maximum(tc, 0.5) * (2 * math.tan(math.radians(FOV / 2)) / H)
                    width = np.maximum(0.025, px * 0.8)
                    col += lc * (np.exp(-(gap / width) ** 2) * 0.9)[:, None]
        # 미러볼 (구)
        oc = self.eye - BALL
        b = self.d @ oc
        c = oc @ oc - 0.3 ** 2
        disc = b * b - c
        hitb = (disc > 0) & (-b - np.sqrt(np.maximum(disc, 0)) < tmax)
        sparkle = 0.55 + 0.45 * (np.modf(np.sin(np.arange(len(b)) * 0.37 + s * 9) * 999)[0] % 1.0 > 0.8)
        col = np.where(hitb[:, None], np.array([0.75, 0.78, 0.85]) * sparkle[:, None], col)
        img = np.clip(col, 0, 1) ** (1 / 1.1)
        return Image.fromarray((img.reshape(H, W, 3) * 255).astype(np.uint8))


def main():
    path = os.path.join(ROOT, "build-out", "maps", "club.txt")
    if not os.path.isfile(path):
        raise SystemExit("build-out/maps/club.txt 가 없음: 먼저 플러그인 테스트(MapRenderTest)를 실행하세요")
    _, _, bounds, grid, *_ = render_maps.load(path)
    vox = Voxels(bounds, grid)
    floor_eye = Y0 + 1 + 1.62
    views = [("댄스홀에서 DJ 부스 쪽", (2.5, floor_eye, 13.5), 172.0, 2.0),
             ("2층 라운지에서 내려다봄", (12.5, Y0 + 5 + 1 + 1.62, 12.0), 150.0, 20.0)]
    font = ImageFont.truetype(FONT, 18)
    out_dir = os.path.join(ROOT, "build-out", "club")
    os.makedirs(out_dir, exist_ok=True)
    stills = []
    for vi, (label, eye, yaw, pitch) in enumerate(views):
        sc = Scene(vox, eye, yaw, pitch)
        frames = []
        # 레이저가 켜진 구간(16~32박)부터 4초, 실제 속도 12.5fps
        for n in range(60):
            s = 8.2 + n * 0.08
            im = sc.frame(s)
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, W, 26], fill=(0, 0, 0))
            d.text((10, 3), f"{label} · 시뮬레이션 (게임 캡처 아님)", font=font, fill=(255, 220, 90))
            frames.append(im)
            if n in (0, 22):
                stills.append(im)
        pal = [f.quantize(colors=192, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
        gif = os.path.join(out_dir, f"club_lights_{vi + 1}.gif")
        pal[0].save(gif, save_all=True, append_images=pal[1:], duration=80, loop=0, optimize=True)
        print(gif, os.path.getsize(gif) // 1024, "KB")
    sheet = Image.new("RGB", (W * 2, H * 2))
    for i, im in enumerate(stills[:4]):
        sheet.paste(im, ((i % 2) * W, (i // 2) * H))
    png = os.path.join(ROOT, "docs", "images", "club_lights.png")
    sheet.save(png)
    print(png)


if __name__ == "__main__":
    main()
