#!/usr/bin/env python3
"""
연사(왼클릭 유지) 1인칭 시뮬레이션 GIF.
서버 로직(연사 누적기, 발사마다 거는 쿨다운, 잔떨림)과 클라이언트 프레임 선택(range_dispatch cooldown)을
틱 단위로 그대로 따라 하고, 탄환 궤적은 Fx.tracer 와 같은 시간표로 그린다.
결과: build-out/autofire/<총>.gif (실제 속도), <총>_slow_x4.gif
게임 캡처가 아니라 시뮬레이션이다.
"""
import math
import os
import random
import re
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_animations as EA  # noqa: E402
import fp_gallery as G  # noqa: E402
import fp_sim  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build-out", "autofire")
FPS_MS = 20                 # GIF 한 장 = 20ms (틱당 2.5장)
HOLD_TICKS = 30             # 1.5초 동안 누르고
REST_TICKS = 14             # 0.7초 쉼
WALL = 14.0                 # 벽까지 거리 (블록)
OUT_SIZE = (960, 540)
PX_PER_RAD = (fp_sim.H / 2) / math.tan(math.radians(fp_sim.FOV / 2))


def weapon_stats(gid):
    yml = open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "weapons.yml"), encoding="utf-8").read()
    block = re.search(r"^  " + gid + r":\s*\n((?:    .*\n)+)", yml, re.M).group(1)
    rpm = float(re.search(r"rpm:\s*([\d.]+)", block).group(1))
    spread = float(re.search(r"spread:\s*([\d.]+)", block).group(1))
    return rpm, spread


def fire_anim_ticks(rpm):
    # WeaponType.fireAnimTicks() 와 같은 계산
    return int(max(2, min(6, round(1200.0 / rpm * 2))))


