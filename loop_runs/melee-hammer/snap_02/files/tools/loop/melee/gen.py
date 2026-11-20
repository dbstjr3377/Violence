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
    "anod":    (54, 54, 59),   "pan_in": (34, 34, 37), "pot": (70, 74, 80), "bore": (10, 10, 11),
}
# 윗모서리 밝은 줄: 금속 머리·칼등·가죽처럼 '위로 놓인 면'이 있는 재질만
TOPLINE = ("steel_d", "steel_k", "blade_d", "red", "red_d", "leather", "anod", "pot")


def rod(b, y0, y1, r, mat, x=8, z=8, name="rod"):
    b.oct("y", x, z, r, y0, y1, mat, name=name)


def taper(b, y0, y1, r0, r1, mat, name="taper"):
    """반지름이 r0→r1 로 매끈하게 바뀌는 팔각 막대: 가는 쪽 팔각 심 + 기울어진 옆판 8장 (계단 턱 없음)"""
    rmin = min(r0, r1); rm = (r0 + r1) / 2; L = y1 - y0
    rod(b, y0, y1, rmin * 0.97, mat, name=name)
    phi = math.degrees(math.atan2(r1 - r0, L))
    w = rm * math.tan(math.radians(22.5)) * 1.06
    t = min(0.35, rm * 0.5)
    for k in range(8):
        xf = Xf.rot("y", k * 45, (8, 0, 8)) * Xf.rot("x", phi, (8, (y0 + y1) / 2, 8 + rm))
        b.put([8 - w, y0, 8 + rm - t], [8 + w, y1, 8 + rm], mat, xf, name=name)


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
    # 날: x 폭, z 두께. x+ 쪽 날(베벨+연마선), x- 쪽 등. 끝은 날 쪽 사선이 등 쪽으로 모이는 클립 포인트
    b.put([7.25, 7.5, 7.7], [8.75, 13.4, 8.3], "blade", name="blade")
    b.put([8.35, 7.5, 7.75], [8.8, 13.4, 8.25], "edge", name="bevel")
    b.put([7.85, 8.2, 7.66], [8.15, 13.0, 8.34], "blade_d", name="fuller")
    b.put([7.2, 7.5, 7.74], [7.4, 15.5, 8.26], "blade_d", name="spine")
    for (x1, y0, y1) in ((8.5, 13.3, 14.2), (8.2, 14.1, 15.0), (7.9, 14.9, 15.7)):
        b.put([7.25, y0, 7.72], [x1, y1, 8.28], "blade", name="tip_fill")
    dx = Xf.rot("z", 22.5, (8.75, 12.8, 8))
    b.put([8.3, 12.8, 7.74], [8.75, 16.5, 8.26], "blade", dx, name="tip_slope")
    b.put([8.62, 12.8, 7.78], [8.8, 16.4, 8.22], "edge", dx, name="tip_edge")


def machete(b):
    b.chamfer_box([7.3, 0, 7.2], [8.7, 6.6, 8.8], 0.45, "black", name="handle")
    b.chamfer_box([7.3, 0.5, 6.95], [8.7, 1.4, 9.05], 0.25, "black_t", name="finger_rest")
    for y in (2.0, 4.4):
        b.oct("x", y, 8.0, 0.24, 7.25, 8.75, "brass", name="rivet")
    b.chamfer_box([7.15, 6.5, 6.85], [8.85, 7.25, 9.15], 0.2, "steel_d", name="bolster")
    # 날: x 두께, z 폭 (z+ 날, z- 등). 손잡이 쪽 좁고 끝으로 갈수록 넓어지는 배, 끝은 등 쪽으로 휨
    for (y0, y1, z1) in ((7.2, 13.0, 9.4), (12.9, 18.0, 9.9), (17.9, 22.0, 10.3)):
        b.put([7.75, y0, 6.6], [8.25, y1, z1], "blade", name="blade")
        b.put([7.72, y0, z1 - 0.45], [8.28, y1, z1], "edge", name="edge")
    b.put([7.7, 7.2, 6.55], [8.3, 23.0, 6.95], "blade_d", name="spine")
    tx = Xf.rot("x", -32, (8, 21.9, 10.3))
    b.put([7.75, 21.9, 7.0], [8.25, 24.6, 10.3], "blade", tx, name="tip")
    b.put([7.72, 21.9, 9.85], [8.28, 24.5, 10.3], "edge", tx, name="tip_edge")
    b.put([7.75, 21.9, 6.6], [8.25, 23.4, 8.0], "blade", name="tip_fill")


