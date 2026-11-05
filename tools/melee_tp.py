#!/usr/bin/env python3
"""
3인칭 근접 무기: 두 손 대기 자세와 휘두르기 키프레임 (build_pack 과 melee_tp_preview 가 함께 씀).

다른 사람에게 보이는 근접 무기는 "석궁 장전 중" 동작의 아이템으로 보낸다.
 - 팔: 바닐라 석궁 장전 자세 (양손을 몸 앞에 모음). 주 손을 왼손으로 바꾸면 좌우가 뒤집힘
 - 휘두르기: 바닐라 공격 동작(WHACK)이 주 팔과 몸통을 비틀고,
   아이템 모델은 "사용 시간"(use_duration, 틱)에 따라 키프레임을 바꿔 무기를 옆으로 크게 휘두른다.
   키프레임은 손 위치를 따라가며 손잡이가 손에서 떨어지지 않도록 손 기준 표시 변환을 역으로 계산한다.
 - 휘두르기 끝 자세 = 반대쪽 대기 자세 (주 손을 바꿔도 무기가 튀지 않음)
좌표: 개체가 +Z 를 봄. 개체의 오른쪽 = -X.
"""
import math

import numpy as np

import tp_sim as T

SWING_TICKS = 6          # 휘두르기 프레임 수 (20fps). 플러그인의 3인칭 휘두르기 길이와 같아야 함
CHARGE_TICKS = 5         # 빠른 장전 IV: 보조 팔이 자세를 잡는 시간
SCALE = 0.85
HOLD = np.array([0.0, -0.177, 0.094])   # 손 기준 손잡이 위치 (블록)

RT = np.array([-1.0, 0, 0])
UP = np.array([0, 1.0, 0])
FW = np.array([0, 0, 1.0])


def arm_pose(left_main, attack, charge=1.0):
    """(오른팔, 왼팔, 몸통 yRot, 오른팔/왼팔 피벗 x,z) — 바닐라 animateCrossbowCharge + setupAttackAnimation(WHACK)"""
    s = -1 if left_main else 1
    main = {"x": -0.97079635, "y": -0.8 * s, "z": 0.0}
    c = max(0.0, min(1.0, charge))
    off = {"x": -0.97079635 + (-math.pi / 2 + 0.97079635) * c, "y": (0.4 + 0.45 * c) * s, "z": 0.0}
    body_y = 0.0
    rpiv, lpiv = (-5.0, 0.0), (5.0, 0.0)
    if attack > 0:
        body_y = math.sin(math.sqrt(attack) * math.tau) * 0.2 * s
        rpiv = (-math.cos(body_y) * 5.0, math.sin(body_y) * 5.0)
        lpiv = (math.cos(body_y) * 5.0, -math.sin(body_y) * 5.0)
        right = off if left_main else main
        left = main if left_main else off
        right["y"] += body_y
        left["y"] += body_y
        left["x"] += body_y
        g = math.sin((1 - (1 - attack) ** 4) * math.pi)
        h = math.sin(attack * math.pi) * 0.7 * 0.75
        main["x"] -= g * 1.2 + h
        main["y"] += body_y * 2
        main["z"] += math.sin(attack * math.pi) * -0.4
    right = off if left_main else main
    left = main if left_main else off
    return right, left, body_y, rpiv, lpiv


def hand_matrix(left_main, attack, charge=1.0):
    """주 손 아이템 공간(표시 변환 적용 전) → 개체 공간"""
    right, left, body_y, rpiv, lpiv = arm_pose(left_main, attack, charge)
    root = T.entity_root(0)
    if left_main:
        arm = root @ T.part(lpiv[0], 2, lpiv[1], left["x"], left["y"], left["z"])
        return arm @ T.rx(math.radians(-90)) @ T.ry(math.radians(180)) @ T.tr(-1 / 16, 0.125, -0.625)
    arm = root @ T.part(rpiv[0], 2, rpiv[1], right["x"], right["y"], right["z"])
    return arm @ T.rx(math.radians(-90)) @ T.ry(math.radians(180)) @ T.tr(1 / 16, 0.125, -0.625)


def display_matrix(disp, mirror=False):
    """바닐라 ItemTransform.apply (왼손이면 x 이동, y·z 회전 부호 반전)"""
    r = [math.radians(v) for v in disp["rotation"]]
    t = [v / 16 for v in disp["translation"]]
    if mirror:
        r = [r[0], -r[1], -r[2]]
        t = [-t[0], t[1], t[2]]
    s = disp["scale"]
    return T.tr(*t) @ T.rx(r[0]) @ T.ry(r[1]) @ T.rz(r[2]) @ T.sc(*s) @ T.tr(-0.5, -0.5, -0.5)


def euler_xyz(A):
    """A = Rx(a)·Ry(b)·Rz(c) → (a, b, c) 도"""
    b = math.asin(max(-1.0, min(1.0, A[0, 2])))
    a = math.atan2(-A[1, 2], A[2, 2])
    c = math.atan2(-A[0, 1], A[0, 0])
    return [round(math.degrees(v), 2) for v in (a, b, c)]


def _n(v):
    return v / np.linalg.norm(v)


def frame(d, e):
    """모델 +Y(손잡이→끝) = d, 모델 +Z(날) ≈ e 인 회전 (열 = 모델 축의 개체 공간 방향)"""
    y = _n(d)
    z = _n(e - (e @ y) * y)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