def gun_layer(name, cache={}):
    if name not in cache:
        m = G.load_model(name)
        tex_ref = m["textures"]["t"].split(":")[1]
        tex = Image.open(os.path.join(G.NS, "textures", tex_ref + ".png")).convert("RGBA")
        layer = Image.new("RGBA", (fp_sim.W, fp_sim.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        items = []
        fp_sim.render_items(items, m, tex, m["display"]["firstperson_righthand"])
        items.sort(key=lambda t: t[0])
        for _, vq, col in items:
            d.polygon([fp_sim.project(v) for v in vq], fill=col + (255,))
        cache[name] = layer
    return cache[name]


def view_dir(yaw, pitch):
    """시점 기준 방향 (x 오른쪽, y 위, -z 앞). yaw + 오른쪽, pitch + 아래 (마인크래프트와 같음)"""
    return [math.sin(yaw) * math.cos(pitch), -math.sin(pitch), -math.cos(yaw) * math.cos(pitch)]


def simulate(gid):
    rpm, spread = weapon_stats(gid)
    per_tick = rpm / 1200.0
    dur = fire_anim_ticks(rpm)
    frames = EA.anim_of(gid)               # [(모델, 상한, 하한)] 쿨다운 1 → 0
    rnd = random.Random(7)
    budget, last_shot = 0.0, -100
    cd_start = None
    trauma, last_yaw, last_pitch = 0.0, 0.0, 0.0
    cam = [0.0, 0.0]                        # 흔들림으로 돌아간 시야 (rad)
    tracers = []                            # (발사 틱, 방향)
    ticks = []
    interval = 1.0 / per_tick
    for tick in range(HOLD_TICKS + REST_TICKS):
        # 서버: FireAccumulator.tickHeld
        if tick < HOLD_TICKS:
            if tick - last_shot > math.ceil(interval) + 1:
                budget = max(budget, 1.0)
            else:
                budget += per_tick
            shots = int(budget)
            if shots > 0:
                budget -= shots
                last_shot = tick
                cd_start = tick
                for _ in range(shots):
                    j = math.radians(spread) * 0.5
                    tracers.append((tick, cam[0] + rnd.gauss(0, j), cam[1] + rnd.gauss(0, j)))
                trauma = max(trauma, 0.3)  # Shake.atLeast
        # 서버: Shake.tick
        mag = trauma * trauma
        yaw = pitch = 0.0
        if mag > 0.0005:
            yaw = (rnd.random() * 2 - 1) * mag * 5.0
            pitch = (rnd.random() * 2 - 1) * mag * 3.5
        cam[0] += math.radians(yaw - last_yaw)
        cam[1] += math.radians(pitch - last_pitch)
        last_yaw, last_pitch = yaw, pitch
        trauma = max(0.0, trauma - 0.06)
        ticks.append((cd_start, tuple(cam), list(tracers)))
    return ticks, frames, dur


def frame_model(frames, progress):
    for name, hi, lo in frames:
        if progress >= lo and progress > 0:
            return name
    return frames[-1][0]


def draw_tracer(d, cam, tick_f, shot_tick, ty, tp):
    age = tick_f - shot_tick
    if age < 0 or age >= 3:
        return
    dirv = view_dir(ty - cam[0], tp - cam[1])
    # 시점 이동 반영: 발사 순간의 총구 위치 (오른쪽 0.15, 아래 0.13, 앞 0.6)
    start = [0.15, -0.13, -0.6]
    if age < 1:
        a, b, w = 0.0, 3.0, 0.035
    else:
        k = min(1.0, age - 1)
        a, b = (0.0 + (WALL - 1.2) * k), (3.0 + (WALL - 3.0) * k)
        w = 0.035 * (1 - 0.4 * k)
    p0 = [start[i] + dirv[i] * a for i in range(3)]
    p1 = [start[i] + dirv[i] * b for i in range(3)]
    s0, s1 = fp_sim.project(p0), fp_sim.project(p1)
    w0 = max(1, int(w * PX_PER_RAD / -p0[2]))
    d.line([s0, s1], fill=(255, 205, 40), width=w0)
    d.line([s0, s1], fill=(255, 250, 200), width=max(1, w0 // 3))


def render(gid):
    ticks, frames, dur = simulate(gid)
    bg = fp_sim.background()
    total = len(ticks)
    out = []
    t_ms = 0
    while t_ms < total * 50:
        tick_f = t_ms / 50.0
        ti = int(tick_f)
        cd_start, cam, tracers = ticks[ti]
        # 시야가 돌아간 만큼 배경을 밀어 흔들림 표현 (손과 총은 화면에 고정)
        dx = -cam[0] * PX_PER_RAD
        dy = -cam[1] * PX_PER_RAD
        img = bg.transform(bg.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR, fillcolor=(60, 58, 66))
        d = ImageDraw.Draw(img)
        for shot_tick, ty, tp in tracers:
            draw_tracer(d, cam, tick_f, shot_tick, ty, tp)
        progress = 0.0 if cd_start is None else max(0.0, (cd_start + dur - tick_f) / dur)
        img.paste(gun_layer(frame_model(frames, progress)), (0, 0), gun_layer(frame_model(frames, progress)))
        cx, cy = fp_sim.W / 2, fp_sim.H / 2
        d = ImageDraw.Draw(img)
        d.line([(cx - 9, cy), (cx + 9, cy)], fill=(255, 255, 255), width=2)
        d.line([(cx, cy - 9), (cx, cy + 9)], fill=(255, 255, 255), width=2)
        out.append(img.resize(OUT_SIZE, Image.LANCZOS))
        t_ms += FPS_MS
    os.makedirs(OUT, exist_ok=True)
    pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in out]
    for suffix, ms in (("", FPS_MS), ("_slow_x4", FPS_MS * 4)):
        path = os.path.join(OUT, f"{gid}_autofire{suffix}.gif")
        pal[0].save(path, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=True, disposal=1)
        print(path, f"{os.path.getsize(path) // 1024}KB", f"{len(pal)}장", f"애니메이션 {dur}틱")


if __name__ == "__main__":
    for g in sys.argv[1:] or ["uzi", "m16"]:
        render(g)