def cleaver(b):
    rod(b, 0, 6.2, 0.75, "wood", name="handle")
    for y in (2.0, 4.4):
        b.oct("x", y, 8.0, 0.22, 7.2, 8.8, "brass", name="rivet")
    b.chamfer_box([7.4, 5.8, 7.3], [8.6, 7.0, 8.7], 0.15, "steel", name="bolster")
    # 날판 (얇게, 가운데 구멍은 판을 네 조각으로 둘러 만듦): z 6.2~11.6, y 6.6~16
    hz0, hz1, hy0, hy1 = 9.1, 10.1, 14.1, 15.1
    for frm, to in (([7.82, 6.6, 6.2], [8.18, 16.0, hz0]), ([7.82, 6.6, hz1], [8.18, 16.0, 11.0]),
                    ([7.82, 6.6, hz0], [8.18, hy0, hz1]), ([7.82, hy1, hz0], [8.18, 16.0, hz1])):
        b.put(frm, to, "blade_d", name="blade")
    b.put([7.86, 6.6, 10.95], [8.14, 16.0, 11.45], "ground", name="bevel")
    b.put([7.9, 6.6, 11.4], [8.1, 16.0, 11.65], "edge", name="edge")
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
    # 칼날: 5마디, 마디마다 2.5°씩 칼등(z+) 쪽으로 누적되어 휨 (소리)
    xf = Xf(); y = 8.6; segs = (5.2, 4.6, 4.2, 3.8, 3.4)
    for k, L in enumerate(segs):
        if k:
            xf = xf * Xf.rot("x", 2.5, (8, y, 8.0))
        b.put([7.72, y - 0.05, 7.25], [8.28, y + L, 8.75], "blade", xf, name="blade")
        b.put([7.7, y - 0.05, 7.25], [8.3, y + L, 7.5], "edge", xf, name="hamon")
        b.put([7.7, y - 0.05, 8.55], [8.3, y + L, 8.78], "blade_d", xf, name="mune")
        if k % 2 == 0:
            b.put([7.7, y + L * 0.3, 7.48], [8.3, y + L * 0.7, 7.62], "edge", xf, name="hamon_wave")
        y += L
    kx = xf * Xf.rot("x", 30, (8, y, 8.75))
    b.put([7.72, y - 0.3, 7.25], [8.28, y + 1.6, 8.75], "blade", kx, name="kissaki")
    b.put([7.7, y - 0.3, 7.25], [8.3, y + 1.5, 7.5], "edge", kx, name="kissaki_edge")


# ───────── 둔기 ─────────
def bat(b):
    rod(b, 0, 0.8, 1.3, "wood_d", name="knob")
    rod(b, 0.8, 7.5, 0.75, "tape", name="grip")
    rings(b, _ys(1.2, 7.1, 6), 0.8, "tape_d", name="tape_wrap")
    taper(b, 7.4, 17.2, 0.76, 1.2, "wood", name="taper")
    taper(b, 17.0, 28.0, 1.2, 1.55, "wood_l", name="barrel")
    rod(b, 27.95, 28.6, 1.4, "wood_l", name="cap")


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
    rod(b, 1.6, 20.6, 0.85, "steel_d", name="pipe")
    for (y, h, k) in ((6.2, 0.5, 0), (13.6, 0.7, 3)):
        b.put([7.3, y, 7.12], [7.9, y + h, 7.2], "rust", Xf.rot("y", k * 45, (8, 0, 8)), name="rust")
    rings(b, [0.25, 0.6, 0.95, 1.3], 0.95, "steel", h=0.18, name="thread")
    rod(b, 0, 1.7, 0.8, "steel_d", name="pipe_end")
    rings(b, [20.75, 21.1, 21.45, 21.8], 0.95, "steel", h=0.18, name="thread")
    rod(b, 20.5, 22.6, 0.8, "steel_d", name="pipe_top")
    rod(b, 22.0, 22.5, 1.35, "steel", name="washer")
    rod(b, 22.5, 25.6, 1.25, "steel_k", name="elbow_v")
    b.chamfer_box([6.75, 24.2, 6.75], [9.25, 26.8, 10.4], 0.5, "steel_k", name="elbow")
    b.oct("z", 8, 25.6, 1.25, 9.6, 12.6, "steel_k", name="elbow_h")
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
    taper(b, 22.6, 25.2, 0.34, 0.56, "steel", name="hosel")
    # 아이언 헤드: 얇은 판(두께 1), 토(z+) 쪽이 높아지는 윤곽, 앞(+x) 면에 그루브
    hx = Xf.rot("x", 8, (8, 24.2, 7.6))
    b.chamfer_box([7.5, 24.2, 7.4], [8.5, 25.9, 12.6], 0.25, "steel", hx, name="head")
    b.chamfer_box([7.52, 25.4, 10.4], [8.48, 26.7, 12.7], 0.3, "steel", hx, name="toe")
    b.chamfer_box([7.4, 24.0, 7.6], [8.6, 24.6, 12.4], 0.15, "steel_d", hx, name="sole")
    for k in range(5):
        y = 24.7 + k * 0.32
        b.put([8.48, y, 8.2], [8.54, y + 0.1, 11.8], "steel_d", hx, name="groove")
    b.put([7.46, 24.8, 9.0], [7.5, 25.6, 11.8], "steel_l", hx, name="cavity")


