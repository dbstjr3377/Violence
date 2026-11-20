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
    "wood":    (100, 64, 40),  "wood_l": (114, 76, 48), "wood_d": (74, 46, 28),
    "rubber":  (30, 30, 32),   "rubber_t": (42, 42, 45), "tape": (40, 40, 44), "tape_d": (28, 28, 31),
    "steel":   (86, 90, 98),   "steel_d": (52, 54, 58),  "steel_l": (108, 112, 120),
    "blade":   (90, 94, 102), "blade_d": (72, 76, 84), "edge": (126, 130, 140),
    "black":   (40, 40, 43),   "black_t": (54, 54, 57),
    "chrome":  (112, 116, 124), "gold": (150, 118, 52), "gold_d": (112, 86, 38),
    "cloth":   (34, 34, 38),   "ito": (120, 30, 34),
    "foam":    (44, 44, 47),   "red": (92, 30, 28), "red_d": (72, 24, 22), "rust": (110, 62, 36),
    "leather": (86, 54, 34),   "leather_d": (66, 40, 26), "brass": (150, 118, 52),
    "ivory":   (188, 178, 156), "white": (196, 196, 192), "chalk": (60, 92, 150),
    "glass":   (46, 48, 52),   "ground": (128, 134, 144),
    "anod":    (58, 58, 63),   "pan_in": (40, 40, 43), "bore": (10, 10, 11),
}
TOPLINE = ()   # 세로로 쥐는 물건이라 옆면 '윗줄'은 막대 끝 단면 쪽이 됨 → 칠하지 않음


def rod(b, y0, y1, r, mat, x=8, z=8, name="rod"):
    b.oct("y", x, z, r, y0, y1, mat, name=name)


def taper(b, y0, y1, r0, r1, n, mat, name="taper"):
    """반지름이 r0→r1 로 바뀌는 막대 (n 마디 계단, 마디끼리 살짝 겹침)"""
    for k in range(n):
        a = y0 + (y1 - y0) * k / n; c = y0 + (y1 - y0) * (k + 1) / n
        rod(b, a - (0.02 if k else 0), c + 0.02, r0 + (r1 - r0) * (k + 0.5) / n, mat, name=name)


def rings(b, y0, y1, n, r, mat, name="ring"):
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        rod(b, y - 0.1, y + 0.1, r, mat, name=name)


# ───────── 칼 ─────────
def dagger(b):
    rod(b, 0.6, 6.8, 0.85, "rubber", name="handle")
    rings(b, 1.2, 6.4, 5, 0.9, "rubber_t", name="grip_ring")
    b.chamfer_box([7.05, 0, 7.05], [8.95, 0.75, 8.95], 0.2, "steel_d", name="pommel")
    b.chamfer_box([5.9, 6.8, 7.35], [10.1, 7.55, 8.65], 0.2, "steel_d", name="guard")
    # 날: x 폭, z 두께. 오른쪽(x+) 날 끝 연마선, 왼쪽 등날
    b.chamfer_box([7.25, 7.5, 7.68], [8.75, 15.0, 8.32], 0.06, "blade", name="blade", edges="y")
    b.put([8.45, 7.6, 7.66], [8.78, 15.0, 8.34], "edge", name="edge")
    b.put([7.85, 8.2, 7.64], [8.15, 13.6, 8.36], "blade_d", name="fuller")
    b.put([7.22, 7.6, 7.75], [7.4, 14.6, 8.25], "blade_d", name="spine")
    b.chamfer_box([7.25, 14.8, 7.7], [8.45, 16.4, 8.3], 0.05, "blade", Xf.rot("z", -22.5, (7.25, 15.0, 8)), name="tip")
    b.put([8.15, 14.8, 7.68], [8.48, 16.2, 8.32], "edge", Xf.rot("z", -22.5, (7.25, 15.0, 8)), name="tip_edge")


def machete(b):
    b.chamfer_box([7.25, 0, 7.15], [8.75, 6.6, 8.85], 0.3, "black", name="handle")
    for y in (1.8, 4.6):
        b.oct("x", y, 8.0, 0.25, 7.18, 8.82, "steel_l", name="rivet")
    b.chamfer_box([7.3, 0.6, 6.95], [8.7, 1.4, 9.05], 0.2, "black_t", name="finger_rest")
    b.chamfer_box([7.1, 6.5, 6.85], [8.9, 7.25, 9.15], 0.15, "steel_d", name="bolster")
    # 날: x 두께, z 폭 (z+ 쪽이 날, z- 쪽이 등)
    b.put([7.65, 7.2, 6.6], [8.35, 22.5, 9.9], "blade", name="blade")
    b.put([7.62, 7.2, 9.35], [8.38, 22.5, 9.9], "edge", name="edge")
    b.put([7.62, 7.2, 6.6], [8.38, 22.5, 7.0], "blade_d", name="spine")
    tx = Xf.rot("x", -22.5, (8, 22.5, 9.9))
    b.put([7.65, 21.0, 7.4], [8.35, 25.5, 10.2], "blade", tx, name="tip")
    b.put([7.62, 21.0, 9.7], [8.38, 25.3, 10.2], "edge", tx, name="tip_edge")


