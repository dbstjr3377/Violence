"""
1인칭 팔: 플레이어 스킨을 입힌 두 마디 팔 (어깨 → 팔꿈치 → 손).

- 텍스처: violence:skin/self (64x64 스킨). 리소스팩에는 기본 스킨이 있고, 플러그인이 접속한 사람에게
  자기 스킨을 같은 경로로 덮는 작은 리소스팩을 따로 보낸다 (1인칭 팔은 자기 눈에만 보이므로 모두 같은 모델을 씀).
- 팔 모양: 바닐라 플레이어 팔(4x12x4)을 위아래 반씩 위팔/아래팔로 나눔. 바깥 겉옷 층(소매)도 0.25px 부풀려 겹침.
- 자세: 어깨는 화면 밖 아래 고정 자리, 손은 무기 손잡이. 두 마디 IK 로 팔꿈치를 정하고
  프레임(표시 변환)마다 다시 풀어서 무기가 휘둘러질 때 팔꿈치가 굽혀지고 펴진다.
- 큐브 회전: 26.3 모델은 원소마다 x·y·z 오일러 회전(rotationZYX)을 지원한다.
좌표: fp_sim 과 같은 1인칭 시점 좌표 (블록 단위, 오른쪽 +x, 위 +y, 앞 -z).
"""
import math

import fp_sim

SKIN = "violence:skin/self"

# 어깨 관절 자리 (시점 좌표, 블록): 화면 밖 오른쪽/왼쪽 아래
SHOULDER = {"r": (0.40, -0.66, -0.06), "l": (-0.34, -0.70, -0.06)}
# 팔 굵기 (시점 좌표, 블록): 예전 1인칭 소매 굵기 정도
THICK = 0.13
# 팔꿈치가 굽는 쪽 (바깥 아래)
POLE = {"r": (1.0, -1.0, 0.3), "l": (-1.0, -1.0, 0.3)}

# 스킨 UV (픽셀). 옆면은 (바깥, 앞, 안, 뒤) 순서로 4픽셀씩, 위/아래 4x4
_ARM_UV = {
    # 오른팔: 바닥 층 (40,16), 겉옷 층 (40,32). 첫 칸이 바깥쪽
    "r": {"base": (40, 16), "over": (40, 32), "order": ("outer", "front", "inner", "back")},
    # 왼팔: 바닥 층 (32,48), 겉옷 층 (48,48). 첫 칸이 안쪽
    "l": {"base": (32, 48), "over": (48, 48), "order": ("inner", "front", "outer", "back")},
}


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _add(a, b):
    return [a[i] + b[i] for i in range(3)]


def _mul(a, k):
    return [v * k for v in a]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _len(a):
    return math.sqrt(_dot(a, a))


def _norm(a):
    n = _len(a)
    return [v / n for v in a] if n > 1e-9 else [0.0, 0.0, 0.0]


def _disp_rot(disp):
    r = [math.radians(v) for v in disp.get("rotation", [0, 0, 0])]
    return fp_sim.mm(fp_sim.mm(fp_sim.rx(r[0]), fp_sim.ry(r[1])), fp_sim.rz(r[2]))


def to_cam(disp, p):
    """모델 좌표(16 단위) → 시점 좌표"""
    return fp_sim.muzzle_screen(disp, p)[0]


def to_model(disp, v):
    """시점 좌표 → 모델 좌표 (fp_sim.muzzle_screen 의 역변환)"""
    t = [x / 16 for x in disp.get("translation", [0, 0, 0])]
    s = disp.get("scale", [1, 1, 1])
    R = _disp_rot(disp)
    q = [v[i] - t[i] - (0.56, -0.52, -0.72)[i] for i in range(3)]
    q = [sum(R[k][i] * q[k] for k in range(3)) for i in range(3)]   # R^T
    return [(q[i] / s[i] + 0.5) * 16 for i in range(3)]


def dir_to_model(disp, d):
    R = _disp_rot(disp)
    return _norm([sum(R[k][i] * d[k] for k in range(3)) for i in range(3)])


def solve(shoulder, hand, l1, l2, pole):
    """두 마디 IK: 팔꿈치 위치 (손이 닿지 않으면 손 쪽으로 쭉 뻗음)"""
    d = _sub(hand, shoulder)
    dist = _len(d)
    n = _norm(d)
    if dist >= l1 + l2 - 1e-6:
        return _add(shoulder, _mul(n, l1)), _add(shoulder, _mul(n, l1 + l2))
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    p = _sub(pole, _mul(n, _dot(pole, n)))
    p = _norm(p) if _len(p) > 1e-6 else _norm(_cross(n, [0, 0, 1]))
    return _add(_add(shoulder, _mul(n, a)), _mul(p, h)), hand


def _euler_zyx(cols):
    """열 벡터 (X, Y, Z) 로 된 회전행렬 → 마인크래프트 원소 회전 {x, y, z}° (R = Rz·Ry·Rx)"""
    X, Y, Z = cols
    m = [[X[0], Y[0], Z[0]], [X[1], Y[1], Z[1]], [X[2], Y[2], Z[2]]]
    y = math.asin(max(-1.0, min(1.0, -m[2][0])))
    if abs(math.cos(y)) > 1e-6:
        x = math.atan2(m[2][1], m[2][2])
        z = math.atan2(m[1][0], m[0][0])
    else:
        x = math.atan2(-m[1][2], m[1][1])
        z = 0.0
    return {"x": round(math.degrees(x), 3), "y": round(math.degrees(y), 3), "z": round(math.degrees(z), 3)}


