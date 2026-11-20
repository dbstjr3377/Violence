"""1인칭 키프레임 (쿨다운 진행률 → 표시 변환 차이). fp_sim 과 build_pack 이 함께 쓴다."""

# (임계값, 회전 차이, 이동 차이) — 쿨다운 값이 임계값 이상이면 해당 프레임 (값은 1 → 0 으로 줄어듦)
# 휘두르기 (오른쪽 → 왼쪽): 오른쪽으로 젖혔다가 화면을 가로질러 왼쪽 아래까지 길게 벤다
SWING = [(0.82, (-2, 14, 38), (2.0, 2.0, 1.0)),
         (0.62, (-30, -20, -35), (-3.0, -0.5, -2.0)),
         (0.42, (-34, -30, -90), (-10.0, -1.5, -2.5)),
         (0.18, (-14, -18, -40), (-4.0, -0.4, -0.8))]
# 되받아 휘두르기 (왼쪽 → 오른쪽): 앞 동작이 끝난 왼쪽에서 시작해 오른쪽으로 쓸어 올린다
SWING_L2R = [(0.82, (-20, -20, -75), (-9.0, 1.2, 0.0)),
             (0.62, (-30, 0, 10), (-1.0, -0.5, -2.5)),
             (0.42, (-10, 14, 40), (3.0, 1.0, 0.0)),
             (0.18, (-4, 6, 18), (1.5, 0.3, 0.0))]
STAB = [(0.75, (8, 0, 0), (-2.4, 0.6, -7.0)),
        (0.5, (6, 0, 0), (-1.8, 0.4, -4.0)),
        (0.25, (2, 0, 0), (-0.6, 0.1, -1.4))]
# RECOIL 의 첫 값은 화염 프레임 임계값에 곱하는 상대값 (1 = 화염 프레임)
RECOIL = [(1.0, (7, 0, 1.5), (0.0, 0.5, 2.0)),
          (0.62, (4.5, 0, -1.0), (0.0, 0.3, 1.2)),
          (0.3, (1.5, 0, 0.6), (0.0, 0.05, 0.4))]

# 블록벤치 MCP 로 만든 키프레임 (tools/loop/anim/gen.py → fp_frames.json) 이 있으면 그것을 쓴다
import json as _json, os as _os
_F = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "loop", "anim", "out", "fp_frames.json")
if _os.path.exists(_F):
    _c = _json.load(open(_F, encoding="utf-8"))["clips"]
    SWING, SWING_L2R, STAB, RECOIL = ([(e[0], tuple(e[1]), tuple(e[2])) for e in _c[k]] for k in ("SWING", "SWING_L2R", "STAB", "RECOIL"))


def apply(base, delta_rot, delta_t):
    r = [base["rotation"][i] + delta_rot[i] for i in range(3)]
    t = [round(base["translation"][i] + delta_t[i], 3) for i in range(3)]
    return {"rotation": r, "translation": t, "scale": base["scale"]}


# ── TACZ / LRTactical 에서 옮긴 공격 애니메이션 (tools/loop/anim/tacz_import.py → tacz_frames.json) ──
# 무기 뼈의 '쥔 점 기준 회전 Rd + 쥔 점 이동 dg' 를 무기마다 기본 1인칭 표시 변환에 합성한다.
import math as _m
_TF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "loop", "anim", "out", "tacz_frames.json")
TACZ = _json.load(open(_TF, encoding="utf-8"))["clips"] if _os.path.exists(_TF) else {}
MELEE_FAMILY = {w: "DAGGER" for w in ("dagger", "cleaver", "machete")}
GUN_CLIP = {"m16": "SHOOT_M16A4", "mp5": "SHOOT_MP5", "shotgun": "SHOOT_M870", "double_barrel": "SHOOT_DB",
            "magnum": "SHOOT_RHINO", "silenced_pistol": "SHOOT_MK23", "uzi": "SHOOT_UZI", "silenced_uzi": "SHOOT_UZI"}


def _mat_xyz(r):
    x, y, z = (_m.radians(v) for v in r)
    cx, sx, cy, sy, cz, sz = _m.cos(x), _m.sin(x), _m.cos(y), _m.sin(y), _m.cos(z), _m.sin(z)
    Rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return _mm(_mm(Rx, Ry), Rz)


def _mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(A, v):
    return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]


def _euler_xyz(R, near):
    """행렬 = Rx·Ry·Rz (자바 표시 변환 회전) → 각도, near 에 가장 가까운 표현"""
    b = _m.asin(max(-1.0, min(1.0, R[0][2])))
    a = _m.atan2(-R[1][2], R[2][2])
    c = _m.atan2(-R[0][1], R[0][0])
    out = []
    for v, n in zip((_m.degrees(a), _m.degrees(b), _m.degrees(c)), near):
        while v - n > 180: v -= 360
        while v - n < -180: v += 360
        out.append(round(v, 2))
    return out


def tacz_disps(base, clip, grip, k=1.0):
    """base 1인칭 표시 변환에 TACZ 클립을 합성한 표시 변환 목록 (프레임 순서대로)"""
    R0 = _mat_xyz(base["rotation"])
    s = base["scale"]
    gl = [(grip[i] - 8) * s[i] for i in range(3)]
    rg = _mv(R0, gl)
    out, prev = [], list(base["rotation"])
    for f in TACZ[clip]["frames"]:
        Rd = f["Rd"]
        rot = _euler_xyz(_mm(Rd, R0), prev)
        prev = rot
        d = _mv(Rd, rg)
        t = [round(base["translation"][i] + rg[i] - d[i] + k * f["dg"][i], 3) for i in range(3)]
        out.append({"rotation": rot, "translation": t, "scale": base["scale"]})
    return out


def tacz_thresholds(clip, gun=False):
    n = len(TACZ[clip]["frames"])
    if gun:
        return [round(1 - i / n, 4) for i in range(n)]   # 화염 프레임 대비 상대값
    return [round(1 - (i + 1) / (n + 1), 4) for i in range(n)]


def _shortest_arc(a, b):
    """단위벡터 a 를 b 로 돌리는 행렬"""
    ax = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    c = sum(a[i] * b[i] for i in range(3))
    s = _m.sqrt(sum(v * v for v in ax))
    if s < 1e-9:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]] if c > 0 else [[1, 0, 0], [0, -1, 0], [0, 0, -1]]
    k = [v / s for v in ax]
    K = [[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]
    K2 = _mm(K, K)
    return [[(1 if i == j else 0) + s * K[i][j] + (1 - c) * K2[i][j] for j in range(3)] for i in range(3)]


# 바닐라 1인칭 오른손 아이템 위치 (블록 0.56, -0.52, -0.72 → px)
HAND = (0.56 * 16, -0.52 * 16, -0.72 * 16)


def tacz_abs(base, clip, grip, axis=(0, 1, 0), k=1.0):
    """원본 무기의 절대 자세(눈 기준)를 그대로 옮긴 표시 변환 목록. [0] = 쉬는 자세(t=0), 나머지 = 프레임"""
    c = TACZ[clip]
    A = _shortest_arc(list(axis), c["tip"])
    s = base["scale"]
    gl = [(grip[i] - 8) * s[i] for i in range(3)]
    out, prev = [], list(base["rotation"])
    for f in c["abs"]:
        R = _mm(f["R"], A)
        rot = _euler_xyz(R, prev)
        prev = rot
        rg = _mv(R, gl)
        t = [round(k * f["g"][i] - HAND[i] - rg[i], 3) for i in range(3)]
        out.append({"rotation": rot, "translation": t, "scale": s})
    return out