def cleaver(b):
    rod(b, 0, 6.2, 0.75, "wood", name="handle")
    for y in (2.0, 4.4):
        b.oct("x", y, 8.0, 0.22, 7.2, 8.8, "steel_l", name="rivet")
    b.chamfer_box([7.4, 5.8, 7.3], [8.6, 7.0, 8.7], 0.15, "steel", name="bolster")
    # 날판 (가운데 구멍은 판을 네 조각으로 둘러 만듦): x 두께, z 6.2~11.6, y 6.6~16
    hz0, hz1, hy0, hy1 = 9.1, 10.1, 14.1, 15.1
    b.put([7.68, 6.6, 6.2], [8.32, 16.0, hz0], "blade", name="blade")
    b.put([7.68, 6.6, hz1], [8.32, 16.0, 11.6], "blade", name="blade")
    b.put([7.68, 6.6, hz0], [8.32, hy0, hz1], "blade", name="blade")
    b.put([7.68, hy1, hz0], [8.32, 16.0, hz1], "blade", name="blade")
    b.put([7.65, 6.6, 11.1], [8.35, 16.0, 11.6], "edge", name="edge")
    b.chamfer_box([7.6, 6.6, 5.6], [8.4, 16.0, 6.25], 0.1, "blade_d", name="spine")


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
    b.put([7.72, 8.6, 7.25], [8.28, 30.0, 8.75], "blade", name="blade")
    b.put([7.7, 8.6, 7.25], [8.3, 30.0, 7.55], "edge", name="hamon")
    for k in range(7):   # 물결 하몬
        y = 10 + k * 2.8
        b.put([7.7, y, 7.5], [8.3, y + 1.2, 7.68], "edge", name="hamon_wave")
    b.put([7.7, 8.6, 8.55], [8.3, 30.0, 8.78], "blade_d", name="mune")
    b.put([7.72, 29.0, 7.3], [8.28, 31.6, 8.5], "blade", Xf.rot("x", 22.5, (8, 30, 8.75)), name="kissaki")


# ───────── 둔기 ─────────
def bat(b):
    rod(b, 0, 0.8, 1.3, "wood_d", name="knob")
    rod(b, 0.8, 7.5, 0.75, "tape", name="grip")
    rings(b, 1.2, 7.1, 6, 0.8, "tape_d", name="tape_wrap")
    taper(b, 7.5, 17.0, 0.78, 1.15, 5, "wood", name="taper")
    taper(b, 17.0, 28.0, 1.2, 1.55, 4, "wood_l", name="barrel")
    rod(b, 27.9, 28.6, 1.35, "wood_l", name="cap")
    b.put([8.0, 24.0, 6.5], [8.6, 26.2, 6.62], "wood_d", name="brand")


def baton(b):
    rod(b, 0, 8, 0.85, "foam", name="grip")
    rings(b, 0.8, 7.4, 6, 0.9, "black_t", name="grip_ridge")
    b.chamfer_box([7.15, 0, 7.15], [8.85, 0.5, 8.85], 0.15, "steel_d", name="cap")
    rod(b, 7.9, 8.4, 0.7, "steel_d", name="collar1")
    rod(b, 8.0, 16.0, 0.55, "black", name="tube1")
    rod(b, 15.9, 16.3, 0.5, "steel", name="collar2")
    rod(b, 16.0, 23.0, 0.42, "steel_d", name="tube2")
    rod(b, 22.9, 24.0, 0.7, "chrome", name="tip")


