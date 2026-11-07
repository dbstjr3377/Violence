#!/usr/bin/env python3
"""
3인칭 근접 무기: 두 손 대기 자세와 휘두르기 키프레임 (build_pack, melee_tp_preview, melee_kill_preview 가 함께 씀).

팔 (바닐라로 만들 수 있는 것만 씀)
 - 보는 사람에게 주 손을 "왼손"으로 보내고, 무기는 왼손에 "석궁 장전 중" 동작의 아이템으로 든다.
   바닐라 석궁 장전 자세는 보조 팔(오른팔)이 주 팔(왼팔)보다 높아서, 두 손이 손잡이 위아래로 겹친다 → 오른손이 위.
 - 휘두를 때는 보조 손(오른팔) 휘두르기를 보낸다. 바닐라 공격 동작(WHACK)이 오른팔을 오른쪽 위로 들었다가
   가운데로 내리고 몸통을 비튼다. 휘두르는 방향과 상관없이 늘 오른손이 위, 오른팔이 휘두름.
무기 (아이템 모델 키프레임)
 - 대기: 두 손 사이(손잡이 가운데)를 잡고, 다음 공격 방향 쪽 어깨로 살짝 기울임 (오른쪽 대기 / 왼쪽 대기)
 - 휘두르기: 사용 시간(틱)에 따라 6프레임. 손잡이 윗부분이 휘두르는 오른손을 따라가고,
   무기는 뒤로 젖혔다가(예비 동작) 옆으로 크게 돌아 반대쪽으로 넘어간다(따라가기). 날은 움직이는 방향을 향함.
 - 휘두르기 끝 자세 = 반대쪽 대기 자세 (대기 아이템으로 바꿔도 무기가 튀지 않음)
좌표: 개체가 +Z 를 봄. 개체의 오른쪽 = -X.
"""
import math

import numpy as np

import tp_sim as T

SWING_TICKS = 6          # 휘두르기 프레임 수 (20fps). 플러그인의 3인칭 휘두르기 길이와 같아야 함
CHARGE_TICKS = 5         # 빠른 장전 IV: 보조 팔이 자세를 잡는 시간 (휘두를 때마다 사용을 다시 시작하므로 다시 잡음)
SCALE = 0.85
GRIP_SPAN = 6.0          # 두 손 사이 손잡이 길이 (모델 픽셀) — 대기 자세의 두 손 거리와 같게

RT = np.array([-1.0, 0, 0])
UP = np.array([0, 1.0, 0])
FW = np.array([0, 0, 1.0])


def arm_pose(left_main, attack, charge=1.0, attack_off=False):
    """(오른팔, 왼팔, 몸통 yRot, 오른팔/왼팔 피벗 x,z)
    바닐라 animateCrossbowCharge + setupAttackAnimation(WHACK). attack_off 이면 보조 손 휘두르기."""
    s = -1 if left_main else 1
    main = {"x": -0.97079635, "y": -0.8 * s, "z": 0.0}
    c = max(0.0, min(1.0, charge))
    off = {"x": -0.97079635 + (-math.pi / 2 + 0.97079635) * c, "y": (0.4 + 0.45 * c) * s, "z": 0.0}
    right = off if left_main else main
    left = main if left_main else off
    body_y = 0.0
    rpiv, lpiv = (-5.0, 0.0), (5.0, 0.0)
    if attack > 0:
        attack_right = (not left_main) != attack_off
        body_y = math.sin(math.sqrt(attack) * math.tau) * 0.2 * (1 if attack_right else -1)
        rpiv = (-math.cos(body_y) * 5.0, math.sin(body_y) * 5.0)
        lpiv = (math.cos(body_y) * 5.0, -math.sin(body_y) * 5.0)
        right["y"] += body_y
        left["y"] += body_y
        left["x"] += body_y
        part = right if attack_right else left
        g = math.sin((1 - (1 - attack) ** 4) * math.pi)
        h = math.sin(attack * math.pi) * 0.7 * 0.75
        part["x"] -= g * 1.2 + h
        part["y"] += body_y * 2
        part["z"] += math.sin(attack * math.pi) * -0.4
    return right, left, body_y, rpiv, lpiv