def crowbar(b):
    b.oct("y", 8, 8, 0.62, 0.8, 21.7, "red", name="shaft")
    # 위: 거위목 갈고리 — 반지름 1.6 반원을 5마디로 (각 마디는 호의 접선 방향)
    R = 1.6; cy, cz = 21.6, 8 + R
    for k in range(5):
        ph = math.radians((k + 0.5) * 36)
        py, pz = cy + R * math.sin(ph), cz - R * math.cos(ph)
        L = 2 * R * math.sin(math.radians(18)) + 0.35
        b.chamfer_box([7.4, py - L / 2, pz - 0.6], [8.6, py + L / 2, pz + 0.6], 0.2, "red", Xf.rot("x", math.degrees(ph), (8, py, pz)), name="hook")
    b.chamfer_box([7.4, 20.0, cz + R - 0.6], [8.6, 21.7, cz + R + 0.6], 0.2, "red", name="hook_down")
    tx = Xf.rot("x", 12, (8, 20.0, cz + R))
    for sx in (7.42, 8.1):   # 쪼개진 노루발 (끝으로 얇아짐, 칠 벗겨진 쇠)
        b.chamfer_box([sx, 18.4, cz + R - 0.45], [sx + 0.48, 20.2, cz + R + 0.45], 0.1, "steel_d", tx, name="claw")
    # 아래: 납작 끌 (꺾임) + 얇아지는 쇠 끝
    cx_ = Xf.rot("x", -22.5, (8, 0.8, 8))
    b.chamfer_box([7.45, 0, 7.45], [8.55, 1.2, 10.2], 0.2, "red", cx_, name="chisel")
    b.chamfer_box([7.5, 0.1, 10.0], [8.5, 1.0, 11.0], 0.12, "steel_d", cx_, name="chisel_tip")
    b.chamfer_box([7.6, 0.25, 10.9], [8.4, 0.75, 11.5], 0.08, "steel_d", cx_, name="chisel_edge")


def hammer(b, top=15.0, short=False):
    r = 0.7 if short else 0.8
    rod(b, 0, top + 0.6, r, "wood", name="handle")
    gt = 4 if short else 6
    rod(b, 0, gt, r + 0.15, "rubber", name="grip")
    rings(b, _ys(0.4, gt - 0.4, 4), r + 0.2, "rubber_t", name="grip_ring")
    b.chamfer_box([7.0, top - 0.6, 6.0], [9.0, top + 2.2, 11.0], 0.3, "steel_d", name="head")
    b.oct("z", 8, top + 0.8, 1.1, 10.8, 11.2, "steel_k", name="neck")
    b.oct("z", 8, top + 0.8, 1.0, 11.1, 12.6, "steel", name="face")
    # 노루발: 머리에서 이어져 두 마디로 아래로 휨, 두 갈래
    c1 = Xf.rot("x", -15, (8, top + 1.8, 6.2))
    c2 = c1 * Xf.rot("x", -20, (8, top + 1.6, 4.4))
    for sx in (7.3, 8.2):
        b.chamfer_box([sx, top + 0.2, 4.3], [sx + 0.5, top + 1.9, 6.4], 0.15, "steel_d", c1, name="claw")
        b.chamfer_box([sx + 0.05, top + 0.5, 2.6], [sx + 0.45, top + 1.7, 4.5], 0.12, "steel_d", c2, name="claw_tip")