def pipe(b):
    rod(b, 1.6, 20.6, 0.85, "steel_d", name="pipe")
    for k, (y, h) in enumerate(((4.0, 0.8), (9.5, 1.4), (14.2, 0.6), (18.0, 1.0))):
        b.put([7.15 + 0.3 * (k % 2), y, 7.12], [8.4 + 0.3 * (k % 2), y + h, 7.2], "rust", name="rust")
    rings(b, 0.1, 1.6, 5, 0.95, "steel", name="thread")
    rod(b, 0, 1.7, 0.8, "steel_d", name="pipe_end")
    rings(b, 20.6, 22.4, 6, 0.95, "steel", name="thread")
    rod(b, 20.5, 22.6, 0.8, "steel_d", name="pipe_top")
    rod(b, 22.0, 22.5, 1.35, "steel", name="washer")
    rod(b, 22.5, 25.6, 1.25, "steel_d", name="elbow_v")
    b.chamfer_box([6.75, 24.2, 6.75], [9.25, 26.8, 10.4], 0.5, "steel_d", name="elbow")
    b.oct("z", 8, 25.6, 1.25, 9.6, 12.6, "steel_d", name="elbow_h")
    for k in range(3):
        z = 12.7 + k * 0.32
        b.oct("z", 8, 25.6, 1.05, z, z + 0.18, "steel", name="thread")
    b.oct("z", 8, 25.6, 0.95, 12.6, 14.0, "steel", name="plug")
    b.oct("z", 8, 25.6, 0.45, 13.95, 14.05, "bore", name="plug_hole")


def golf_club(b):
    rod(b, 0, 8, 0.75, "rubber", name="grip")
    rings(b, 0.6, 7.6, 7, 0.78, "rubber_t", name="grip_line")
    rod(b, 7.9, 8.4, 0.55, "black", name="ferrule")
    taper(b, 8.2, 25.0, 0.42, 0.32, 3, "chrome", name="shaft")
    rod(b, 24.2, 26.6, 0.55, "steel", name="hosel")
    hx = Xf.rot("x", 22.5, (8, 24.5, 8))
    b.chamfer_box([7.2, 24.2, 7.0], [8.8, 26.6, 12.8], 0.3, "steel", hx, name="head")
    for k in range(5):
        y = 24.6 + k * 0.4
        b.put([8.78, y, 7.6], [8.84, y + 0.12, 12.2], "steel_d", hx, name="groove")
    b.put([7.18, 24.5, 9.0], [7.22, 26.0, 11.8], "steel_l", hx, name="cavity")


def crowbar(b):
    b.oct("y", 8, 8, 0.62, 0.8, 21.6, "red", name="shaft")
    # 위: 갈고리 (세 마디로 꺾임) + 쪼개진 노루발
    b.chamfer_box([7.4, 21.0, 7.4], [8.6, 23.0, 9.6], 0.2, "red", Xf.rot("x", 45, (8, 21.5, 8)), name="hook1")
    b.chamfer_box([7.4, 21.5, 9.2], [8.6, 22.6, 12.2], 0.2, "red", name="hook2")
    b.chamfer_box([7.4, 19.8, 11.2], [8.6, 22.6, 12.4], 0.2, "red", name="hook3")
    for sx in (7.45, 8.12):
        b.chamfer_box([sx, 18.4, 11.4], [sx + 0.43, 19.9, 12.2], 0.08, "steel", name="claw")
    # 아래: 납작 끌 (꺾임) + 쇠 끝
    b.chamfer_box([7.45, 0, 7.45], [8.55, 1.2, 10.2], 0.2, "red", Xf.rot("x", -22.5, (8, 0.8, 8)), name="chisel")
    b.chamfer_box([7.6, -0.2, 10.0], [8.4, 0.7, 11.0], 0.1, "steel", name="chisel_tip")
    b.put([7.35, 9.0, 7.38], [8.65, 13.0, 7.42], "red_d", name="label")


def hammer(b, top=15.0, short=False):
    r = 0.7 if short else 0.8
    rod(b, 0, top, r, "wood", name="handle")
    rod(b, 0, 4 if short else 6, r + 0.15, "rubber", name="grip")
    rings(b, 0.4, (4 if short else 6) - 0.4, 4, r + 0.2, "rubber_t", name="grip_ring")
    b.chamfer_box([7.0, top - 0.6, 6.0], [9.0, top + 2.2, 11.0], 0.3, "steel_d", name="head")
    b.oct("z", 8, top + 0.8, 1.0, 11.0, 12.6, "steel", name="face")
    b.oct("z", 8, top + 0.8, 1.1, 10.8, 11.1, "steel_d", name="neck")
    # 노루발 (두 갈래, 아래로 휨)
    for sx in (7.35, 8.15):
        b.chamfer_box([sx, top + 0.2, 3.0], [sx + 0.5, top + 1.8, 6.0], 0.15, "steel_d", Xf.rot("x", 22.5, (8, top + 1, 6)), name="claw")
    b.chamfer_box([7.4, top - 1.2, 7.6], [8.6, top - 0.5, 9.4], 0.1, "steel", name="wedge")


