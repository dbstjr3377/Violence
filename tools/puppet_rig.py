#!/usr/bin/env python3
"""
인형 뼈대 (플러그인 FallPose 와 같은 계산): 머리·몸통 + 팔(위팔·아래팔) + 다리(허벅지·정강이) = 10부위.

좌표: 몸 기준 x=왼쪽, y=위, z=앞 (픽셀 = 0.9375/16 블록). 몸 전체는 발 기준으로 pitch 만큼 앞으로 기울고 feet 로 옮겨짐.
프레임 키: head/body/arm_r/arm_l/leg_r/leg_l = [x,y,z] 도 (XYZ 오일러), elbow_r/elbow_l/knee_r/knee_l = x축 굽힘 (도).
팔꿈치는 음수가 앞으로 굽힘, 무릎은 양수가 뒤로 굽힘.

ik_arm / ik_leg: 손(발)을 목표점에 닿게 하는 두 마디 IK (팔꿈치·무릎이 pole 쪽을 향함).
"""
import math

import numpy as np

PX = 0.9375 / 16
HAND_PX = 5.0   # 팔꿈치 → 주먹
FOOT_PX = 6.0   # 무릎 → 발바닥

# 이름: (부모, 관절(px, 서 있을 때), 관절→중심(px), 크기(px), 모델)
PARTS = {
    "head": (None, (0, 24, 0), (0, 4, 0), (8, 8, 8), "head"),
    "body": (None, (0, 12, 0), (0, 6, 0), (8, 12, 4), "body"),
    "arm_r": (None, (-5, 22, 0), (-1, -1, 0), (4, 6, 4), "arm_upper"),
    "arm_l": (None, (5, 22, 0), (1, -1, 0), (4, 6, 4), "arm_upper"),
    "elbow_r": ("arm_r", (-6, 18, 0), (0, -3, 0), (4, 6, 4), "forearm"),
    "elbow_l": ("arm_l", (6, 18, 0), (0, -3, 0), (4, 6, 4), "forearm"),
    "leg_r": (None, (-1.9, 12, 0), (0, -3, 0), (4, 6, 4), "leg_upper"),
    "leg_l": (None, (1.9, 12, 0), (0, -3, 0), (4, 6, 4), "leg_upper"),
    "knee_r": ("leg_r", (-1.9, 6, 0), (0, -3, 0), (4, 6, 4), "shin"),
    "knee_l": ("leg_l", (1.9, 6, 0), (0, -3, 0), (4, 6, 4), "shin"),
}


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler(a):
    """XYZ 오일러 (도) → 회전 (JOML rotationXYZ = Rx·Ry·Rz)"""
    return rx(math.radians(a[0])) @ ry(math.radians(a[1])) @ rz(math.radians(a[2]))


def to_euler(m):
    """회전 → XYZ 오일러 (도)"""
    y = math.asin(max(-1.0, min(1.0, m[0, 2])))
    if abs(m[0, 2]) < 0.9999:
        x = math.atan2(-m[1, 2], m[2, 2])
        z = math.atan2(-m[0, 1], m[0, 0])
    else:
        x = math.atan2(m[2, 1], m[1, 1])
        z = 0.0
    return [math.degrees(x), math.degrees(y), math.degrees(z)]


def joint_value(frame, key):
    v = frame.get(key, 0)
    if isinstance(v, (int, float)):
        return [float(v), 0.0, 0.0]
    return [float(x) for x in v]


def body_rot(frame):
    return rx(math.radians(frame["pitch"]))


def origin(frame):
    return np.array([0.0, frame["feet"][0], frame["feet"][1]])


def local_place(frame, name):
    """몸통 기준(기울이기 전): 중심(px), 회전"""
    parent, joint, off, _, _ = PARTS[name]
    if parent is None:
        r = euler(joint_value(frame, name))
        return r @ np.array(off, float) + np.array(joint, float), r
    pr = euler(joint_value(frame, parent))
    pj = np.array(PARTS[parent][1], float)
    j = pr @ (np.array(joint, float) - pj) + pj
    r = pr @ euler(joint_value(frame, name))
    return r @ np.array(off, float) + j, r


