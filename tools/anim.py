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