def small_hammer(b):
    hammer(b, 9.5, True)


def sledgehammer(b):
    rod(b, 0, 27, 0.85, "wood", name="handle")
    rod(b, 0, 5, 1.0, "rubber", name="grip")
    rings(b, 0.4, 4.6, 5, 1.05, "rubber_t", name="grip_wrap")
    rod(b, 23.4, 25.2, 1.0, "wood_d", name="neck")
    b.chamfer_box([6.6, 25.0, 3.4], [9.4, 29.8, 12.6], 0.55, "steel_d", name="head")
    for z0, z1 in ((2.4, 3.5), (12.5, 13.6)):
        b.chamfer_box([6.9, 25.3, z0], [9.1, 29.5, z1], 0.45, "steel", name="face")
    b.chamfer_box([7.2, 24.2, 6.6], [8.8, 25.1, 9.4], 0.15, "steel", name="wedge")
    b.put([6.58, 26.2, 5.0], [6.62, 28.6, 11.0], "steel_l", name="mark")


# ───────── 생활용품 ─────────
def pot(b):
    rod(b, 0, 9.6, 0.62, "black", name="handle")
    b.oct("x", 0.9, 8, 0.45, 7.3, 8.7, "steel", name="hang_ring")
    b.chamfer_box([7.4, 9.3, 7.4], [8.6, 11.2, 8.6], 0.15, "steel", name="bracket")
    b.oct("z", 8, 15.4, 5.0, 4.4, 11.0, "steel", name="body")
    b.oct("z", 8, 15.4, 5.4, 10.6, 11.3, "steel_l", name="rim")
    b.oct("z", 8, 15.4, 4.6, 11.25, 11.32, "pan_in", name="inside")
    b.oct("z", 8, 15.4, 4.6, 4.0, 4.5, "steel_d", name="bottom")
    b.chamfer_box([2.0, 14.6, 7.0], [3.0, 16.2, 9.0], 0.2, "black", name="side_handle")


def frying_pan(b):
    rod(b, 0, 11, 0.7, "black", name="handle")
    b.oct("z", 1.4, 8, 0.4, 7.25, 8.75, "bore", name="hang_hole")
    b.chamfer_box([7.5, 10.4, 7.6], [8.5, 12.4, 8.4], 0.12, "steel_d", name="bracket")
    for y in (11.0, 11.8):
        b.oct("z", y, 8.0, 0.16, 7.55, 8.45, "steel_l", name="rivet")
    b.oct("z", 8, 18.5, 6.2, 7.6, 8.6, "anod", name="base")
    b.oct("z", 8, 18.5, 5.4, 8.55, 8.65, "pan_in", name="surface")
    for k in range(8):   # 테두리 (안쪽 면 위로 솟은 고리)
        b.put([8 - 2.6, 18.5 + 5.4, 8.55], [8 + 2.6, 18.5 + 6.2, 9.3], "anod", Xf.rot("z", k * 45 + 22.5, (8, 18.5, 0)), name="rim")


def briefcase(b):
    b.chamfer_box([6.0, 0.0, 7.4], [10.0, 1.0, 8.6], 0.3, "leather_d", name="handle")
    for x in (6.0, 9.2):
        b.chamfer_box([x, 0.4, 7.45], [x + 0.8, 2.7, 8.55], 0.15, "leather_d", name="handle_post")
        b.chamfer_box([x - 0.1, 2.3, 7.3], [x + 0.9, 2.8, 8.7], 0.1, "brass", name="handle_mount")
    b.chamfer_box([1.5, 2.6, 6.4], [14.5, 14.6, 9.6], 0.5, "leather", name="body")
    b.put([1.45, 2.55, 7.9], [14.55, 14.65, 8.1], "leather_d", name="seam")
    for x in (1.3, 13.9):
        for y in (2.3, 13.8):
            b.chamfer_box([x, y, 6.2], [x + 0.8, y + 1.1, 9.8], 0.15, "brass", name="corner")
    for x in (4.0, 10.6):
        b.chamfer_box([x, 3.0, 6.2], [x + 1.4, 4.2, 6.45], 0.08, "brass", name="latch")
        b.put([x + 0.5, 3.4, 6.15], [x + 0.9, 3.8, 6.2], "bore", name="keyhole")


