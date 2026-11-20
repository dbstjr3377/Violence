#!/usr/bin/env python3
"""근접무기 17종(소방도끼 포함) 루프 제작물 (블록벤치 MCP 로 생성). docs/TACZ_STYLE.md 2판 기준.
좌표는 기존 팩(tools/models_melee.py)과 같다: 손잡이가 아래(y 0~8), 날/머리가 +Y, 중심 x=8, z=8.
GRIP(쥐는 자리)과 날 방향을 그대로 지킨다.

사용: python3 tools/loop/melee/gen.py <무기> [렌더 폴더] [이름]
출력: tools/loop/melee/out/<무기>/<무기>.bbmodel (블록벤치 MCP) / .png / .json (MCP 내보내기)
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import bbkit  # noqa: E402
from bbkit import Builder, Xf, atlas, build_bbmodel, export_java, validate, render_views  # noqa: E402

PAL = {
    "wood":    (92, 58, 38),   "wood_l": (106, 70, 44), "wood_d": (70, 44, 28), "maple": (140, 110, 72), "wood_raw": (166, 136, 94),
    "rubber":  (30, 30, 32),   "rubber_t": (42, 42, 45), "tape": (40, 40, 44), "tape_d": (28, 28, 31),
    "steel":   (86, 90, 98),   "steel_d": (52, 54, 58),  "steel_l": (108, 112, 120), "steel_k": (44, 46, 50),
    "blade":   (78, 82, 90),   "blade_d": (62, 66, 74), "edge": (118, 122, 132),
    "black":   (40, 40, 43),   "black_t": (54, 54, 57),
    "chrome":  (96, 100, 108), "gold": (138, 108, 48), "gold_d": (104, 80, 36),
    "cloth":   (34, 34, 38),   "ito": (96, 30, 32),
    "foam":    (36, 36, 39),   "red": (84, 30, 28), "red_d": (72, 24, 22), "rust": (96, 56, 34),
    "leather": (80, 50, 32),   "leather_d": (60, 38, 24), "brass": (130, 104, 48),
    "ivory":   (176, 166, 146), "white": (186, 186, 182), "chalk": (60, 92, 150),
    "glass":   (46, 48, 52),   "ground": (104, 110, 120),
    "wood_g": (80, 50, 33), "wood_lg": (92, 60, 38), "maple_g": (122, 95, 62), "wood_dg": (58, 37, 24), "wood_rg": (146, 118, 80),
    "hone":    (150, 156, 166), "rust_s": (96, 56, 34),
    "anod":    (54, 54, 59),   "pan_in": (34, 34, 37), "pot": (70, 74, 80), "pipe_s": (52, 54, 58), "pipe_k": (44, 46, 50), "bore": (10, 10, 11),
}
# 윗모서리 밝은 줄: 금속 머리·칼등·가죽처럼 '위로 놓인 면'이 있는 재질만
TOPLINE = ("steel_d", "steel_k", "blade_d", "red", "red_d", "leather", "anod", "pot")


def rod(b, y0, y1, r, mat, x=8, z=8, name="rod"):
    b.oct("y", x, z, r, y0, y1, mat, name=name)


def taper(b, y0, y1, r0, r1, mat, name="taper", xf0=None):
    """반지름이 r0→r1 로 매끈하게 바뀌는 팔각 막대: 가는 쪽 팔각 심 + 기울어진 옆판 8장 (계단 턱 없음)"""
    rmin = min(r0, r1); rm = (r0 + r1) / 2; L = y1 - y0
    xf0 = xf0 or Xf()
    b.oct("y", 8, 8, rmin * 0.97, y0, y1, mat, xf0, name=name)
    phi = math.degrees(math.atan2(r1 - r0, L))
    w = rm * math.tan(math.radians(22.5)) * 1.06
    t = min(0.35, rm * 0.5)
    for k in range(8):
        xf = xf0 * Xf.rot("y", k * 45, (8, 0, 8)) * Xf.rot("x", phi, (8, (y0 + y1) / 2, 8 + rm))
        b.put([8 - w, y0, 8 + rm - t], [8 + w, y1, 8 + rm], mat, xf, name=name)


def _shift(dx, dy, dz):
    return Xf(None, (dx, dy, dz))


def rings(b, ys, r, mat, h=0.2, name="ring"):
    """감은 테이프·고무 마디: 위치(ys)를 직접 줘 간격이 조금씩 다르게"""
    for k, y in enumerate(ys):
        hh = h * (1.0 + 0.25 * ((k * 7) % 3 - 1))
        rod(b, y - hh / 2, y + hh / 2, r, mat, name=name)


def _ys(y0, y1, n):
    """y0~y1 에 n 개, 간격 ±15% 흔들림 (결정적)"""
    out = []
    for k in range(n):
        f = (k + 0.5) / n + (((k * 37) % 7) - 3) * 0.012
        out.append(y0 + (y1 - y0) * f)
    return out


# ───────── 칼 ─────────
def dagger(b):
    rod(b, 0.6, 6.8, 0.85, "rubber", name="handle")
    rings(b, _ys(1.2, 6.4, 5), 0.9, "rubber_t", name="grip_ring")
    b.chamfer_box([7.05, 0, 7.05], [8.95, 0.75, 8.95], 0.2, "steel_d", name="pommel")
    b.chamfer_box([5.9, 6.8, 7.35], [10.1, 7.55, 8.65], 0.2, "steel_d", name="guard")
    # 날: x 폭, z 두께. x+ 쪽 날(베벨+연마선), x- 쪽 등. 끝은 22.5° 사선 날이 등으로 모이는 클립 포인트
    b.put([7.25, 7.5, 7.72], [8.75, 13.0, 8.28], "blade", name="blade")
    b.put([8.4, 7.5, 7.78], [8.72, 13.0, 8.22], "ground", name="bevel")
    b.put([8.68, 7.5, 7.82], [8.8, 13.0, 8.18], "hone", name="hone")
    b.put([7.85, 8.2, 7.68], [8.15, 12.6, 8.32], "blade_d", name="fuller")
    b.put([7.2, 7.5, 7.75], [7.42, 16.4, 8.25], "blade_d", name="spine")
    T = math.tan(math.radians(22.5)); y = 12.95
    while y < 16.3:      # 사선 안쪽을 채우는 얇은 단 (모서리가 사선 판 안에 숨음)
        x1 = 8.75 - T * (y + 0.35 - 12.8) - 0.12
        if x1 <= 7.3:
            break
        b.put([7.25, y, 7.74], [x1, y + 0.4, 8.26], "blade", name="tip_fill")
        y += 0.35
    dx = Xf.rot("z", 22.5, (8.75, 12.8, 8))
    b.put([8.15, 12.8, 7.7], [8.75, 16.65, 8.3], "ground", dx, name="tip_slope")      # 채움 단보다 두꺼워 앞에 보임 → 사선이 곧게
    b.put([8.66, 12.8, 7.76], [8.8, 16.55, 8.24], "hone", dx, name="tip_hone")


def machete(b):
    b.chamfer_box([7.3, 0, 7.2], [8.7, 6.6, 8.8], 0.45, "black", name="handle")
    b.chamfer_box([7.3, 0.5, 6.95], [8.7, 1.4, 9.05], 0.25, "black_t", name="finger_rest")
    for y in (2.0, 4.4):
        b.oct("x", y, 8.0, 0.24, 7.25, 8.75, "brass", name="rivet")
    b.chamfer_box([7.15, 6.5, 6.85], [8.85, 7.25, 9.15], 0.2, "steel_d", name="bolster")
    # 날: 곧은 판 (z+ 날 / z- 등). 끝은 날 쪽 사선이 등으로 모임 — 사선 판은 채움보다 두꺼워 앞에 보이고, 회전은 한 번만
    b.put([7.8, 7.2, 6.6], [8.2, 21.6, 9.5], "blade", name="blade")
    b.put([7.78, 7.2, 9.1], [8.22, 21.6, 9.75], "ground", name="bevel")
    b.put([7.82, 7.2, 9.7], [8.18, 21.6, 9.9], "hone", name="hone")
    b.put([7.76, 7.2, 6.55], [8.24, 24.4, 6.95], "blade_d", name="spine")
    T = math.tan(math.radians(40)); y = 21.55
    while y < 24.4:
        z1 = 9.9 - T * (y + 0.3 - 21.6) - 0.12
        if z1 <= 7.0:
            break
        b.put([7.8, y, 6.6], [8.2, y + 0.35, z1], "blade", name="tip_fill")
        y += 0.3
    tx = Xf.rot("x", -40, (8, 21.6, 9.9))
    b.put([7.76, 21.6, 9.0], [8.24, 25.1, 9.9], "ground", tx, name="tip_slope")
    b.put([7.8, 21.6, 9.7], [8.2, 25.0, 9.92], "hone", tx, name="tip_hone")


def cleaver(b):
    rod(b, 0, 6.2, 0.75, "wood", name="handle")
    for y in (2.0, 4.4):
        b.oct("x", y, 8.0, 0.22, 7.2, 8.8, "brass", name="rivet")
    b.chamfer_box([7.4, 5.8, 7.3], [8.6, 7.0, 8.7], 0.15, "steel_l", name="bolster")
    # 날판 (얇게) + 둥근(팔각) 걸이 구멍: 판을 구멍 둘레로 나눠 만들고 구멍 테두리는 45° 판으로 깎음
    hz, hy, hr = 7.2, 14.6, 0.5   # 걸이 구멍은 등 쪽
    for frm, to in (([7.82, 6.6, 6.2], [8.18, 16.0, hz - hr]), ([7.82, 6.6, hz + hr], [8.18, 16.0, 11.0]),
                    ([7.82, 6.6, hz - hr], [8.18, hy - hr, hz + hr]), ([7.82, hy + hr, hz - hr], [8.18, 16.0, hz + hr])):
        b.put(frm, to, "blade_d", name="blade")
    w = hr * math.tan(math.radians(22.5))
    for (dy, dz) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):   # 구멍 네 모서리를 45° 판으로 막아 팔각 구멍
        b.put([7.82, hy + dy * hr - 0.18, hz + dz * hr - 0.18], [8.18, hy + dy * hr + 0.18, hz + dz * hr + 0.18], "blade_d",
              Xf.rot("x", 45, (8, hy + dy * hr, hz + dz * hr)), name="hole_corner")
    b.put([7.86, 6.6, 10.95], [8.14, 16.0, 11.45], "ground", name="bevel")
    b.put([7.9, 6.6, 11.4], [8.1, 16.0, 11.65], "hone", name="hone")
    b.chamfer_box([7.72, 6.6, 5.6], [8.28, 16.1, 6.25], 0.1, "steel_k", name="spine")


def katana(b):
    b.chamfer_box([7.25, 0.3, 7.25], [8.75, 7.0, 8.75], 0.3, "cloth", name="tsuka")
    for k in range(6):   # 손잡이 끈 마름모 (교차 띠)
        y = 0.9 + k * 1.0
        for a in (35, -35):
            b.put([7.2, y - 0.12, 7.2], [8.8, y + 0.12, 8.8], "ito", Xf.rot("z", a, (8, y, 8)), name="ito")
    b.chamfer_box([7.12, 0, 7.12], [8.88, 0.5, 8.88], 0.15, "gold_d", name="kashira")
    b.oct("y", 8, 8, 2.3, 7.0, 7.6, "black", name="tsuba")
    b.oct("y", 8, 8, 2.35, 7.25, 7.35, "gold", name="tsuba_rim")
    b.chamfer_box([7.3, 7.6, 7.2], [8.7, 8.6, 8.8], 0.12, "gold", name="habaki")
    # 칼날 (얇은 판 0.4): 5마디, 마디마다 2.5°씩 칼등(z+) 쪽으로 누적되어 휨 (소리), 날 쪽 연마선
    xf = Xf(); y = 8.6; segs = (5.2, 4.6, 4.2, 3.8, 3.4)
    for k, L in enumerate(segs):
        if k:
            xf = xf * Xf.rot("x", 2.5, (8, y, 8.0))
        b.put([7.8, y - 0.25, 7.3], [8.2, y + L, 8.75], "blade", xf, name="blade")
        b.put([7.83, y - 0.25, 7.22], [8.17, y + L, 7.55], "hone", xf, name="hamon")
        b.put([7.78, y - 0.25, 8.55], [8.22, y + L, 8.78], "blade_d", xf, name="mune")
        y += L
    # 킷사키: 칼등(z+)은 곧게 이어지고, 날(z−) 쪽이 사선으로 올라가 칼등과 만남 (사선 판이 채움보다 두꺼움)
    b.put([7.78, y - 0.08, 8.55], [8.22, y + 2.0, 8.78], "blade_d", xf, name="mune_tip")
    T = math.tan(math.radians(36)); yy = y - 0.05
    while yy < y + 2.0:
        z0 = 7.3 + T * (yy + 0.3 - y) + 0.08
        if z0 >= 8.5:
            break
        b.put([7.82, yy, z0], [8.18, yy + 0.32, 8.75], "blade", xf, name="kissaki_fill")
        yy += 0.28
    kx = xf * Xf.rot("x", 36, (8, y, 7.3))
    b.put([7.78, y, 7.22], [8.22, y + 2.0, 7.75], "hone", kx, name="kissaki_edge")


# ───────── 둔기 ─────────
def bat(b):
    rod(b, 0, 0.8, 1.3, "wood_d", name="knob")
    rod(b, 0.8, 7.5, 0.75, "tape", name="grip")
    rings(b, _ys(1.2, 7.1, 6), 0.8, "tape_d", name="tape_wrap")
    taper(b, 7.4, 15.0, 0.76, 1.0, "wood", name="taper")
    taper(b, 14.95, 21.0, 1.0, 1.38, "wood", name="taper")
    taper(b, 20.95, 28.0, 1.38, 1.55, "wood_l", name="barrel")
    rod(b, 27.95, 28.6, 1.42, "wood_l", name="cap")


def baton(b):
    rod(b, 0, 8, 0.85, "foam", name="grip")
    rings(b, _ys(0.8, 7.4, 6), 0.9, "rubber", h=0.18, name="grip_ridge")
    b.chamfer_box([7.15, 0, 7.15], [8.85, 0.5, 8.85], 0.15, "steel_d", name="cap")
    rod(b, 7.9, 8.4, 0.7, "steel_d", name="collar1")
    rod(b, 8.0, 16.0, 0.55, "black_t", name="tube1")
    rod(b, 15.9, 16.3, 0.5, "steel", name="collar2")
    rod(b, 16.0, 23.0, 0.42, "steel_l", name="tube2")
    rod(b, 22.8, 23.2, 0.5, "steel", name="tip_neck")
    rod(b, 23.1, 24.1, 0.7, "chrome", name="tip")
    rod(b, 22.9, 24.3, 0.45, "chrome", name="tip")
    b.oct("x", 23.6, 8, 0.62, 7.3, 8.7, "chrome", name="tip_ball")
    b.oct("z", 8, 23.6, 0.62, 7.3, 8.7, "chrome", name="tip_ball")


def pipe(b):
    rod(b, 1.6, 20.6, 0.85, "pipe_s", name="pipe")
    rings(b, [0.25, 0.6, 0.95, 1.3], 0.95, "steel", h=0.18, name="thread")
    rod(b, 0, 1.7, 0.8, "pipe_s", name="pipe_end")
    rings(b, [20.75, 21.1, 21.45, 21.8], 0.95, "steel", h=0.18, name="thread")
    rod(b, 20.5, 22.6, 0.8, "pipe_s", name="pipe_top")
    rod(b, 22.0, 22.5, 1.35, "steel", name="washer")
    rod(b, 22.5, 25.6, 1.25, "pipe_k", name="elbow_v")
    b.chamfer_box([6.75, 24.2, 6.75], [9.25, 26.8, 10.4], 0.5, "pipe_k", name="elbow")
    b.oct("z", 8, 25.6, 1.25, 9.6, 12.6, "pipe_k", name="elbow_h")
    for k in range(3):
        z = 12.7 + k * 0.32
        b.oct("z", 8, 25.6, 1.05, z, z + 0.18, "steel", name="thread")
    b.oct("z", 8, 25.6, 0.95, 12.6, 14.0, "steel", name="plug")
    b.oct("z", 8, 25.6, 0.45, 13.95, 14.05, "bore", name="plug_hole")


def golf_club(b):
    taper(b, 0.3, 8.0, 0.8, 0.68, "rubber", name="grip")
    rod(b, 0, 0.35, 0.82, "black_t", name="grip_cap")
    for y in (1.6, 4.1, 6.4):
        rod(b, y, y + 0.06, 0.82, "rubber_t", name="grip_line")
    rod(b, 7.9, 8.4, 0.55, "black", name="ferrule")
    taper(b, 8.2, 23.0, 0.42, 0.32, "chrome", name="shaft")
    taper(b, 22.6, 25.0, 0.34, 0.5, "steel", name="hosel")
    # 아이언 헤드: 얇은 판(두께 0.8), 토(z+)가 둥글게 높아짐, 앞(+x) 면에 그루브, 로프트 10°
    hx = Xf.rot("z", -10, (8, 24.2, 8)) * Xf.rot("x", 8, (8, 24.2, 7.6))
    b.put([7.6, 24.1, 7.4], [8.4, 25.8, 12.4], "steel", hx, name="head")
    b.put([7.6, 25.0, 10.6], [8.4, 26.3, 12.4], "steel", hx * Xf.rot("x", 22.5, (8, 26.3, 12.4)), name="toe")
    b.put([7.5, 24.0, 7.5], [8.5, 24.35, 12.3], "steel_d", hx, name="sole")
    for k in range(5):
        y = 24.55 + k * 0.28
        b.put([8.38, y, 8.0], [8.43, y + 0.08, 11.6], "steel_d", hx, name="groove")
    b.put([7.56, 24.6, 9.0], [7.6, 25.5, 11.8], "steel_l", hx, name="cavity")


def crowbar(b):
    # 빨간 도장 몸통 + 양 끝 칠 벗겨진 쇠
    b.oct("y", 8, 8, 0.62, 0.8, 21.7, "red", name="shaft")
    R = 1.6; cy, cz = 21.6, 8 + R
    for k in range(5):
        ph = math.radians((k + 0.5) * 36)
        py, pz = cy + R * math.sin(ph), cz - R * math.cos(ph)
        L = 2 * R * math.sin(math.radians(18)) + 0.5
        b.put([7.38, py - L / 2, pz - 0.62], [8.62, py + L / 2, pz + 0.62], "red", Xf.rot("x", math.degrees(ph), (8, py, pz)), name="hook")
    b.put([7.38, 20.0, cz + R - 0.62], [8.62, 21.75, cz + R + 0.62], "red", name="hook_down")
    tx = Xf.rot("x", 12, (8, 20.0, cz + R))
    for sx in (7.4, 8.12):   # 쪼개진 노루발: 끝으로 얇아지는 쐐기
        b.put([sx, 18.6, cz + R - 0.5], [sx + 0.48, 20.2, cz + R + 0.5], "steel", tx, name="claw")
        b.put([sx + 0.06, 17.8, cz + R - 0.3], [sx + 0.42, 18.7, cz + R + 0.3], "steel", tx, name="claw_tip")
    cx_ = Xf.rot("x", -22.5, (8, 0.8, 8))
    b.chamfer_box([7.45, 0, 7.45], [8.55, 1.2, 10.2], 0.2, "red", cx_, name="chisel")
    b.put([7.5, 0.15, 10.0], [8.5, 1.05, 11.2], "steel", cx_, name="chisel_tip")
    b.put([7.55, 0.3, 11.1], [8.45, 0.9, 11.9], "steel", cx_, name="chisel_edge")


def hammer(b, top=15.0, short=False):
    r = 0.7 if short else 0.8
    rod(b, 0, top + 0.6, r, "wood", name="handle")
    gt = 4 if short else 6
    rod(b, 0, gt, r + 0.15, "rubber", name="grip")
    rings(b, _ys(0.4, gt - 0.4, 4), r + 0.2, "rubber_t", name="grip_ring")
    b.chamfer_box([7.0, top - 0.6, 6.0], [9.0, top + 2.2, 11.0], 0.3, "steel_d", name="head")
    b.oct("z", 8, top + 0.8, 1.1, 10.8, 11.2, "steel_k", name="neck")
    b.oct("z", 8, top + 0.8, 1.0, 11.1, 12.6, "steel", name="face")
    # 노루발: 머리에서 이어져 두 마디로 아래로 휨, 두 갈래가 V 로 벌어지며 끝으로 얇아지는 쐐기
    c1 = Xf.rot("x", -15, (8, top + 1.8, 6.2))
    c2 = c1 * Xf.rot("x", -20, (8, top + 1.6, 4.4))
    for sx, sg in ((7.2, 1), (8.3, -1)):
        sp = Xf.rot("y", sg * 6, (sx + 0.25, 0, 6.2))
        b.chamfer_box([sx, top + 0.2, 4.3], [sx + 0.5, top + 1.9, 6.4], 0.15, "steel_d", c1 * sp, name="claw")
        b.chamfer_box([sx + 0.08, top + 0.6, 2.6], [sx + 0.42, top + 1.6, 4.5], 0.1, "steel_d", c2 * sp, name="claw_tip")


def sledgehammer(b):
    rod(b, 0, 26.4, 0.85, "wood", name="handle")
    rod(b, 0, 5, 1.0, "rubber", name="grip")
    rings(b, _ys(0.4, 4.6, 5), 1.05, "rubber_t", name="grip_wrap")
    rod(b, 23.0, 25.2, 1.0, "wood_d", name="neck")
    b.chamfer_box([6.7, 25.0, 4.4], [9.3, 29.4, 11.6], 0.55, "steel_d", name="head")
    for z0, z1 in ((3.6, 4.5), (11.5, 12.4)):
        b.oct("z", 8, 27.2, 1.3, z0, z1, "steel", name="face")
    b.put([6.68, 26.4, 6.0], [6.72, 28.0, 10.0], "steel_l", name="mark")


# ───────── 생활용품 ─────────
def ring_z(b, cx, cy, r_out, th, z0, z1, mat, name):
    """z축 팔각 고리 (판 8장)"""
    w = r_out * math.tan(math.radians(22.5)) * 1.04
    for k in range(8):
        b.put([cx - w, cy + r_out - th, z0], [cx + w, cy + r_out, z1], mat, Xf.rot("z", k * 45 + 22.5, (cx, cy, 0)), name=name)


def pot(b):
    rod(b, 0, 9.6, 0.62, "black", name="handle")
    b.oct("x", 0.9, 8, 0.45, 7.3, 8.7, "steel", name="hang_ring")
    b.chamfer_box([7.3, 9.3, 7.3], [8.7, 11.0, 8.7], 0.15, "pot", name="bracket")
    for z in (7.5, 8.5):
        b.oct("x", 10.6, z, 0.16, 7.25, 8.75, "steel_l", name="rivet")
    # 속 빈 몸통: 팔각 벽(판 8장) + 안쪽 바닥(깊이 있음) + 바깥 바닥
    ring_z(b, 8, 15.4, 5.0, 0.45, 4.4, 11.0, "pot", "wall")
    ring_z(b, 8, 15.4, 5.4, 0.55, 10.6, 11.3, "steel", "rim")
    b.oct("z", 8, 15.4, 4.7, 4.45, 4.9, "pan_in", name="inside_bottom")
    b.oct("z", 8, 15.4, 4.6, 4.0, 4.5, "steel_k", name="bottom")
    b.chamfer_box([2.0, 14.6, 7.0], [3.0, 16.2, 9.0], 0.2, "black", name="side_handle")


def frying_pan(b):
    rod(b, 0, 11, 0.7, "black", name="handle")
    b.oct("x", 1.4, 8, 0.38, 7.26, 8.74, "bore", name="hang_hole")
    b.chamfer_box([7.4, 10.4, 7.5], [8.6, 12.4, 8.5], 0.12, "steel_d", name="bracket")
    for y in (11.0, 11.8):
        b.oct("x", y, 8.0, 0.16, 7.36, 8.64, "steel_l", name="rivet")
    b.oct("z", 8, 18.5, 6.2, 7.6, 8.6, "anod", name="base")
    b.oct("z", 8, 18.5, 5.5, 8.55, 8.62, "pan_in", name="surface")
    ring_z(b, 8, 18.5, 6.2, 0.75, 8.55, 9.3, "steel_d", "rim")


def briefcase(b):
    b.chamfer_box([6.0, 0.0, 7.4], [10.0, 1.0, 8.6], 0.4, "leather_d", name="handle")
    for x in (6.0, 9.2):
        b.chamfer_box([x, 0.4, 7.45], [x + 0.8, 2.7, 8.55], 0.25, "leather_d", name="handle_post")
        b.chamfer_box([x - 0.1, 2.3, 7.3], [x + 0.9, 2.8, 8.7], 0.1, "brass", name="handle_mount")
    b.chamfer_box([1.5, 2.6, 6.4], [14.5, 12.6, 9.6], 0.5, "leather", name="body")
    b.put([1.45, 2.55, 7.9], [14.55, 12.65, 8.1], "leather_d", name="seam")
    for z in (6.38, 9.58):   # 테두리 파이핑
        b.put([1.6, 2.7, z - 0.04], [14.4, 2.85, z + 0.04], "leather_d", name="piping")
        b.put([1.6, 12.35, z - 0.04], [14.4, 12.5, z + 0.04], "leather_d", name="piping")
    for x in (4.0, 11.0):
        b.chamfer_box([x, 12.5, 7.4], [x + 1.0, 12.8, 8.6], 0.08, "brass", name="hinge")
    for x in (1.35, 14.05):
        for y in (2.4, 11.9):
            b.chamfer_box([x, y, 6.25], [x + 0.6, y + 0.8, 9.75], 0.12, "brass", name="corner")
    for x in (4.0, 10.6):
        b.chamfer_box([x, 3.0, 6.2], [x + 1.4, 4.2, 6.45], 0.08, "brass", name="latch")
        b.chamfer_box([x + 0.3, 4.1, 6.25], [x + 1.1, 4.6, 6.45], 0.06, "brass", name="latch_lever")
        b.put([x + 0.5, 3.4, 6.15], [x + 0.9, 3.8, 6.2], "bore", name="keyhole")


def pool_cue(b, short=False):
    rod(b, 0, 0.6, 0.85, "rubber", name="bumper")
    rod(b, 0.6, 3.0, 0.82, "wood_d", name="butt")
    rod(b, 3.0, 7.4, 0.8, "black", name="wrap")
    rings(b, _ys(3.3, 7.1, 5), 0.81, "black_t", h=0.12, name="linen")
    taper(b, 7.4, 13.2, 0.8, 0.66, "wood_d", name="forearm")
    for k in range(4):   # 상아 포인트 상감 (표면과 거의 같은 높이)
        b.put([7.8, 8.0, 7.25], [8.2, 10.6, 7.3], "ivory", Xf.rot("y", k * 90, (8, 0, 8)), name="inlay")
    rod(b, 13.1, 13.7, 0.68, "ivory", name="joint")
    if short:
        # 부러진 큐대 한 자루: 샤프트가 비스듬히 꺾여 부러진 끝. 쪼가리는 샤프트 굵기 안에서만 들쭉날쭉 (펼쳐진 막대 묶음 X)
        rod(b, 13.6, 15.6, 0.56, "maple", name="shaft")
        r = 0.5
        for (x0, x1, z0, z1, top) in ((7.5, 8.0, 7.5, 8.0, 16.9), (8.0, 8.5, 7.5, 8.0, 16.3), (7.5, 8.0, 8.0, 8.5, 16.1), (8.0, 8.5, 8.0, 8.5, 15.8)):
            b.put([x0, 15.5, z0], [x1, top, z1], "maple", name="break_part")
            b.put([x0 + 0.03, top - 0.12, z0 + 0.03], [x1 - 0.03, top, z1 - 0.03], "wood_raw", name="break_end")
        b.put([7.55, 16.8, 7.55], [7.8, 17.5, 7.8], "wood_raw", Xf.rot("z", -8, (7.67, 16.8, 7.67)), name="splinter_tip")
    else:
        taper(b, 13.6, 30.5, 0.58, 0.42, "maple", name="shaft")
        rod(b, 30.5, 31.2, 0.45, "white", name="ferrule")
        rod(b, 31.2, 31.6, 0.42, "chalk", name="tip")


def fire_axe(b):
    """소방도끼: 손잡이 +Y (y 0~28), 날은 −z, 곡괭이 뿔은 +z, 두께 x (기존 팩과 같은 방향)"""
    rod(b, 0.0, 0.3, 1.0, "steel_d", name="cap")
    rod(b, 0.3, 0.8, 1.14, "rubber", name="swell")
    rod(b, 0.8, 7.6, 0.92, "rubber", name="grip")
    rings(b, _ys(1.6, 7.0, 6), 1.0, "rubber_t", h=0.3, name="grip_rib")
    rod(b, 7.6, 7.95, 1.0, "rubber_t", name="grip_end")
    rod(b, 7.9, 25.0, 0.8, "glass", name="haft")
    rod(b, 20.1, 20.85, 0.92, "steel", name="collar")
    # 눈 (자루 끼우는 통) + 쐐기
    b.chamfer_box([7.1, 20.8, 6.9], [8.9, 25.2, 9.1], 0.25, "red", name="eye")
    b.chamfer_box([7.84, 25.0, 7.35], [8.16, 25.35, 8.65], 0.06, "steel", name="wedge")
    # 날 (−z): 가운데 판(두꺼움, 앞) + 위/아래로 벌어지는 판(얇음, 뒤에 숨어 바깥 윤곽만 보임) → 이음매 없이 한 장
    b.put([7.7, 21.6, 4.3], [8.3, 24.5, 7.2], "red", name="cheek")
    b.put([7.74, 23.6, 4.3], [8.26, 24.7, 7.1], "red", Xf.rot("x", 8, (8, 24.7, 7.0)), name="cheek_top")
    b.put([7.74, 21.3, 4.3], [8.26, 22.6, 7.1], "red", Xf.rot("x", -14, (8, 21.3, 7.0)), name="cheek_low")
    b.put([7.76, 20.4, 3.05], [8.24, 25.3, 4.45], "ground", name="bevel")
    b.put([7.84, 20.4, 2.7], [8.16, 25.3, 3.1], "hone", name="edge")
    # 곡괭이 뿔 (+z, 11.25° 아래로): 팔각 단면이 끝으로 갈수록 가늘어지는 송곳 (y축 테이퍼를 +z 로 눕힘)
    pk = Xf.rot("x", 11.25, (8, 23.0, 9.0)) * Xf.rot("x", 90, (8, 23.0, 9.0)) * _shift(0, 0, 1.0)   # 막대 축 (8,·,8) → (8,23,9) 에서 +z 로
    taper(b, 23.0 - 0.2, 23.0 + 1.8, 0.62, 0.45, "red", "pick", pk)
    taper(b, 23.0 + 1.7, 23.0 + 4.9, 0.45, 0.06, "ground", "pick_tip", pk)


WEAPONS = {
    "fire_axe": fire_axe, "dagger": dagger, "bat": bat, "pipe": pipe, "golf_club": golf_club, "machete": machete,
    "pot": pot, "frying_pan": frying_pan, "crowbar": crowbar, "katana": katana, "baton": baton, "hammer": hammer,
    "briefcase": briefcase, "pool_cue": pool_cue, "pool_cue_short": lambda b: pool_cue(b, True),
    "cleaver": cleaver, "sledgehammer": sledgehammer,
}


GRAIN = {"wood": "wood_g", "wood_l": "wood_lg", "maple": "maple_g", "wood_d": "wood_dg", "wood_raw": "wood_rg"}


def painter(p, f, i, j, tw, th):
    """3회차~: 나무 면에 길이 방향 결(1텍셀 줄, 끊긴 마디), 파이프에 녹 얼룩(2x2), 삼단봉 손잡이 널링(2x2 체크)"""
    from bbkit import _hash
    fi = "nsewud".index(f[0]) if f[0] in "nsewud" else 0
    pid = int(sum(p.frm) * 7 + sum(p.to) * 13)
    mat = p.mat.split("@")[0]
    tl = "@t" if p.mat.endswith("@t") else ""
    if mat in GRAIN and max(tw, th) >= 8:
        vert = th >= tw
        L, W_ = (th, tw) if vert else (tw, th)
        a, c = (j, i) if vert else (i, j)       # a: 길이 방향, c: 폭 방향
        for k in range(max(1, W_ // 3)):
            col = _hash(pid, fi, k, 11) % W_
            st0 = _hash(pid, fi, k, 12) % max(1, L // 2)
            ln = 4 + _hash(pid, fi, k, 13) % max(1, L - 4)
            if c == col and st0 <= a < st0 + ln:
                return GRAIN[mat] + tl
    if mat == "pipe_s":
        h = _hash(pid, fi, i // 2, j // 3, 21)
        if h % 23 == 0:
            return "rust_s" + tl
    if mat == "foam":
        if ((i // 2) + (j // 2)) % 2 == 0:
            return "rubber_t" + tl
    return None


def _fake_model(parts, uvs):
    return {"elements": [{"from": pt.frm, "to": pt.to, "faces": {f: {"uv": uvs[k][f]} for f in ("north", "south", "east", "west", "up", "down")}}
                         for k, pt in enumerate(parts)]}


def pick_topline(parts):
    """윗모서리 밝은 줄 비율이 TACZ 범위(0.04~0.30) 가운데쯤(0.14) 오도록, 줄을 칠할 부품 묶음(이름별)을 고름.
    고른 부품은 재질 이름에 '@t' 를 붙여(색은 같음) 그 재질만 윗줄을 칠한다."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    import tacz_texstats as T
    def run(sel):
        for pt in parts:
            base = pt.mat.split("@")[0]
            pt.mat = base + "@t" if pt.name in sel else base
        img, uvs = atlas(parts, PAL, density=2, painter=painter, style="tacz2", step=14, topline=TL)
        r = T.stats(T.rects_java(_fake_model(parts, uvs), *img.size), img)
        return r["topline_ratio"] or 0, img, uvs
    for m in list(PAL):
        PAL[m + "@t"] = PAL[m]
    TL = tuple(m + "@t" for m in PAL if "@" not in m)
    names = sorted(set(pt.name for pt in parts))
    contrib = {n: run({n})[0] for n in names}
    sel = set(); cur = 0.0
    for n in sorted(names, key=lambda n: -contrib[n]):
        if contrib[n] > 0 and cur + contrib[n] <= 0.2:
            sel.add(n); cur += contrib[n]
    if not sel:
        pos = [n for n in names if 0 < contrib[n] <= 0.3]
        if pos:
            sel = {min(pos, key=lambda n: contrib[n])}
    tl, img, uvs = run(sel)
    return None, tuple(sorted(sel)), img, uvs, tl