def _faces(side, layer, rows, cap):
    """rows: 옆면 스킨 줄 범위 (0~12), cap: 'up' / 'down' / None (위·아래 면)"""
    u0, v0 = _ARM_UV[side][layer]
    order = _ARM_UV[side]["order"]
    col = {name: u0 + 4 * i for i, name in enumerate(order)}
    # 바깥쪽 면: 오른팔은 +x(east), 왼팔은 -x(west)
    outer, inner = ("east", "west") if side == "r" else ("west", "east")
    face_of = {"front": "north", "back": "south", "outer": outer, "inner": inner}
    out = {}
    for name, f in face_of.items():
        x = col[name]
        out[f] = {"uv": [x / 4, (v0 + 4 + rows[0]) / 4, (x + 4) / 4, (v0 + 4 + rows[1]) / 4], "texture": "#skin"}
    if cap == "up":
        out["up"] = {"uv": [(u0 + 4) / 4, v0 / 4, (u0 + 8) / 4, (v0 + 4) / 4], "texture": "#skin"}
    if cap == "down":
        out["down"] = {"uv": [(u0 + 8) / 4, v0 / 4, (u0 + 12) / 4, (v0 + 4) / 4], "texture": "#skin"}
    return out


def _segment(disp, a_cam, b_cam, thick_cam, side, rows, cap, layer):
    """시점 좌표 a→b 를 잇는 팔 한 마디 → 모델 원소"""
    s = disp.get("scale", [1, 1, 1])[0]
    d = _norm(_sub(b_cam, a_cam))
    # 팔의 앞면(스킨 front)은 화면 위쪽을 보게 (총을 앞으로 든 팔은 앞면이 위를 향함)
    up = [0.0, 1.0, 0.0]
    f = _sub(up, _mul(d, _dot(up, d)))
    f = _norm(f) if _len(f) > 1e-4 else _norm(_cross(d, [1, 0, 0]))
    Yc = _mul(d, -1)          # 원소 +y = 손 → 어깨
    Zc = _mul(f, -1)          # 원소 -z(north) = 앞면
    Xc = _cross(Yc, Zc)
    cols = [dir_to_model(disp, Xc), dir_to_model(disp, Yc), dir_to_model(disp, Zc)]
    rot = _euler_zyx(cols)
    mid = to_model(disp, _mul(_add(a_cam, b_cam), 0.5))
    length = _len(_sub(b_cam, a_cam)) * 16 / s
    t = thick_cam * 16 / s
    if layer == "over":
        t *= 1.125                     # 겉옷 층: 바닐라처럼 조금 부풀림
        length += t * 0.06
    h = t / 2
    # 원소 좌표는 -16~32 안이어야 하지만 회전 중심(origin)은 제한이 없다.
    # 회전 전 상자 중심 pc 를 모델 가운데 가까이 두고, origin 을 골라 회전 뒤 중심이 mid 에 오게 한다:
    #   origin + M (pc - origin) = mid  →  (I - M) origin = mid - M pc   (pc 는 회전축 방향 성분만 mid 와 같으면 됨)
    pc, origin = _place(mid, rot)
    el = {"from": [round(pc[0] - h, 3), round(pc[1] - length / 2, 3), round(pc[2] - h, 3)],
          "to": [round(pc[0] + h, 3), round(pc[1] + length / 2, 3), round(pc[2] + h, 3)],
          "rotation": dict(origin=[round(v, 4) for v in origin], **rot),
          "faces": _faces(side, layer, rows, cap)}
    return el


def _rot_matrix(rot):
    r = lambda k: math.radians(rot[k])
    return fp_sim.mm(fp_sim.mm(fp_sim.rz(r("z")), fp_sim.ry(r("y"))), fp_sim.rx(r("x")))


def _place(mid, rot, center=(8.0, 8.0, 8.0)):
    """회전 전 상자 중심 pc 와 회전 중심 origin (회전 뒤 상자 중심이 mid)"""
    import numpy as np
    M = np.array(_rot_matrix(rot))
    mid = np.array(mid, float)
    c = np.array(center, float)
    # 회전축 n (고윳값 1 의 고유벡터)
    w, v = np.linalg.eig(M)
    k = int(np.argmin(np.abs(w - 1)))
    n = np.real(v[:, k])
    n /= np.linalg.norm(n)
    angle = math.acos(max(-1.0, min(1.0, (np.trace(M) - 1) / 2)))
    if angle < 1e-4:
        return list(mid), list(mid)
    pc = c + n * np.dot(n, mid - c)
    rhs = mid - M @ pc
    origin, *_ = np.linalg.lstsq(np.eye(3) - M, rhs, rcond=None)
    return [float(x) for x in pc], [float(x) for x in origin]


def arm(disp, hand_model, side, l1, l2, thick=THICK):
    """한 팔 (위팔 + 아래팔, 각각 바닥 층 + 겉옷 층) 원소 목록. 손잡이가 주먹 가운데에 오게 손끝을 조금 더 뻗음"""
    s_cam = list(SHOULDER[side])
    h_cam = to_cam(disp, hand_model)
    e_cam, h_cam = solve(s_cam, h_cam, l1, l2, list(POLE[side]))
    lo = _norm(_sub(h_cam, e_cam))
    end = _add(h_cam, _mul(lo, thick * 0.5))
    out = []
    for layer in ("base", "over"):
        out.append(_segment(disp, s_cam, e_cam, thick, side, (0, 6), "up", layer))
        out.append(_segment(disp, e_cam, end, thick, side, (6, 12), "down", layer))
    return out


def lengths(disps_hands, side):
    """무기 하나의 모든 프레임에서 손이 닿도록 위팔·아래팔 길이와 굵기 (시점 좌표, 블록)"""
    s = SHOULDER[side]
    ds = [_len(_sub(to_cam(d, h), s)) for d, h in disps_hands]
    seg = max(ds[0] * 0.58, max(ds) * 0.505)
    return seg, seg, THICK