def arm_matrices(left_main, attack, charge=1.0, attack_off=False):
    right, left, body_y, rpiv, lpiv = arm_pose(left_main, attack, charge, attack_off)
    root = T.entity_root(0)
    ra = root @ T.part(rpiv[0], 2, rpiv[1], right["x"], right["y"], right["z"])
    la = root @ T.part(lpiv[0], 2, lpiv[1], left["x"], left["y"], left["z"])
    return ra, la, body_y


def hand_matrix(left_main, attack, charge=1.0, attack_off=False):
    """주 손 아이템 공간(표시 변환 적용 전) → 개체 공간 (바닐라 ItemInHandLayer)"""
    ra, la, _ = arm_matrices(left_main, attack, charge, attack_off)
    if left_main:
        return la @ T.rx(math.radians(-90)) @ T.ry(math.radians(180)) @ T.tr(-1 / 16, 0.125, -0.625)
    return ra @ T.rx(math.radians(-90)) @ T.ry(math.radians(180)) @ T.tr(1 / 16, 0.125, -0.625)


def hands(attack, charge=1.0):
    """(오른손, 왼손) 주먹 중심 — 왼손 주 손, 오른손(보조) 휘두르기"""
    ra, la, _ = arm_matrices(True, attack, charge, attack_off=True)
    r = (ra @ np.array([-1 / 16, 9 / 16, 0, 1]))[:3]
    l_ = (la @ np.array([1 / 16, 9 / 16, 0, 1]))[:3]
    return r, l_


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
    y = _n(np.asarray(d, dtype=float))
    e = np.asarray(e, dtype=float)
    z = _n(e - (e @ y) * y)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


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


# 대기: 두 손(오른손 위)이 세로로 겹친 손잡이를 잡고, 다음 공격 쪽 어깨로 기울임. 날은 앞.
STANCE_R = frame(0.38 * RT + 0.9 * UP - 0.22 * FW, FW)     # 오른쪽 대기 → 다음은 오른쪽에서 왼쪽으로
STANCE_L = frame(-0.38 * RT + 0.9 * UP - 0.22 * FW, FW)    # 왼쪽 대기 → 다음은 왼쪽에서 오른쪽으로


def _swing_keys(side):
    """side=+1: 오른쪽→왼쪽, -1: 왼쪽→오른쪽. (진행률, 방향, 손잡이를 오른손에 붙이는 정도)"""
    s = side
    start, end = (STANCE_R, STANCE_L) if s > 0 else (STANCE_L, STANCE_R)
    sweep = -s * RT   # 무기가 지나가는 방향 (날이 이쪽을 향함)
    return [
        (0.0, start, 0.0),
        (0.12, frame(0.55 * s * RT + 0.65 * UP - 0.6 * FW, FW + 0.3 * s * RT), 0.85),   # 예비 동작: 어깨 뒤로 젖힘
        (0.3, frame(0.95 * s * RT + 0.2 * UP + 0.25 * FW, FW), 1.0),                    # 옆으로 펴지며 앞으로
        (0.46, frame(0.1 * s * RT - 0.1 * UP + FW, sweep), 1.0),                        # 정면 (맞는 순간)
        (0.64, frame(-0.9 * s * RT - 0.05 * UP + 0.45 * FW, sweep - 0.5 * FW), 1.0),    # 반대쪽으로 넘어감
        (0.82, frame(-0.75 * s * RT + 0.45 * UP - 0.3 * FW, -FW + 0.4 * UP), 0.7),      # 따라가며 어깨 쪽으로 올라옴
        (1.0, end, 0.0),
    ]


SWINGS = {"r2l": _swing_keys(+1), "l2r": _swing_keys(-1)}


def path(keys, p):
    """진행률 p → (무기 방향 회전, 오른손에 붙이는 정도)"""
    p = max(0.0, min(1.0, p))
    for (p0, r0, w0), (p1, r1, w1) in zip(keys, keys[1:]):
        if p <= p1:
            t = (p - p0) / (p1 - p0)
            t = t * t * (3 - 2 * t)
            return _mat(_slerp(_quat(r0), _quat(r1), t)), w0 + (w1 - w0) * t
    return keys[-1][1], keys[-1][2]


