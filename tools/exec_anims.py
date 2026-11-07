#!/usr/bin/env python3
"""
처형 애니메이션 만들기 → plugin-src/src/main/resources/execution.json (플러그인 ExecutionAnims 가 읽음)
미리보기: python3 tools/exec_anims.py --preview → docs/images/executions.png, build-out/executions/<이름>.gif

처형자와 피처형자 모두 10부위 인형(팔·다리가 두 마디: 팔꿈치·무릎)으로 그린다 (puppet_rig = FallPose 와 같은 좌표).
 - 처형자: 누운 적의 머리 쪽을 본다. 기준점 = 적의 발에서 머리 쪽으로 anchor 블록
 - 피처형자: 등으로 누운 자세 (fall.json back 의 마지막 프레임과 같음) + 머리·팔 움직임
 - 무기: 키프레임마다 무기 자체를 놓음 (쥐는 곳 위치 + 각도). 팔은 틱마다 두 마디 IK 로 손을 손잡이에 붙임
   (두 손 무기는 왼손이 오른손 아래 손잡이에). 무기는 위→앞→아래로 돌며 앞면(모델 +Z: 갈고리·도끼날·식칼 날)이 앞장섬.
 - 무릎을 꿇은 다리도 IK: 발끝은 바닥 뒤쪽, 무릎은 앞으로
 - 맨손: 두 손이 피처형자 머리 양옆을 따라감 (머리를 들었다 바닥에 박음)
 - 프레임 w = [x, y, z, qx, qy, qz, qw]: 오른손이 쥐는 곳(몸 기준, 블록)과 무기 회전 — 플러그인이 그대로 무기를 놓음
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
import puppet_rig as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "plugin-src", "src", "main", "resources", "execution.json")
FALL = os.path.join(ROOT, "plugin-src", "src", "main", "resources", "fall.json")

PX = R.PX
W_SCALE = 0.85 * 0.9375
# 두 손 무기: 왼손은 오른손보다 손잡이 끝 쪽으로 (블록)
LEFT_GAP = 3.4 / 16 * W_SCALE
# 무기 묶음별 대표 길이 (쥔 곳 → 치는 부분, 모델 픽셀)
STRIKE_ALONG = {"blunt": 22.0, "heavy": 23.5, "light": 8.5, "blade": 8.0}
# 팔꿈치가 향할 쪽 (몸 기준): 바깥·아래·조금 뒤
POLE_R, POLE_L = (-1.0, -0.6, -0.2), (1.0, -0.6, -0.2)

# ───────────────────────── 자세 ─────────────────────────


def pose(base=None, **kw):
    p = {"pitch": 0.0, "feet": [0.0, 0.0], "head": [0, 0, 0], "arm_r": [0, 0, 0], "arm_l": [0, 0, 0],
         "elbow_r": 0.0, "elbow_l": 0.0, "leg_r": [0, 0, 0], "leg_l": [0, 0, 0], "knee_r": 0.0, "knee_l": 0.0}
    if base:
        p.update(json.loads(json.dumps(base)))
    p.update(json.loads(json.dumps(kw)))
    return p


def _lying():
    fall = json.load(open(FALL, encoding="utf-8"))
    last = fall["kinds"]["back"]["frames"][-1]
    return pose(pitch=last["pitch"], feet=list(last["feet"]))


LYING = _lying()
HIP_PX = 12.0


def lerp(a, b, t):
    if isinstance(a, dict):
        return {k: lerp(a[k], b[k], t) if k in b else a[k] for k in a}
    if isinstance(a, list):
        return [lerp(x, y, t) for x, y in zip(a, b)]
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
        return a + (b - a) * t
    return a if t < 0.5 else b


def track(keys, length=None):
    """[(틱, 키)] → 틱마다 키 (부드럽게 이어 붙임). 키는 숫자·목록·사전 (같은 모양)"""
    keys = sorted(keys, key=lambda k: k[0])
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
        out.append(lerp(k0[1], k1[1], u))
    return out


def rnd(frames):
    def r(v):
        if isinstance(v, list):
            return [r(x) for x in v]
        return round(float(v), 4)
    return [{k: r(v) for k, v in f.items()} for f in frames]


# ───────────────────────── 무기 ─────────────────────────

def weapon_rot(a):
    """무기 각도 [θ, 좌우, 굴림] (도): θ=0 위, 90 앞, 180 아래 (Ry·Rx·Rz). 모델 +Y = 손잡이→끝, +Z = 앞면"""
    return R.ry(math.radians(a[1])) @ R.rx(math.radians(a[0])) @ R.rz(math.radians(a[2]))


def quat(m):
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1) * 2
        return [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]
    if m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        return [s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    if m[1, 1] > m[2, 2]:
        s = math.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        return [(m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    s = math.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
    return [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4, (m[1, 0] - m[0, 1]) / s]


def from_quat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def grip_for(tip, ang, along_px):
    """무기의 along_px 지점이 tip 에 닿는 쥐는 곳"""
    d = weapon_rot(ang) @ np.array([0, 1.0, 0])
    return list(np.asarray(tip, float) - d * (along_px / 16 * W_SCALE))


# ───────────────────────── 피처형자 / 처형자 좌표 ─────────────────────────

def victim_point(fv, anchor, part="head", up=0.0):
    """피처형자 부위 중심(+위로 up) → 처형자 기준 좌표 (피처형자는 발이 -anchor, 머리 쪽 = 처형자 앞)"""
    c, _ = R.place(fv, part)
    return np.array([-c[0], c[1] + up, -c[2] - anchor])


def head_top(anchor, fv=None):
    """누운 머리의 얼굴 쪽 표면 (치는 곳)"""
    return victim_point(fv or LYING, anchor, "head", 0.2)


def kneel(fr, pitch, hip_y=0.45, hip_z=0.0, spread=0.27, back=0.36):
    """무릎 꿇고 올라탐: 엉덩이를 (hip_y, hip_z) 에 두고 무릎은 바닥, 발끝은 뒤로"""
    h = HIP_PX * PX
    fr["pitch"] = pitch
    fr["feet"] = [hip_y - h * math.cos(math.radians(pitch)), hip_z - h * math.sin(math.radians(pitch))]
    for side, sx in (("r", -1), ("l", 1)):
        R.ik_leg(fr, side, [sx * spread, 0.12, hip_z - back], [sx * 0.35, -0.5, 1.0])
    return fr


def look_at(fr, target):
    """머리를 target 쪽으로 숙임/듦 (몸 기울기를 뺀 나머지)"""
    eye, _ = R.place(fr, "head")
    v = np.asarray(target, float) - eye
    total = math.degrees(math.atan2(-v[1], max(1e-6, v[2])))
    fr["head"] = [max(-40.0, min(70.0, total - fr["pitch"])), 0, 0]


def realize(k, vic, anchor):
    """키(보간된 값) → 출력 프레임: 다리 꿇기, 무기·손 IK, 머리 방향"""
    fr = pose(k["pose"])
    if "kneel" in k:
        kneel(fr, **k["kneel"])
    for side in ("r", "l"):
        if "foot_" + side in k:
            sx = -1 if side == "r" else 1
            R.ik_leg(fr, side, k["foot_" + side], k.get("knee_pole_" + side, [sx * 0.2, 0.3, 1.0]))
    if "w" in k:
        rot = weapon_rot(k["w"]["a"])
        g = np.asarray(k["w"]["p"], float)
        R.ik_arm(fr, "r", g, k.get("pole_r", POLE_R))
        if k.get("both"):
            R.ik_arm(fr, "l", g - rot @ np.array([0, LEFT_GAP, 0]), k.get("pole_l", POLE_L))
        fr["w"] = [*g, *quat(rot)]
    for side in ("r", "l"):
        tgt = k.get("hand_" + side)
        if tgt is None:
            continue
        if isinstance(tgt, str):   # 피처형자 머리 옆 등 (틱마다 따라감)
            part, dx, dy, dz = tgt.split(":")
            tgt = victim_point(vic, anchor, part, float(dy)) + [float(dx), 0, float(dz)]
        R.ik_arm(fr, side, tgt, k.get("pole_" + side, POLE_R if side == "r" else POLE_L))
    look_at(fr, victim_point(vic, anchor, "head", 0.1))
    return fr


def run(keys_e, keys_v, anchor):
    """처형자 키·피처형자 자세 → 틱마다 프레임"""
    vic = track(keys_v)
    ks = track(keys_e, len(vic))
    ex = [realize(k, v, anchor) for k, v in zip(ks, vic)]
    return rnd(ex), rnd(vic)


def K(pose_=None, **kw):
    """처형자 키: 몸 자세(pose) + kneel / w(무기: p 쥐는 곳, a 각도) / both / hand_r·hand_l / foot_r·foot_l"""
    d = {"pose": pose(pose_)}
    d.update(json.loads(json.dumps(kw, default=lambda o: [float(x) for x in o])))
    return d


# ───────────────────────── 처형 동작 ─────────────────────────

def anims():
    A = {}
    v_r = pose(LYING, head=[6, 0, 0])
    v_h = pose(LYING, head=[-12, 0, 0], arm_r=[-30, 0, -20], arm_l=[-30, 0, 20])

    # 1. 맨손: 올라타 두 손으로 머리 양옆을 잡고 들어 바닥에 박음 (왼클릭 5번)
    an = 0.85
    grab = {"hand_r": "head:-0.24:0.02:0.0", "hand_l": "head:0.24:0.02:0.0", "pole_r": [-1, 0.2, -0.6], "pole_l": [1, 0.2, -0.6]}
    hold = K(kneel={"pitch": 30}, **grab)
    lift = K(kneel={"pitch": 18, "hip_y": 0.5}, **grab)
    slam = K(kneel={"pitch": 42, "hip_y": 0.42}, **grab)
    v_hold = pose(LYING, head=[12, 0, 0], arm_r=[-20, 0, -10], arm_l=[-20, 0, 10])
    v_lift = pose(v_hold, head=[48, 0, 0])
    v_slam = pose(v_hold, head=[-8, 0, 0], arm_r=[-35, 0, -25], arm_l=[-35, 0, 25])
    ready_e, ready_v = run([(0, hold)], [(0, v_hold)], an)
    se, sv = run([(0, hold), (2, lift), (4, slam), (5, slam), (8, hold)],
                 [(0, v_hold), (2, v_lift), (4, v_slam), (5, v_slam), (8, v_hold)], an)
    A["fist"] = {"anchor": an, "weapon": "none", "style": "hits",
                 "ready": {"exec": ready_e[0], "victim": ready_v[0]}, "strike": {"exec": se, "victim": sv, "impact": 4}}

    # 1-1. 코브라·돼지·곰 가면 맨손: 서서 한쪽 다리를 머리 위로 높이 들고(무릎 굽힘) 힘껏 밟음 (자동)
    an = 1.1
    top = head_top(an)
    # 피처형자 가슴을 가랑이 사이에 두고 넓게 서서, 오른발을 머리 바로 위로 들었다가 내리찍음
    arms_up = {"arm_r": [-30, 0, -40], "arm_l": [-35, 0, 40], "elbow_r": -50, "elbow_l": -50}
    stand_l = {"foot_l": [0.32, 0.03, -0.04], "knee_pole_l": [0.3, 0.1, 1.0]}
    hover = top + [0, 0.42, 0.02]
    up = K(pose(pitch=-6, feet=[-0.03, 0.0], **arms_up), foot_r=list(hover), knee_pole_r=[-0.2, 0.8, 1.0], **stand_l)
    up2 = K(pose(pitch=-10, feet=[-0.03, 0.0], **{**arms_up, "arm_r": [-45, 0, -55], "arm_l": [-50, 0, 55]}),
            foot_r=list(hover + [0, 0.08, -0.02]), knee_pole_r=[-0.2, 0.9, 1.0], **stand_l)
    stomp = K(pose(pitch=12, feet=[-0.1, 0.0], arm_r=[15, 0, -25], arm_l=[20, 0, 25], elbow_r=-20, elbow_l=-20),
              foot_r=list(top + [0, 0.02, -0.03]), knee_pole_r=[-0.2, 0.4, 1.0], foot_l=[0.32, 0.04, -0.06], knee_pole_l=[0.3, 0.1, 1.0])
    stand = K(pose(), foot_r=[-0.3, 0.0, 0.0], foot_l=[0.3, 0.0, 0.0], knee_pole_r=[0, 0, 1.0], knee_pole_l=[0, 0, 1.0])
    v_ok = pose(LYING, head=[8, 0, 0])
    v_hit = pose(LYING, pitch=-93, head=[-14, 0, 0], arm_r=[-40, 0, -30], arm_l=[-40, 0, 30], leg_r=[-10, 0, 0], leg_l=[-12, 0, 0])
    fe, fv = run([(0, up), (6, up2), (11, up2), (14, stomp), (17, stomp), (26, stand)],
                 [(0, v_ok), (13, v_ok), (14, v_hit), (17, v_hit), (22, LYING), (26, LYING)], an)
    A["stomp"] = {"anchor": an, "weapon": "none", "style": "auto",
                  "full": {"exec": fe, "victim": fv, "impacts": [14], "kill": 16, "events": []}}

    # 2. 둔기: 무릎 꿇고 올라타 두 손으로 무기를 머리 위로 높이 들고 → 위·앞으로 돌려 내려침 (왼클릭 3번)
    # 긴 무기는 피처형자 무릎 위에 올라타 앞아래로 비스듬히 머리에 닿음
    an = 0.25
    L = STRIKE_ALONG["blunt"]
    two = {"both": True}
    raised = K(kneel={"pitch": -6}, w={"p": [-0.08, 1.5, -0.02], "a": [-35, 0, 0]}, **two)
    wind = K(kneel={"pitch": -12}, w={"p": [-0.08, 1.46, -0.14], "a": [-60, 0, 0]}, **two)
    over = K(kneel={"pitch": 4}, w={"p": [-0.1, 1.48, 0.3], "a": [35, 0, 0]}, **two)
    hit_a = [124, 0, 0]
    hit = K(kneel={"pitch": 18}, w={"p": grip_for(head_top(an), hit_a, L), "a": hit_a}, **two)
    strike_e, strike_v = run([(0, raised), (2, wind), (3, over), (4, hit), (5, hit), (8, raised)],
                             [(0, v_r), (3, v_r), (4, v_h), (5, v_h), (8, v_r)], an)
    ready_e, ready_v = run([(0, raised)], [(0, v_r)], an)
    A["blunt"] = {"anchor": an, "weapon": "both", "style": "hits", "lgap": LEFT_GAP,
                  "ready": {"exec": ready_e[0], "victim": ready_v[0]},
                  "strike": {"exec": strike_e, "victim": strike_v, "impact": 4}}

    # 3. 무거운 무기: 높이 들었다 크게 한 번 내려쳐(자동), 박힌 무기를 흔들어(끝은 머리에 박힌 채) 뽑아 올림
    L = STRIKE_ALONG["heavy"]
    tip = head_top(an) + [0, -0.06, 0]
    hraise = K(kneel={"pitch": -6}, w={"p": [-0.08, 1.5, -0.04], "a": [-38, 0, 0]}, **two)
    hwind = K(kneel={"pitch": -16, "hip_y": 0.5}, w={"p": [-0.08, 1.5, -0.2], "a": [-75, 0, 0]}, **two)
    hstart = K(kneel={"pitch": -8, "hip_y": 0.48}, w={"p": [-0.08, 1.52, -0.08], "a": [-20, 0, 0]}, **two)
    hover = K(kneel={"pitch": 8}, w={"p": [-0.1, 1.48, 0.32], "a": [52, 0, 0]}, **two)

    def stuck(a, pitch):
        return K(kneel={"pitch": pitch}, w={"p": grip_for(tip, [a, 0, 0], L), "a": [a, 0, 0]}, **two)
    hhit, tug_a, tug_b = stuck(122, 22), stuck(112, 12), stuck(128, 24)
    pull = K(kneel={"pitch": 0, "hip_y": 0.5}, w={"p": [-0.06, 1.2, 0.32], "a": [70, 0, 0]}, **two)
    v_big = pose(LYING, pitch=-92, head=[-18, 0, 0], arm_r=[-45, 0, -35], arm_l=[-45, 0, 35], leg_r=[-14, 0, 0], leg_l=[-10, 0, 0])
    v_jerk = pose(LYING, head=[-10, 0, 0], arm_r=[-20, 0, -15], arm_l=[-20, 0, 15])
    fe, fv = run([(0, hraise), (5, hwind), (8, hwind), (9, hstart), (10, hover), (11, hhit), (14, hhit), (16, tug_a), (18, tug_b),
                  (20, tug_a), (22, tug_b), (24, tug_a), (28, pull), (33, hraise)],
                 [(0, v_r), (10, v_r), (11, v_big), (14, v_big), (16, v_jerk), (18, v_big), (20, v_jerk),
                  (22, v_big), (24, v_jerk), (28, LYING), (33, LYING)], an)
    A["heavy"] = {"anchor": an, "weapon": "both", "style": "auto", "lgap": LEFT_GAP,
                  "full": {"exec": fe, "victim": fv, "impacts": [11], "kill": 12,
                           "events": [{"t": 16, "kind": "tug"}, {"t": 20, "kind": "tug"}, {"t": 24, "kind": "tug"}, {"t": 27, "kind": "pull"}]}}

    # 4. 가벼운 무기: 올라타 왼손으로 가슴을 누르고 오른손으로만 내려침 (왼클릭 3번)
    an = 0.85
    L = STRIKE_ALONG["light"]
    chest = {"hand_l": "body:0.08:0.14:-0.05", "pole_l": [1, 0.3, -0.4]}
    lraised = K(kneel={"pitch": 8}, w={"p": [-0.2, 1.3, 0.02], "a": [-40, 0, 0]}, **chest)
    lwind = K(kneel={"pitch": 2}, w={"p": [-0.22, 1.32, -0.08], "a": [-55, 0, 0]}, **chest)
    lover = K(kneel={"pitch": 16}, w={"p": [-0.14, 1.2, 0.28], "a": [30, 0, 0]}, **chest)
    la = [118, 0, 0]
    lhit = K(kneel={"pitch": 30}, w={"p": grip_for(head_top(an), la, L), "a": la}, **chest)
    se, sv = run([(0, lraised), (2, lwind), (3, lover), (4, lhit), (5, lhit), (8, lraised)],
                 [(0, v_r), (3, v_r), (4, v_h), (5, v_h), (8, v_r)], an)
    ready_e, ready_v = run([(0, lraised)], [(0, v_r)], an)
    A["light"] = {"anchor": an, "weapon": "right", "style": "hits",
                  "ready": {"exec": ready_e[0], "victim": ready_v[0]}, "strike": {"exec": se, "victim": sv, "impact": 4}}

    # 5. 날붙이: 왼손으로 이마를 누르고, 칼끝을 왼쪽으로 눕혀 날(옆면)을 목에 댄 채 → 오른쪽으로 당겨 그음 (자동)
    L = STRIKE_ALONG["blade"]
    neck = victim_point(LYING, an, "head", 0.0) + [0, 0.02, -0.24]
    # 칼끝은 왼쪽 앞(목을 비스듬히 가로질러), 날 아래 — 오른손이 너무 멀리 뻗지 않게
    knife, knife2 = [0, -40, -90], [0, -25, -90]
    kl = L / 16 * W_SCALE

    def knife_grip(tip_x, a):
        d = weapon_rot(a) @ np.array([0, 1.0, 0])
        return list(neck + [tip_x, 0.1, 0] - d * kl)
    press = {"hand_l": "head:0.02:0.24:0.06", "pole_l": [1, 0.4, -0.3], "pole_r": [-1, -0.3, -0.5]}
    at = K(kneel={"pitch": 58, "hip_y": 0.38, "hip_z": 0.14}, w={"p": knife_grip(0.14, knife), "a": knife}, **press)
    cut = K(kneel={"pitch": 60, "hip_y": 0.38, "hip_z": 0.14}, w={"p": knife_grip(-0.16, knife2), "a": knife2}, **press)
    after = K(kneel={"pitch": 16}, w={"p": [-0.26, 0.98, 0.3], "a": [-30, -20, -90]}, hand_l="head:0.02:0.3:0.1", pole_l=[1, 0.4, -0.3])
    v_neck = pose(LYING, head=[-24, 0, 0], arm_r=[-10, 0, -10], arm_l=[-10, 0, 10])
    v_cut = pose(LYING, head=[-30, 0, 0], arm_r=[-50, 0, -30], arm_l=[-55, 0, 20], leg_r=[-12, 0, 0])
    v_twitch = pose(LYING, head=[-20, 0, 0], arm_r=[-30, 0, -15], arm_l=[-20, 0, 10])
    fe, fv = run([(0, at), (8, at), (11, cut), (14, cut), (20, after), (24, after)],
                 [(0, v_neck), (9, v_neck), (11, v_cut), (14, v_twitch), (17, v_cut), (20, v_twitch), (24, LYING)], an)
    A["blade"] = {"anchor": an, "weapon": "right", "style": "auto",
                  "full": {"exec": fe, "victim": fv, "impacts": [10], "kill": 14, "events": [{"t": 10, "kind": "artery"}]}}
    return A


def check(A):
    """손이 무기에 붙어 있는지 출력"""
    for name, a in A.items():
        frames = []
        if "ready" in a:
            frames.append(a["ready"]["exec"])
        for part in ("strike", "full"):
            if part in a:
                frames += a[part]["exec"]
        worst = 0.0
        for f in frames:
            if "w" not in f:
                continue
            g = np.array(f["w"][:3])
            worst = max(worst, float(np.linalg.norm(R.hand(f, "r") - g)))
            if a["weapon"] == "both":
                d = from_quat(f["w"][3:]) @ np.array([0, 1.0, 0])
                worst = max(worst, float(np.linalg.norm(R.hand(f, "l") - (g - d * LEFT_GAP))))
        if a["weapon"] != "none":
            print(f"  {name}: 손과 손잡이 최대 거리 {worst:.3f} 블록")


# 무기 묶음 (플러그인 ExecutionAnim 과 같아야 함 — 테스트가 확인)
GROUPS = {
    "blunt": ["pipe", "bat", "golf_club", "baton", "hammer", "briefcase", "crowbar"],
    "heavy": ["katana", "pool_cue", "sledgehammer", "fire_axe"],
    "light": ["pot", "frying_pan", "machete", "cleaver"],
    "blade": ["dagger", "pool_cue_short"],
}
STOMP_MASKS = ["JAKE", "PIG_BUTCHER", "MARK"]


def build():
    A = anims()
    check(A)
    data = {"_comment": "처형 애니메이션 (tools/exec_anims.py 가 만듦 — 직접 고치지 말고 그 파일을 고친 뒤 다시 실행)",
            "groups": GROUPS, "stomp_masks": STOMP_MASKS,
            "grips": {k: list(v) for k, v in models_melee.GRIP.items()},
            "anims": A}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


# ───────────────────────── 미리보기 ─────────────────────────

def weapon_polys(fr, wid, grips):
    """frame["w"] 그대로 무기를 놓음 (ExecutionAnims.weapon 과 같음)"""
    from PIL import Image
    import tp_sim as T
    NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
    m = json.load(open(os.path.join(NS, "models", "item", "weapon", wid + ".json"), encoding="utf-8"))
    tex = Image.open(os.path.join(NS, "textures", m["textures"]["t"].split(":")[1] + ".png")).convert("RGBA")
    rot = from_quat(fr["w"][3:])
    g = np.array(grips[wid]) / 16 - 0.5
    M = np.eye(4)
    M[:3, :3] = rot
    M = T.tr(*(np.array(fr["w"][:3]) - rot @ (g * W_SCALE))) @ M @ T.sc(W_SCALE, W_SCALE, W_SCALE)
    return T.item_polys(M, m, tex, {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]})


def preview(data):
    from PIL import Image, ImageDraw, ImageFont
    import fall_preview as FPV
    import melee_kill_preview as MK
    S = 300
    font = ImageFont.truetype(FPV.FONT, 15)
    samples = {"fist": None, "stomp": None, "blunt": "crowbar", "heavy": "sledgehammer", "light": "cleaver", "blade": "dagger"}
    labels = {"fist": "맨손: 머리 박기 ×5", "stomp": "코브라·돼지·곰: 밟기", "blunt": "둔기(크로우바): 내려치기 ×3",
              "heavy": "무거운 무기(오함마): 내려치고 뽑기", "light": "가벼운 무기(중식도): 한 손 ×3", "blade": "날붙이(단검): 목 긋기"}

    def scene(name, fr_e, fr_v):
        a = data["anims"][name]
        polys = []
        FPV.floor_polys(polys)
        MK.set_fall_colors(MK.NPC_COL)
        vp = []
        FPV.puppet_polys(fr_v, vp)
        polys += MK.world_of(vp, np.array([0.0, 0, -0.9]), 180)
        MK.set_fall_colors(MK.ME_COL)
        ep = []
        FPV.puppet_polys(fr_e, ep)
        if samples[name] and "w" in fr_e:
            ep += weapon_polys(fr_e, samples[name], data["grips"])
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

    cam_side, cam_q = (3.3, 1.4, 0.1), (2.4, 2.3, 2.3)
    rows = []
    gdir = os.path.join(ROOT, "build-out", "executions")
    os.makedirs(gdir, exist_ok=True)
    for name in samples:
        seq, impacts = frames_of(name)
        pick = sorted(set([0, impacts[0] - 2, impacts[0] - 1, impacts[0], min(len(seq) - 1, impacts[0] + 3), len(seq) - 1]))
        if len(pick) > 5:
            pick = [pick[0], pick[1], pick[2], pick[3], pick[-1]]
        row = []
        for k in pick:
            fe, fv = seq[k]
            img = FPV.draw(scene(name, fe, fv), cam_side, S, (labels[name] if k == pick[0] else f"{k}틱" + (" (닿음)" if k in impacts else "")),
                           look=(0, 0.55, 0.0))
            row.append(img)
        rows.append(row)
        gif = []
        for fe, fv in seq:
            im = Image.new("RGB", (S * 2, S))
            im.paste(FPV.draw(scene(name, fe, fv), cam_q, S, "", look=(0, 0.5, 0.0)), (0, 0))
            im.paste(FPV.draw(scene(name, fe, fv), cam_side, S, "", look=(0, 0.55, 0.0)), (S, 0))
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