def build(name, render_dir=None, stem=None):
    bbkit.DOT_MODE = "cell"
    bbkit.GRAD = "jag"   # 3회차~: 긴 면 2단 그라데이션을 다시 켜되 경계를 줄마다 ±1텍셀 흔듦 (곧은 두 톤 경계 없이 길이 방향 명암)
    bbkit.OCT_STAGGER = True   # 2회차~: 팔각 판 끝면 겹침 깜빡임 제거
    bbkit.ROT_NORMALIZE = True   # 3회차~: 45° 넘는 한 축 회전은 90° 배수를 상자 크기 교환으로 (프라이팬 테두리 튀어나옴)
    bbkit.TOPLINE_WIDE_ONLY = True   # 4회차~: 세로 막대 마디마다 밝은 가로 띠 방지
    bbkit.DOT_MIX = True   # 3회차~: 점 모양 가로2·가로3·세로2 섞기 (같은 크기 사각 반복 지적)
    bbkit.DOT_P = 0.35   # 작은 막대 면이 많아 점이 촘촘하면 얼룩이 TACZ보다 세짐
    b = Builder()
    bbkit.GRAD = False if name in ("briefcase", "pot", "frying_pan") else "jag"   # 넓고 둥근/큰 판은 명암 경계가 반으로 갈라 보임
    WEAPONS[name](b)
    out = os.path.join(HERE, "out", name); os.makedirs(out, exist_ok=True)
    _, tl_mats, img, uvs, tl = pick_topline(b.parts)
    png = os.path.join(out, name + ".png"); img.save(png)
    bb = os.path.join(out, name + ".bbmodel")
    build_bbmodel(bb, name, b.parts, png, uvs, name)
    validate(bb)
    export_java(bb, os.path.join(out, name + ".json"))
    if render_dir:
        render_views(bb, render_dir, stem or name, views=("right", "front", "three-quarter", "top"))
    print(f"{name}: parts={len(b.parts)} tex={img.size} topline={tl_mats}->{tl}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)