def mirror_frame(R):
    M = np.diag([-1.0, 1, 1])
    return M @ R @ M


# 오른손 휘두르기 경로 (오→왼): 오른쪽 어깨 위 → 오른쪽 옆 → 정면 → 왼쪽 옆 → 왼쪽 어깨 위
REST = frame(0.45 * RT + 0.85 * UP - 0.3 * FW, FW)
KEYS = [
    (0.0, REST),
    (0.22, frame(0.95 * RT + 0.15 * UP + 0.3 * FW, FW - 0.4 * RT)),
    (0.45, frame(0.12 * RT - 0.08 * UP + FW, -RT)),
    (0.7, frame(-0.95 * RT + 0.05 * UP + 0.25 * FW, -FW)),
    (1.0, mirror_frame(REST)),
]


def _quat(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return np.array([w, x, y, z])


def _mat(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def _slerp(a, b, t):
    if a @ b < 0:
        b = -b
    d = min(1.0, a @ b)
    th = math.acos(d)
    if th < 1e-5:
        return a
    return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)


def path(p):
    """휘두르기 진행률 p(0~1) → 무기 방향 (개체 공간 회전)"""
    p = max(0.0, min(1.0, p))
    for (p0, r0), (p1, r1) in zip(KEYS, KEYS[1:]):
        if p <= p1:
            t = (p - p0) / (p1 - p0)
            t = t * t * (3 - 2 * t)
            return _mat(_slerp(_quat(r0), _quat(r1), t))
    return KEYS[-1][1]


def mirror_display(d):
    """바닐라 왼손 반전의 역: 이 값을 thirdperson_lefthand 에 쓰면 반전 후 d 가 된다"""
    r, t = d["rotation"], d["translation"]
    return {"rotation": [r[0], -r[1], -r[2]], "translation": [-t[0], t[1], t[2]], "scale": d["scale"]}


def solve(R_world, attack, grip, charge=1.0, left=False):
    """원하는 개체 공간 방향 → 손 기준 3인칭 표시 변환 (손잡이는 HOLD 에 고정).
    left 이면 왼손 주 손 자세에서 풀고 thirdperson_lefthand 에 넣을 값(반전 전)을 돌려준다.
    (바닐라 왼손 휘두르기는 팔 z 회전이 반전되지 않아 정확한 좌우 대칭이 아니므로 따로 푼다)"""
    H = hand_matrix(left, attack, charge)
    A = H[:3, :3].T @ R_world
    g = np.array(grip) / 16 - 0.5
    hold = np.array([-HOLD[0], HOLD[1], HOLD[2]]) if left else HOLD
    t = hold - A @ (SCALE * g)
    d = {"rotation": euler_xyz(A), "translation": [round(float(v) * 16, 3) for v in t], "scale": [SCALE] * 3}
    return mirror_display(d) if left else d


def _charge(k):
    return min(1.0, (k + 0.5) / CHARGE_TICKS)


def stance(grip):
    """대기 자세 표시 변환 {thirdperson_righthand, thirdperson_lefthand}"""
    return {"thirdperson_righthand": solve(REST, 0.0, grip),
            "thirdperson_lefthand": solve(mirror_frame(REST), 0.0, grip, left=True)}


def swing_frames(grip):
    """use_duration 0..SWING_TICKS-1 프레임 + 끝 자세 (반대쪽 대기와 같은 방향).
    각 항목 = {thirdperson_righthand: 오→왼, thirdperson_lefthand: 왼→오}"""
    out = []
    for k in range(SWING_TICKS):
        p = (k + 0.5) / SWING_TICKS
        R = path(p)
        out.append({"thirdperson_righthand": solve(R, p, grip, _charge(k)),
                    "thirdperson_lefthand": solve(mirror_frame(R), p, grip, _charge(k), left=True)})
    out.append({"thirdperson_righthand": solve(KEYS[-1][1], 0.0, grip),
                "thirdperson_lefthand": solve(mirror_frame(KEYS[-1][1]), 0.0, grip, left=True)})
    return out


def frame_states():
    """(진행률, 공격 시간, 장전 진행) — swing_frames 와 같은 순서"""
    out = [((k + 0.5) / SWING_TICKS, (k + 0.5) / SWING_TICKS, _charge(k)) for k in range(SWING_TICKS)]
    return out + [(1.0, 0.0, 1.0)]


def check(grip=(8, 3.5, 8)):
    """역계산 검증: 표시 변환을 다시 적용하면 원하는 방향·손잡이 위치가 나와야 함 (양손)"""
    errs = []
    for d, (p, att, ch) in zip(swing_frames(grip), frame_states()):
        for left in (False, True):
            want = path(p) if p < 1 else KEYS[-1][1]
            if left:
                want = mirror_frame(want)
            H = hand_matrix(left, att, ch)
            disp = d["thirdperson_lefthand" if left else "thirdperson_righthand"]
            M = H @ display_matrix(disp, mirror=left)
            errs.append(np.abs(M[:3, :3] / SCALE - want).max())
            hold = np.array([-HOLD[0], HOLD[1], HOLD[2]]) if left else HOLD
            gp = M @ np.array([*(np.array(grip) / 16), 1.0])
            errs.append(np.abs(gp[:3] - (H @ np.array([*hold, 1.0]))[:3]).max())
    return max(errs)


if __name__ == "__main__":
    print("max error", check())
    print("stance", stance((8, 3.5, 8)))
    for f in swing_frames((8, 3.5, 8)):
        print(f)