def sledgehammer(b):
    rod(b, 0, 26.4, 0.85, "wood", name="handle")
    rod(b, 0, 5, 1.0, "rubber", name="grip")
    rings(b, _ys(0.4, 4.6, 5), 1.05, "rubber_t", name="grip_wrap")
    rod(b, 23.0, 25.2, 1.0, "wood_d", name="neck")
    b.chamfer_box([6.7, 25.0, 4.4], [9.3, 29.4, 11.6], 0.55, "steel_d", name="head")
    for z0, z1 in ((3.6, 4.5), (11.5, 12.4)):
        b.oct("z", 8, 27.2, 2.0, z0, z1, "steel", name="face")
    b.put([6.68, 26.4, 6.0], [6.72, 28.0, 10.0], "steel_l", name="mark")


# ───────── 생활용품 ─────────
def pot(b):
    rod(b, 0, 9.6, 0.62, "black", name="handle")
    b.oct("x", 0.9, 8, 0.45, 7.3, 8.7, "steel", name="hang_ring")
    b.chamfer_box([7.3, 9.3, 7.3], [8.7, 11.0, 8.7], 0.15, "pot", name="bracket")
    for z in (7.5, 8.5):
        b.oct("x", 10.6, z, 0.16, 7.25, 8.75, "steel_l", name="rivet")
    b.oct("z", 8, 15.4, 5.0, 4.4, 11.0, "pot", name="body")
    b.oct("z", 8, 15.4, 5.4, 10.6, 11.3, "steel", name="rim")
    b.oct("z", 8, 15.4, 4.5, 11.3, 11.36, "pan_in", name="inside")
    b.oct("z", 8, 15.4, 4.6, 4.0, 4.45, "steel_k", name="bottom")
    b.chamfer_box([2.0, 14.6, 7.0], [3.0, 16.2, 9.0], 0.2, "black", name="side_handle")


def frying_pan(b):
    rod(b, 0, 11, 0.7, "black", name="handle")
    b.oct("x", 1.4, 8, 0.38, 7.26, 8.74, "bore", name="hang_hole")
    b.chamfer_box([7.4, 10.4, 7.5], [8.6, 12.4, 8.5], 0.12, "steel_d", name="bracket")
    for y in (11.0, 11.8):
        b.oct("x", y, 8.0, 0.16, 7.36, 8.64, "steel_l", name="rivet")
    b.oct("z", 8, 18.5, 6.2, 7.6, 8.6, "anod", name="base")
    b.oct("z", 8, 18.5, 5.4, 8.6, 8.66, "pan_in", name="surface")
    for k in range(8):   # 테두리 (안쪽 면 위로 솟은 고리)
        b.put([8 - 2.6, 18.5 + 5.4, 8.55], [8 + 2.6, 18.5 + 6.2, 9.3], "anod", Xf.rot("z", k * 45 + 22.5, (8, 18.5, 0)), name="rim")