def pool_cue(b, short=False):
    rod(b, 0, 0.6, 0.85, "rubber", name="bumper")
    rod(b, 0.6, 4.6, 0.8, "wood_d", name="butt")
    rod(b, 4.6, 9.0, 0.8, "black", name="wrap")
    rings(b, 5.0, 8.6, 6, 0.82, "black_t", name="linen")
    for k in range(4):   # 상아 마름모 상감
        b.put([7.8, 2.0, 7.15], [8.2, 3.2, 7.2], "ivory", Xf.rot("y", k * 90, (8, 0, 8)), name="inlay")
    rod(b, 9, 9.6, 0.82, "ivory", name="joint")
    if short:
        rod(b, 9.6, 12.5, 0.6, "wood_l", name="shaft")
        b.chamfer_box([7.6, 12.4, 7.6], [8.3, 15.0, 8.3], 0.08, "wood_l", name="splinter")
        b.chamfer_box([8.0, 12.4, 7.75], [8.45, 13.8, 8.4], 0.08, "wood", name="splinter")
        b.chamfer_box([7.55, 12.4, 7.9], [7.95, 14.2, 8.45], 0.08, "wood_l", name="splinter")
        b.put([7.7, 12.45, 7.7], [8.3, 12.55, 8.3], "wood_d", name="break")
    else:
        taper(b, 9.6, 30.5, 0.55, 0.42, 3, "wood_l", name="shaft")
        rod(b, 30.5, 31.2, 0.45, "white", name="ferrule")
        rod(b, 31.2, 31.6, 0.42, "chalk", name="tip")


def fire_axe(b):
    """소방도끼: 손잡이 +Y (y 0~28), 날은 −z, 곡괭이 뿔은 +z, 두께 x (기존 팩과 같은 방향)"""
    rod(b, 0.0, 0.3, 1.0, "steel_d", name="cap")
    rod(b, 0.3, 0.8, 1.14, "rubber", name="swell")
    rod(b, 0.8, 7.6, 0.92, "rubber", name="grip")
    rings(b, 1.6, 7.0, 6, 1.0, "rubber_t", name="grip_rib")
    rod(b, 7.6, 7.95, 1.0, "rubber_t", name="grip_end")
    rod(b, 7.9, 25.0, 0.8, "glass", name="haft")
    rod(b, 20.1, 20.85, 0.92, "steel", name="collar")
    # 눈 (자루 끼우는 통) + 쐐기
    b.chamfer_box([7.1, 20.8, 6.9], [8.9, 25.2, 9.1], 0.25, "red", name="eye")
    b.chamfer_box([7.84, 25.0, 7.35], [8.16, 25.35, 8.65], 0.06, "steel", name="wedge")
    # 날 (−z): 가운데 판 + 위/아래로 벌어지는 판, 날 쪽은 연마면, 끝은 칼날선
    secs = ((Xf(), 21.7, 24.3), (Xf.rot("x", 14, (8, 24.3, 7.0)), 23.5, 24.7), (Xf.rot("x", -14, (8, 21.7, 7.0)), 21.3, 22.5))
    for xf, y0, y1 in secs:
        b.put([7.72, y0, 4.4], [8.28, y1, 7.2], "red", xf, name="cheek")
        b.put([7.8, y0, 3.1], [8.2, y1, 4.5], "ground", xf, name="bevel")
        b.put([7.88, y0, 2.7], [8.12, y1, 3.15], "edge", xf, name="edge")
    # 곡괭이 뿔 (+z, 11.25° 아래로) : 세 마디로 가늘어짐
    pk = Xf.rot("x", 11.25, (8, 23.0, 9.0))
    b.chamfer_box([7.55, 22.3, 8.8], [8.45, 23.7, 11.6], 0.2, "red", pk, name="pick")
    b.chamfer_box([7.65, 22.5, 11.5], [8.35, 23.5, 12.9], 0.15, "ground", pk, name="pick_tip")
    b.chamfer_box([7.75, 22.7, 12.8], [8.25, 23.3, 13.8], 0.1, "ground", pk, name="pick_point")
    b.put([7.05, 22.4, 7.4], [7.1, 23.6, 8.6], "white", name="label")


WEAPONS = {
    "fire_axe": fire_axe,
    "dagger": dagger, "bat": bat, "pipe": pipe, "golf_club": golf_club, "machete": machete, "pot": pot,
    "frying_pan": frying_pan, "crowbar": crowbar, "katana": katana, "baton": baton, "hammer": hammer,
    "briefcase": briefcase, "pool_cue": pool_cue, "pool_cue_short": lambda b: pool_cue(b, True),
    "cleaver": cleaver, "sledgehammer": sledgehammer,
}


def build(name, render_dir=None, stem=None):
    bbkit.DOT_MODE = "cell"
    bbkit.GRAD = False
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