def place(frame, name):
    """몸 기준(블록): 중심, 회전 — FallPose.place 와 같음"""
    c, r = local_place(frame, name)
    b = body_rot(frame)
    return b @ (c * PX) + origin(frame), b @ r


def tip(frame, lower, down):
    c, r = place(frame, lower)
    off = PARTS[lower][2]
    return c + r @ np.array([0, (-down - off[1]) * PX, 0])


def hand(frame, side="r"):
    return tip(frame, "elbow_" + side, HAND_PX)


def foot(frame, side="r"):
    return tip(frame, "knee_" + side, FOOT_PX)


def to_local(frame, p):
    """몸 기준(블록) → 몸통 기준(기울이기 전, px)"""
    return body_rot(frame).T @ (np.asarray(p, float) - origin(frame)) / PX


def _align(a, b):
    """a 방향을 b 방향으로 돌리는 최소 회전"""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if c < -0.999999:
        axis = np.cross(a, [1.0, 0, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0, 1.0, 0])
        axis /= np.linalg.norm(axis)
        return axis_angle(axis, math.pi)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def axis_angle(axis, ang):
    axis = axis / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(ang) * k + (1 - math.cos(ang)) * (k @ k)


def _two_bone(frame, root, child, tip_px, target, pole, bend_sign):
    """root 관절에서 child 끝(tip_px)이 target(몸 기준 블록)에 닿게. pole = 가운데 관절이 향할 방향(몸 기준)"""
    pj = np.array(PARTS[root][1], float)
    a = np.array(PARTS[child][1], float) - pj           # 위 마디 (관절 → 가운데 관절)
    h = np.array([0, -tip_px, 0.0])                       # 아래 마디 (가운데 관절 → 끝)
    t = to_local(frame, target) - pj
    d = float(np.linalg.norm(t))
    # |a + Rx(b)h|² = |a|² + |h|² + 2 a·Rx(b)h, a·Rx(b)h = a_y·h_y·cos b + a_z·(...) → a_z = 0
    k = 2 * a[1] * h[1]
    cb = (d * d - a @ a - h @ h) / k if abs(k) > 1e-9 else 1.0
    b = bend_sign * math.acos(max(-1.0, min(1.0, cb)))
    v = a + rx(b) @ h
    r0 = _align(v, t if d > 1e-6 else np.array([0, -1.0, 0]))
    # 목표 방향을 축으로 돌려 가운데 관절을 pole 쪽으로
    tn = t / max(d, 1e-9)
    pl = body_rot(frame).T @ np.asarray(pole, float)
    e = r0 @ a
    ep = e - tn * (e @ tn)
    pp = pl - tn * (pl @ tn)
    if np.linalg.norm(ep) > 1e-6 and np.linalg.norm(pp) > 1e-6:
        ang = math.atan2(float(np.cross(ep, pp) @ tn), float(ep @ pp))
        r0 = axis_angle(tn, ang) @ r0
    frame[root] = [round(x, 3) for x in to_euler(r0)]
    frame[child] = round(math.degrees(b), 3)
    return d * PX


def ik_arm(frame, side, target, pole):
    """주먹을 target 에 (팔꿈치는 pole 쪽). 닿지 않으면 그쪽으로 뻗음"""
    return _two_bone(frame, "arm_" + side, "elbow_" + side, HAND_PX, target, pole, -1)


def ik_leg(frame, side, target, pole):
    """발바닥을 target 에 (무릎은 pole 쪽)"""
    return _two_bone(frame, "leg_" + side, "knee_" + side, FOOT_PX, target, pole, 1)


def reach_arm():
    a = np.array(PARTS["elbow_r"][1], float) - np.array(PARTS["arm_r"][1], float)
    return (np.linalg.norm(a) + HAND_PX) * PX