def briefcase(b):
    b.chamfer_box([6.0, 0.0, 7.4], [10.0, 1.0, 8.6], 0.4, "leather_d", name="handle")
    for x in (6.0, 9.2):
        b.chamfer_box([x, 0.4, 7.45], [x + 0.8, 2.7, 8.55], 0.25, "leather_d", name="handle_post")
        b.chamfer_box([x - 0.1, 2.3, 7.3], [x + 0.9, 2.8, 8.7], 0.1, "brass", name="handle_mount")
    b.chamfer_box([1.5, 2.6, 6.4], [14.5, 14.6, 9.6], 0.5, "leather", name="body")
    b.put([1.45, 2.55, 7.9], [14.55, 14.65, 8.1], "leather_d", name="seam")
    for z in (6.38, 9.58):   # 테두리 파이핑
        b.put([1.6, 2.7, z - 0.04], [14.4, 2.85, z + 0.04], "leather_d", name="piping")
        b.put([1.6, 14.35, z - 0.04], [14.4, 14.5, z + 0.04], "leather_d", name="piping")
    for x in (4.0, 11.0):
        b.chamfer_box([x, 14.5, 7.4], [x + 1.0, 14.8, 8.6], 0.08, "brass", name="hinge")
    for x in (1.3, 13.9):
        for y in (2.3, 13.8):
            b.chamfer_box([x, y, 6.2], [x + 0.8, y + 1.1, 9.8], 0.15, "brass", name="corner")
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
        rod(b, 13.6, 15.2, 0.56, "maple", name="shaft")
        # 부러진 끝: 굵기·높이·기울기가 다른 파편들
        for (x0, z0, w, d, h, ax, ang) in ((7.5, 7.6, 0.45, 0.4, 2.4, "z", 10), (8.0, 7.55, 0.4, 0.5, 1.6, "x", -14),
                                           (7.6, 8.1, 0.5, 0.35, 1.9, "x", 18), (8.1, 8.1, 0.35, 0.35, 1.1, "z", -22),
                                           (7.85, 7.85, 0.3, 0.3, 2.9, "z", -6)):
            xf = Xf.rot(ax, ang, (x0 + w / 2, 15.1, z0 + d / 2))
            b.put([x0, 15.0, z0], [x0 + w, 15.0 + h, z0 + d], "maple", xf, name="splinter")
            b.put([x0 + 0.02, 15.0 + h - 0.15, z0 + 0.02], [x0 + w - 0.02, 15.0 + h, z0 + d - 0.02], "wood_raw", xf, name="splinter_end")
        b.put([7.5, 15.1, 7.5], [8.5, 15.2, 8.5], "wood_raw", name="break")
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
    # 날 (−z): 한 장으로 이어진 판 — 가운데 판 + 위/아래로 벌어지는 판(가운데와 겹쳐 틈 없음)
    secs = ((Xf(), 21.7, 24.3), (Xf.rot("x", 14, (8, 24.3, 7.0)), 22.9, 24.7), (Xf.rot("x", -14, (8, 21.7, 7.0)), 21.3, 23.1))
    for xf, y0, y1 in secs:
        b.put([7.72, y0, 4.4], [8.28, y1, 7.2], "red", xf, name="cheek")
        b.put([7.8, y0, 3.1], [8.2, y1, 4.5], "ground", xf, name="bevel")
        b.put([7.88, y0, 2.7], [8.12, y1, 3.15], "edge", xf, name="edge")
    # 곡괭이 뿔 (+z, 11.25° 아래로): 위·아래 판이 끝점으로 모이는 쐐기
    pk = Xf.rot("x", 11.25, (8, 23.0, 9.0))
    b.chamfer_box([7.55, 22.3, 8.8], [8.45, 23.7, 11.0], 0.2, "red", pk, name="pick")
    tip = 14.2
    for sgn in (1, -1):
        f = pk * Xf.rot("x", sgn * 10, (8, 23.0, tip))
        y0, y1 = (23.0, 23.6) if sgn > 0 else (22.4, 23.0)
        b.put([7.6, y0, 10.9], [8.4, y1, tip], "ground", f, name="pick_face")
    for (z0, z1, h) in ((10.9, 12.0, 0.5), (11.9, 13.0, 0.33), (12.9, 13.7, 0.16)):   # 두 판 사이 속채움 (끝으로 갈수록 얇게)
        b.put([7.62, 23.0 - h, z0], [8.38, 23.0 + h, z1], "ground", pk, name="pick_core")


WEAPONS = {
    "fire_axe": fire_axe, "dagger": dagger, "bat": bat, "pipe": pipe, "golf_club": golf_club, "machete": machete,
    "pot": pot, "frying_pan": frying_pan, "crowbar": crowbar, "katana": katana, "baton": baton, "hammer": hammer,
    "briefcase": briefcase, "pool_cue": pool_cue, "pool_cue_short": lambda b: pool_cue(b, True),
    "cleaver": cleaver, "sledgehammer": sledgehammer,
}


def build(name, render_dir=None, stem=None):
    bbkit.DOT_MODE = "cell"
    bbkit.GRAD = False   # 2회차~: 실제로 끔 (1회차는 공용 도구 되돌림으로 켜져 있었음 → 면 반쪽 두 톤)
    bbkit.OCT_STAGGER = True   # 2회차~: 팔각 판 끝면 겹침 깜빡임 제거
    bbkit.DOT_P = 0.35   # 작은 막대 면이 많아 점이 촘촘하면 얼룩이 TACZ보다 세짐
    b = Builder()
    WEAPONS[name](b)
    out = os.path.join(HERE, "out", name); os.makedirs(out, exist_ok=True)
    img, uvs = atlas(b.parts, PAL, density=2, style="tacz2", step=14, topline=TOPLINE)
    png = os.path.join(out, name + ".png"); img.save(png)
    bb = os.path.join(out, name + ".bbmodel")
    build_bbmodel(bb, name, b.parts, png, uvs, name)
    validate(bb)
    export_java(bb, os.path.join(out, name + ".json"))
    if render_dir:
        render_views(bb, render_dir, stem or name, views=("right", "front", "three-quarter", "top"))
    print(f"{name}: parts={len(b.parts)} tex={img.size}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)
