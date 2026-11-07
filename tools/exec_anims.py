#!/usr/bin/env python3
"""
처형 애니메이션 만들기 → plugin-src/src/main/resources/execution.json (플러그인 ExecutionAnims 가 읽음)
미리보기: python3 tools/exec_anims.py --preview → docs/images/executions.png, build-out/executions/<이름>.gif

처형자와 피처형자 모두 6부위 인형으로 그린다 (FallPose 와 같은 좌표: x=왼쪽, y=위, z=앞, 발 기준, 각도는 도).
 - 처형자: 누운 적의 머리 쪽을 본다. 기준점 = 적의 발에서 머리 쪽으로 anchor 블록 (가슴 0.85 = 올라탐)
 - 피처형자: 등으로 누운 자세 (fall.json back 의 마지막 프레임과 같음) + 머리·팔 움직임
 - 무기: 처형자 손(오른손)에 붙은 아이템. weapon = none / right / both(두 손). wrist = 손목 꺾기(팔 x축), twist = 무기 자체 회전
 - hits(왼클릭): ready(대기 1프레임) + strike(한 번 칠 때 프레임, impact = 머리에 닿는 프레임)
 - auto(자동): full(전체 프레임) + impacts(닿는 프레임들) + kill(죽는 프레임) + events(추가 피)
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import models_melee  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "plugin-src", "src", "main", "resources", "execution.json")
FALL = os.path.join(ROOT, "plugin-src", "src", "main", "resources", "fall.json")
JOINTS = ("head", "arm_r", "arm_l", "leg_r", "leg_l")

# ───────────────────────── 자세 ─────────────────────────


def pose(base=None, **kw):
    p = {"pitch": 0.0, "feet": [0.0, 0.0], "head": [0, 0, 0], "arm_r": [0, 0, 0], "arm_l": [0, 0, 0],
         "leg_r": [0, 0, 0], "leg_l": [0, 0, 0], "wrist": 0.0, "twist": 0.0}
    if base:
        p.update(json.loads(json.dumps(base)))
    p.update(json.loads(json.dumps(kw)))
    return p


# 올라탐: 가슴 위에 무릎을 꿇고 다리를 뒤로 벌림
STRADDLE = pose(pitch=8, feet=[-0.3, 0.0], head=[25, 0, 0], arm_r=[-30, 0, 0], arm_l=[-30, 0, 0], leg_r=[82, 0, -22], leg_l=[82, 0, 22])
STAND = pose()


def _lying():
    fall = json.load(open(FALL, encoding="utf-8"))
    last = fall["kinds"]["back"]["frames"][-1]
    return pose(pitch=last["pitch"], feet=list(last["feet"]))


LYING = _lying()


def lerp(a, b, t):
    if isinstance(a, list):
        return [lerp(x, y, t) for x, y in zip(a, b)]
    return a + (b - a) * t


def track(keys, length=None):
    """[(틱, 자세)] → 틱마다 프레임 (부드럽게 이어 붙임)"""
    keys = sorted(keys, key=lambda k: k[0])
    # 손목·무기 회전은 앞 키에서 가까운 쪽으로 돌림 (같은 각도를 360° 다르게 적어 무기가 한 바퀴 도는 일 없게)
    fixed = [keys[0]]
    for t, f in keys[1:]:
        f = pose(f)
        prev = fixed[-1][1]
        for key in ("wrist", "twist"):
            f[key] = prev[key] + ((f[key] - prev[key] + 180) % 360 - 180)
        fixed.append((t, f))
    keys = fixed
    length = length or keys[-1][0] + 1
    out = []
    for t in range(length):
        k0 = max([k for k in keys if k[0] <= t], key=lambda k: k[0], default=keys[0])
        k1 = min([k for k in keys if k[0] >= t], key=lambda k: k[0], default=keys[-1])
        if k1[0] == k0[0]:
            out.append(json.loads(json.dumps(k0[1])))
            continue
        u = (t - k0[0]) / (k1[0] - k0[0])
        u = u * u * (3 - 2 * u)
        f = {key: lerp(k0[1][key], k1[1][key], u) for key in k0[1]}
        out.append(f)
    return out


def rnd(frames):
    def r(v):
        return [r(x) for x in v] if isinstance(v, list) else round(float(v), 2)
    return [{k: r(v) for k, v in f.items()} for f in frames]


# ───────────────────────── 손·무기 위치 (FallPose / ExecutionAnims 와 같은 계산) ─────────────────────────

PX = 0.9375 / 16
JOINT = {"arm_r": (-5, 22, 0), "arm_l": (5, 22, 0)}
W_SCALE = 0.85 * 0.9375


def _rx(a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])


def _ry(a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])


def _rz(a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])


def _rxyz(a):
    return _rx(math.radians(a[0])) @ _ry(math.radians(a[1])) @ _rz(math.radians(a[2]))


def fist(fr, hand="arm_r"):
    body = _rx(math.radians(fr["pitch"]))
    side = -1 if hand == "arm_r" else 1
    local = np.array(JOINT[hand]) * PX + _rxyz(fr[hand]) @ np.array([side * PX, -10 * PX, 0])
    return body @ local + np.array([0, fr["feet"][0], fr["feet"][1]])


def weapon_point(fr, along_px):
    """오른손에 쥔 무기에서 손잡이(쥔 곳)로부터 along_px(모델 픽셀) 떨어진 점"""
    body = _rx(math.radians(fr["pitch"]))
    Rw = body @ _rxyz(fr["arm_r"]) @ _rx(math.pi) @ _rx(math.radians(fr["wrist"])) @ _ry(math.radians(fr["twist"]))
    return fist(fr) + Rw @ np.array([0, along_px / 16 * W_SCALE, 0])


# 피처형자 머리·목 (처형자 기준 좌표, 기준점 = 가슴 0.85): 누운 머리 중심 = 발에서 1.64, 목 = 1.41, 높이 = 몸 중심선 0.14
HEAD = np.array([0.0, 0.32, 1.64 - 0.85])
NECK = np.array([0.0, 0.27, 1.41 - 0.85])


def head_at(anchor):
    """기준점이 anchor 일 때 피처형자 머리 (처형자 기준 좌표)"""
    return np.array([0.0, 0.32, 1.64 - anchor])


def weapon_axes(fr):
    """오른손 무기의 방향(모델 +Y = 손잡이→끝), 앞면(모델 +Z = 치는 면·갈고리 쪽), 옆(모델 +X)"""
    R = _rx(math.radians(fr["pitch"])) @ _rxyz(fr["arm_r"]) @ _rx(math.pi) @ _rx(math.radians(fr["wrist"])) @ _ry(math.radians(fr["twist"]))
    return R[:, 1], R[:, 2], R[:, 0]


def _unit(v):
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v)


def solve(base, target, along_px=None, hands=("arm_r", "arm_l"), free=("x", "wrist"), inward=12, xr=(-190, -10),
          yr=(-45, 45), zr=(-50, 50), step=3.0, aim=None, face=None, side=None, k=0.5):
    """target 에 (오른손 무기의 along_px 지점, 없으면 hands[0] 주먹)이 닿도록 격자 탐색.
    free: 움직일 값 — x(팔 앞뒤), y(팔 비틀기: 무기를 머리 가운데로), z(팔 좌우), wrist(손목).
    aim: 무기가 향할 방향, face: 앞면(+Z)이 향할 방향, side: 옆면(±X, 날붙이의 날)이 향할 방향 — 벗어난 만큼 k 배로 벌점.
    두 손이면 왼팔은 오른팔과 좌우 대칭"""
    xs = np.arange(xr[0], xr[1] + 1, 2.0) if "x" in free else [base[hands[0]][0]]
    ys = np.arange(yr[0], yr[1] + 1, step) if "y" in free else [None]
    zs = np.arange(zr[0], zr[1] + 1, step) if "z" in free else [None]
    ws = np.arange(-180, 181, step) if "wrist" in free else [base["wrist"]]
    aim = None if aim is None else _unit(aim)
    face = None if face is None else _unit(face)
    side = None if side is None else _unit(side)
    best = None
    for ax in xs:
        for ay in ys:
            for az in zs:
                f = pose(base)
                for h in hands:
                    mirror = 1 if h == hands[0] else -1
                    y = ay * mirror if ay is not None else base[h][1]
                    z = az * mirror if az is not None else inward * (1 if h == "arm_r" else -1)
                    f[h] = [float(ax), float(y), float(z)]
                if along_px is None:
                    err = np.linalg.norm(fist(f, hands[0]) - target)
                    if best is None or err < best[0]:
                        best = (err, err, pose(f))
                    continue
                for wr in ws:
                    f["wrist"] = float(wr)
                    hit = np.linalg.norm(weapon_point(f, along_px) - target)
                    err = hit
                    if aim is not None or face is not None or side is not None:
                        d, z_, x_ = weapon_axes(f)
                        if aim is not None:
                            err += k * np.linalg.norm(d - aim)
                        if face is not None:
                            err += k * np.linalg.norm(z_ - face)
                        if side is not None:
                            err += k * (1 - abs(float(x_ @ side)))
                    if best is None or err < best[0]:
                        best = (err, hit, pose(f))
    if best[1] > 0.12:
        print(f"  [solve] 목표에서 {best[1]:.2f} 떨어짐 (목표 {np.round(target, 2)})")
    return best[2]


def swing_forward(ref, f):
    """손목 각을 ref 에서 앞으로(위→앞→아래) 돌아가는 값으로 맞춤: 무기가 등 뒤로 한 바퀴 돌지 않게"""
    f = pose(f)
    f["wrist"] = ref["wrist"] + (f["wrist"] - ref["wrist"]) % 360
    return f


# 내려친 순간 무기 방향: 앞아래로 비스듬히
DOWN_FWD = (0, -0.8, 0.6)

# 휘두르기 풀이: 팔 앞뒤 + 팔 비틀기(무기를 머리 가운데로) + 손목
SWING = ("x", "y", "wrist")

# 무기 묶음별 대표 길이 (쥔 곳 → 치는 부분, 모델 픽셀)
STRIKE_ALONG = {"blunt": 22.0, "heavy": 23.5, "light": 8.5, "blade": 8.0}


# ───────────────────────── 처형 동작 ─────────────────────────

def anims():
    A = {}
    # 1. 맨손: 올라타 머리를 잡고 들어 바닥에 박음 (왼클릭 5번)
    # 두 손이 머리 양옆을 잡음: 들어 올릴 때는 머리가 들린 높이, 박을 때는 바닥 높이
    hold = solve(pose(STRADDLE, pitch=26, head=[35, 0, 0]), HEAD + [-0.17, 0.12, -0.05], free=("x", "z"))
    lift = solve(pose(STRADDLE, pitch=14, head=[25, 0, 0]), HEAD + [-0.17, 0.42, -0.15], free=("x", "z"))
    slam = solve(pose(STRADDLE, pitch=36, head=[45, 0, 0]), HEAD + [-0.17, 0.02, 0.0], free=("x", "z"))
    v_hold = pose(LYING, head=[12, 0, 0], arm_r=[-20, 0, -10], arm_l=[-20, 0, 10])
    v_lift = pose(v_hold, head=[42, 0, 0])
    v_slam = pose(v_hold, head=[-6, 0, 0], arm_r=[-35, 0, -25], arm_l=[-35, 0, 25])
    A["fist"] = {"anchor": 0.85, "weapon": "none", "style": "hits",
                 "ready": {"exec": rnd([hold])[0], "victim": rnd([v_hold])[0]},
                 "strike": {"exec": rnd(track([(0, hold), (2, lift), (4, slam), (5, slam), (8, hold)])),
                            "victim": rnd(track([(0, v_hold), (2, v_lift), (4, v_slam), (5, v_slam), (8, v_hold)])),
                            "impact": 4}}
    # 1-1. 코브라·돼지·곰 가면 맨손: 머리 위로 한쪽 다리를 들고 힘껏 밟음 (자동)
    up = pose(STAND, pitch=-8, leg_r=[-100, 0, -4], arm_r=[-25, 0, -32], arm_l=[-30, 0, 34], head=[30, 0, 0])
    up2 = pose(up, pitch=-11, leg_r=[-108, 0, -4], arm_r=[-40, 0, -45], arm_l=[-45, 0, 45])
    stomp = pose(STAND, pitch=12, leg_r=[-46, 0, -2], leg_l=[8, 0, 2], arm_r=[10, 0, -20], arm_l=[15, 0, 22], head=[40, 0, 0])
    v_ok = pose(LYING, head=[8, 0, 0])
    v_hit = pose(LYING, pitch=-93, head=[-14, 0, 0], arm_r=[-40, 0, -30], arm_l=[-40, 0, 30], leg_r=[-10, 0, 0], leg_l=[-12, 0, 0])
    A["stomp"] = {"anchor": 1.0, "weapon": "none", "style": "auto",
                  "full": {"exec": rnd(track([(0, up), (6, up2), (11, up2), (14, stomp), (17, stomp), (26, STAND)])),
                           "victim": rnd(track([(0, v_ok), (13, v_ok), (14, v_hit), (17, v_hit), (22, LYING), (26, LYING)])),
                           "impacts": [14], "kill": 16, "events": []}}
    # 2. 둔기: 올라탄 채 무기를 높이 들고 머리를 내려침 (왼클릭 3번)
    raised = pose(STRADDLE, pitch=-4, head=[20, 0, 0], arm_r=[-172, 0, 14], arm_l=[-172, 0, -14], wrist=-25)
    wind = pose(raised, pitch=-10, arm_r=[-180, 0, 14], arm_l=[-180, 0, -14], wrist=-40)
    # 긴 무기는 머리에서 조금 떨어진 허벅지 위에 올라탐 (무기가 앞아래로 비스듬히 머리에 닿도록)
    LONG = 0.4
    hit = solve(pose(STRADDLE, pitch=8, head=[40, 0, 0]), head_at(LONG) + [0, 0.05, 0], STRIKE_ALONG["blunt"],
                free=SWING, xr=(-150, -60), aim=DOWN_FWD)
    hit = swing_forward(wind, hit)
    v_r = pose(LYING, head=[6, 0, 0])
    v_h = pose(LYING, head=[-12, 0, 0], arm_r=[-30, 0, -20], arm_l=[-30, 0, 20])
    blunt_strike = {"exec": rnd(track([(0, raised), (2, wind), (4, hit), (5, hit), (8, raised)])),
                    "victim": rnd(track([(0, v_r), (3, v_r), (4, v_h), (5, v_h), (8, v_r)])), "impact": 4}
    A["blunt"] = {"anchor": LONG, "weapon": "both", "style": "hits",
                  "ready": {"exec": rnd([raised])[0], "victim": rnd([v_r])[0]}, "strike": blunt_strike}
    # 3. 무거운 무기: 높이 들고 크게 한 번 내려쳐(자동) 박힌 무기를 뽑아 올림
    hraise = pose(raised, pitch=-8, wrist=-30)
    hwind = pose(raised, pitch=-14, arm_r=[-182, 0, 14], arm_l=[-182, 0, -14], wrist=-12, head=[10, 0, 0])
    hhit = solve(pose(STRADDLE, pitch=10, head=[40, 0, 0]), head_at(LONG) + [0, -0.04, 0], STRIKE_ALONG["heavy"],
                 free=SWING, xr=(-150, -60), aim=DOWN_FWD)
    hhit = swing_forward(hwind, hhit)
    tug1 = solve(pose(STRADDLE, pitch=4, head=[35, 0, 0]), head_at(LONG) + [0, -0.02, 0], STRIKE_ALONG["heavy"],
                 free=SWING, xr=(-150, -60), aim=(0, -0.9, 0.45))
    tug1 = swing_forward(hwind, tug1)
    tug2 = pose(hhit)
    pull = pose(STRADDLE, pitch=0, arm_r=[-120, 0, 14], arm_l=[-120, 0, -14], wrist=-60, head=[25, 0, 0])
    v_big = pose(LYING, pitch=-92, head=[-18, 0, 0], arm_r=[-45, 0, -35], arm_l=[-45, 0, 35], leg_r=[-14, 0, 0], leg_l=[-10, 0, 0])
    v_jerk = pose(LYING, head=[-10, 0, 0], arm_r=[-20, 0, -15], arm_l=[-20, 0, 15])
    A["heavy"] = {"anchor": LONG, "weapon": "both", "style": "auto",
                  "full": {"exec": rnd(track([(0, hraise), (5, hwind), (9, hwind), (11, hhit), (14, hhit), (16, tug1), (18, tug2),
                                              (20, tug1), (22, tug2), (24, tug1), (28, pull), (33, hraise)])),
                           "victim": rnd(track([(0, v_r), (10, v_r), (11, v_big), (14, v_big), (16, v_jerk), (18, v_big), (20, v_jerk),
                                                (22, v_big), (24, v_jerk), (28, LYING), (33, LYING)])),
                           "impacts": [11], "kill": 12, "events": [{"t": 16, "kind": "tug"}, {"t": 20, "kind": "tug"}, {"t": 24, "kind": "tug"},
                                                                  {"t": 27, "kind": "pull"}]}}
    # 4. 가벼운 무기: 둔기와 같지만 오른손으로만 (왼손은 가슴을 누름)
    lraised = pose(STRADDLE, pitch=0, head=[24, 0, 0], arm_r=[-165, 0, 4], arm_l=[-55, 0, -8], wrist=-20)
    lwind = pose(lraised, pitch=-6, arm_r=[-176, 0, 4], wrist=-35)
    # 팔을 안쪽으로 모아 머리 가운데를 침, 칼날(앞면)이 아래를 봄
    lhit = solve(pose(STRADDLE, pitch=10, head=[40, 0, 0], arm_l=[-48, 0, -8]), HEAD + [0, 0.06, 0], STRIKE_ALONG["light"],
                 hands=("arm_r",), free=("x", "z", "wrist"), xr=(-130, -10), zr=(-10, 40), aim=(0.4, -0.85, 0.4), k=0.6)
    lhit = swing_forward(lwind, lhit)
    A["light"] = {"anchor": 0.85, "weapon": "right", "style": "hits",
                  "ready": {"exec": rnd([lraised])[0], "victim": rnd([v_r])[0]},
                  "strike": {"exec": rnd(track([(0, lraised), (2, lwind), (4, lhit), (5, lhit), (8, lraised)])),
                             "victim": rnd(track([(0, v_r), (3, v_r), (4, v_h), (5, v_h), (8, v_r)])), "impact": 4}}
    # 5. 날붙이: 왼손으로 머리를 누르고 날을 목에 댄 채 시작해 목을 그음 (자동)
    # 왼손은 머리를 누르고, 오른손 칼날을 목 왼쪽에 댐 → 오른쪽으로 그음 (칼날을 눕혀 목을 가로지름)
    lhead = solve(pose(STRADDLE, pitch=26, head=[40, 0, 0]), HEAD + [0.05, 0.3, 0.05], hands=("arm_l",), free=("x", "z"))
    # 칼끝은 왼쪽(목을 가로질러), 날은 아래(목) — 오른쪽으로 당겨 그음
    blade_fit = dict(hands=("arm_r",), free=("x", "y", "z", "wrist"), xr=(-100, -20), yr=(-60, 60), zr=(-40, 40), step=6.0,
                     aim=(1, -0.15, 0), side=(0, -1, 0))
    at_throat = solve(pose(lhead, twist=90), NECK + [0.16, 0.06, 0], STRIKE_ALONG["blade"], **blade_fit)
    cut = solve(pose(lhead, twist=90), NECK + [-0.26, 0.06, 0], STRIKE_ALONG["blade"], **blade_fit)
    # 그은 뒤: 칼을 쥔 채 오른쪽 위로 빼 올림
    after = pose(cut, pitch=14, head=[30, 0, 0], arm_r=[cut["arm_r"][0] - 25, cut["arm_r"][1], cut["arm_r"][2] - 10],
                 arm_l=[-60, 0, -6], wrist=cut["wrist"] + 15)
    v_neck = pose(LYING, head=[-24, 0, 0], arm_r=[-10, 0, -10], arm_l=[-10, 0, 10])
    v_cut = pose(LYING, head=[-30, 0, 0], arm_r=[-50, 0, -30], arm_l=[-55, 0, 20], leg_r=[-12, 0, 0])
    v_twitch = pose(LYING, head=[-20, 0, 0], arm_r=[-30, 0, -15], arm_l=[-20, 0, 10])
    A["blade"] = {"anchor": 0.85, "weapon": "right", "style": "auto",
                  "full": {"exec": rnd(track([(0, at_throat), (8, at_throat), (11, cut), (14, cut), (20, after), (24, after)])),
                           "victim": rnd(track([(0, v_neck), (9, v_neck), (11, v_cut), (14, v_twitch), (17, v_cut), (20, v_twitch), (24, LYING)])),
                           "impacts": [10], "kill": 14, "events": [{"t": 10, "kind": "artery"}]}}
    return A


# 무기 묶음 (플러그인 ExecutionAnim 과 같아야 함 — 테스트가 확인)
GROUPS = {
    "blunt": ["pipe", "bat", "golf_club", "baton", "hammer", "briefcase", "crowbar"],
    "heavy": ["katana", "pool_cue", "sledgehammer", "fire_axe"],
    "light": ["pot", "frying_pan", "machete", "cleaver"],
    "blade": ["dagger", "pool_cue_short"],
}
STOMP_MASKS = ["JAKE", "PIG_BUTCHER", "MARK"]


def build():
    data = {"_comment": "처형 애니메이션 (tools/exec_anims.py 가 만듦 — 직접 고치지 말고 그 파일을 고친 뒤 다시 실행)",
            "groups": GROUPS, "stomp_masks": STOMP_MASKS,
            "grips": {k: list(v) for k, v in models_melee.GRIP.items()},
            "anims": anims()}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


# ───────────────────────── 미리보기 ─────────────────────────

def preview(data):
    from PIL import Image, ImageDraw, ImageFont
    import fall_preview as FPV
    import melee_kill_preview as MK
    import tp_sim as T
    PX = FPV.PX
    S = 260
    NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
    font = ImageFont.truetype(FPV.FONT, 15)
    samples = {"fist": None, "stomp": None, "blunt": "bat", "heavy": "sledgehammer", "light": "cleaver", "blade": "dagger"}
    labels = {"fist": "맨손: 머리 박기 ×5", "stomp": "코브라·돼지·곰: 밟기", "blunt": "둔기(몽둥이): 내려치기 ×3",
              "heavy": "무거운 무기(오함마): 내려치고 뽑기", "light": "가벼운 무기(중식도): 한 손 ×3", "blade": "날붙이(단검): 목 긋기"}

    def rot_xyz(a):
        return T.rx(math.radians(a[0])) @ T.ry(math.radians(a[1])) @ T.rz(math.radians(a[2]))

    def weapon_polys(fr, wid, hand):
        m = json.load(open(os.path.join(NS, "models", "item", "weapon", wid + ".json"), encoding="utf-8"))
        tex = Image.open(os.path.join(NS, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
        body = T.rx(math.radians(fr["pitch"]))
        joint, off = FPV.PARTS[hand]
        R = body @ rot_xyz(fr[hand])
        side = -1 if hand == "arm_r" else 1
        local = np.array(joint) * PX + (rot_xyz(fr[hand]) @ np.array([side * PX, -10 * PX, 0, 1.0]))[:3]
        fist = (body @ np.array([*local, 1.0]))[:3] + np.array([0, fr["feet"][0], fr["feet"][1]])
        Rw = R @ T.rx(math.pi) @ T.rx(math.radians(fr["wrist"])) @ T.ry(math.radians(fr["twist"]))
        s = 0.85 * 0.9375
        g = np.array(data["grips"][wid]) / 16 - 0.5
        M = T.tr(*(fist - (Rw[:3, :3] @ (g * s)))) @ Rw @ T.sc(s, s, s)
        return T.item_polys(M, m, tex, {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]})

    def scene(name, fr_e, fr_v):
        a = data["anims"][name]
        polys = []
        FPV.floor_polys(polys)
        # 피처형자: 발이 원점, 머리가 +Z (몸 방향 yaw 180)
        MK.set_fall_colors(MK.NPC_COL)
        vp = []
        FPV.puppet_polys(fr_v, vp)
        polys += MK.world_of(vp, np.array([0.0, 0, -0.9]), 180)
        # 처형자: 머리 쪽(+Z)을 봄
        MK.set_fall_colors(MK.ME_COL)
        ep = []
        FPV.puppet_polys(fr_e, ep)
        wid = samples[name]
        if wid:
            ep += weapon_polys(fr_e, wid, "arm_r")
        polys += MK.world_of(ep, np.array([0.0, 0, -0.9 + a["anchor"]]), 0)
        return polys

    def frames_of(name):
        a = data["anims"][name]
        if a["style"] == "hits":
            seq = [(a["ready"]["exec"], a["ready"]["victim"])] * 4
            for _ in range(2):
                seq += list(zip(a["strike"]["exec"], a["strike"]["victim"]))
            return seq, [4 + a["strike"]["impact"], 4 + len(a["strike"]["exec"]) + a["strike"]["impact"]]
        f = a["full"]
        return list(zip(f["exec"], f["victim"])), f["impacts"]

    cam_side, cam_q = (3.2, 1.3, 0.2), (2.4, 2.2, 2.2)
    rows = []
    gdir = os.path.join(ROOT, "build-out", "executions")
    os.makedirs(gdir, exist_ok=True)
    for name in samples:
        seq, impacts = frames_of(name)
        pick = sorted(set([0, impacts[0] - 2, impacts[0], min(len(seq) - 1, impacts[0] + 3), len(seq) - 1]))
        row = []
        for k in pick[:5]:
            fe, fv = seq[k]
            img = FPV.draw(scene(name, fe, fv), cam_side, S, (labels[name] if k == pick[0] else f"{k}틱" + (" (닿음)" if k in impacts else "")),
                           look=(0, 0.5, 0.0))
            row.append(img)
        rows.append(row)
        gif = []
        for fe, fv in seq:
            im = Image.new("RGB", (S * 2, S))
            im.paste(FPV.draw(scene(name, fe, fv), cam_q, S, "", look=(0, 0.5, 0.0)), (0, 0))
            im.paste(FPV.draw(scene(name, fe, fv), cam_side, S, "", look=(0, 0.5, 0.0)), (S, 0))
            ImageDraw.Draw(im).text((8, 6), labels[name], font=font, fill=(255, 220, 90))
            gif.append(im)
        gif[0].save(os.path.join(gdir, name + ".gif"), save_all=True, append_images=gif[1:], duration=50, loop=0)
    sheet = Image.new("RGB", (5 * S, len(rows) * S), (34, 30, 40))
    for j, r in enumerate(rows):
        for i, t in enumerate(r):
            sheet.paste(t, (i * S, j * S))
    out = os.path.join(ROOT, "docs", "images", "executions.png")
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    d = build()
    print(OUT, len(d["anims"]), "개")
    if "--preview" in sys.argv:
        preview(d)