def mirror_display(d):
    """바닐라 왼손 반전의 역: 이 값을 thirdperson_lefthand 에 쓰면 반전 후 d 가 된다 (반전은 자기 역)"""
    r, t = d["rotation"], d["translation"]
    return {"rotation": [r[0], -r[1], -r[2]], "translation": [-t[0], t[1], t[2]], "scale": d["scale"]}


def grips(grip):
    """(아래 손잡이 = 왼손, 위 손잡이 = 오른손) 모델 좌표 (px)"""
    x, y, z = grip
    lo = max(0.5, y - 2.5)
    return np.array([x, lo, z]), np.array([x, lo + GRIP_SPAN, z])


def anchor(attack, charge, w, grip):
    """무기를 놓을 기준: 대기(w=0)는 두 손 가운데 ↔ 손잡이 가운데, 휘두르기(w=1)는 오른손 ↔ 위 손잡이"""
    r, l_ = hands(attack, charge)
    lo, hi = grips(grip)
    mid_world, mid_model = (r + l_) / 2, (lo + hi) / 2
    world = mid_world + (r - mid_world) * w
    model = mid_model + (hi - mid_model) * w
    return world, model


def solve(R_world, attack, grip, charge=1.0, w=0.0):
    """원하는 개체 공간 방향 → 왼손(주 손)에 넣을 3인칭 표시 변환.
    돌려주는 값 = {thirdperson_lefthand: 바닐라 반전 전 값, thirdperson_righthand: 같은 자세의 좌우 대칭 (주 손 바꾸기 실패 시)}"""
    H = hand_matrix(True, attack, charge, attack_off=True)
    A = H[:3, :3].T @ R_world
    world, model = anchor(attack, charge, w, grip)
    Hi = np.linalg.inv(H)
    target = (Hi @ np.array([*world, 1.0]))[:3]
    g = model / 16 - 0.5
    t = target - A @ (SCALE * g)
    d = {"rotation": euler_xyz(A), "translation": [round(float(v) * 16, 3) for v in t], "scale": [SCALE] * 3}
    return {"thirdperson_lefthand": mirror_display(d), "thirdperson_righthand": d}


def _charge(k):
    return min(1.0, (k + 0.5) / CHARGE_TICKS)


def stance(grip, left=False):
    """대기 자세 (left: 왼쪽 대기)"""
    return solve(STANCE_L if left else STANCE_R, 0.0, grip)


def frame_states():
    """휘두르기 프레임마다 (진행률, 공격 시간, 장전 진행). 마지막은 끝 자세(유지)"""
    out = [((k + 0.5) / SWING_TICKS, (k + 0.5) / SWING_TICKS, _charge(k)) for k in range(SWING_TICKS)]
    return out + [(1.0, 0.0, 1.0)]


def swing_frames(grip, kind="r2l"):
    """use_duration 0..SWING_TICKS-1 프레임 + 끝 자세 (반대쪽 대기와 같음)"""
    keys = SWINGS[kind]
    out = []
    for p, att, ch in frame_states():
        R, w = path(keys, p)
        out.append(solve(R, att, grip, ch, w))
    return out


def check(grip=(8, 3.5, 8)):
    """역계산 검증: 표시 변환을 다시 적용하면 원하는 방향·손잡이 위치가 나와야 함"""
    errs = []
    for kind in SWINGS:
        for d, (p, att, ch) in zip(swing_frames(grip, kind), frame_states()):
            R, w = path(SWINGS[kind], p)
            H = hand_matrix(True, att, ch, attack_off=True)
            M = H @ display_matrix(d["thirdperson_lefthand"], mirror=True)
            errs.append(np.abs(M[:3, :3] / SCALE - R).max())
            world, model = anchor(att, ch, w, grip)
            gp = M @ np.array([*(model / 16), 1.0])
            errs.append(np.abs(gp[:3] - world).max())
    return max(errs)


if __name__ == "__main__":
    print("max error", check())
    print("stance R", stance((8, 3.5, 8)))
