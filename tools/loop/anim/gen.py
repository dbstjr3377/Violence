#!/usr/bin/env python3
"""1인칭 무기 애니메이션 루프 (블록벤치 MCP).

키프레임을 블록벤치 애니메이션(.bbmodel, 'item' 뼈의 rotation/position 채널, catmullrom 보간)으로 만들고,
bbmodel_sample_pose 로 일정 간격 시각의 자세를 뽑아 리소스팩 프레임(쿨다운 임계값 → 표시 변환 차이)으로 바꾼다.
  rotation 값 = 1인칭 표시 변환 회전 차이(도), position 값 = 표시 변환 이동 차이(1/16 블록)
  애니메이션 시간 0~1 = 쿨다운 1 → 0 (t = 1 - 쿨다운)

출력: tools/loop/anim/out/fp_anims.bbmodel (원본), tools/loop/anim/out/fp_frames.json (tools/anim.py 가 읽음)
사용: python3 tools/loop/anim/gen.py
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from bbkit import mcp  # noqa: E402

OUT = os.path.join(HERE, "out")
BB = os.path.join(OUT, "fp_anims.bbmodel")
FRAMES = os.path.join(OUT, "fp_frames.json")

# ── 키프레임 (t, 회전 차이, 이동 차이) ──
CLIPS = {
    # 오른쪽 → 왼쪽 휘두르기: 손목을 덜 비튼 예비 동작 → 중간 키로 이어 붙인 타격 → 왼쪽 아래 여운 → 감속하며 복귀(ease-out)
    "SWING": {"n": 16, "keys": [
        (0.00, (0, 0, 0), (0, 0, 0)),
        (0.10, (-2, 8, 22), (2.0, 2.0, 1.0)),
        (0.20, (-4, 7, 20), (2.2, 2.2, 0.8)),
        (0.29, (-16, -4, -5), (-0.5, 0.8, -1.0)),
        (0.38, (-28, -18, -38), (-3.0, -0.5, -2.0)),
        (0.50, (-32, -26, -80), (-9.0, -1.4, -2.3)),
        (0.62, (-26, -24, -70), (-7.5, -1.0, -1.9)),
        (0.74, (-14, -13, -38), (-4.0, -0.5, -1.0)),
        (0.85, (-6, -6, -16), (-1.6, -0.2, -0.4)),
        (0.93, (-2, -2, -5), (-0.5, 0.0, -0.1)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
    # 왼쪽 → 오른쪽 되받아 휘두르기: 평소 자세에서 왼쪽으로 감아올린 뒤(순간이동 없음) 수평 호로 오른쪽까지 쓸고 감속 복귀
    "SWING_L2R": {"n": 16, "keys": [
        (0.00, (0, 0, 0), (0, 0, 0)),
        (0.12, (-7, -8, -28), (-4.0, 0.6, 0.0)),
        (0.25, (-14, -16, -60), (-8.0, 1.0, 0.0)),
        (0.42, (-10, 0, 0), (-3.0, 0.2, -1.5)),
        (0.55, (-6, 12, 35), (3.0, 0.8, 0.0)),
        (0.68, (-4, 9, 26), (2.2, 0.6, 0.0)),
        (0.80, (-2, 4, 12), (1.0, 0.3, 0.0)),
        (0.90, (-0.8, 1.5, 4), (0.35, 0.1, 0.0)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
    # 찌르기: 살짝 당겼다가 더 깊게 쭉, 잠깐 머문 뒤 감속하며 회수
    "STAB": {"n": 14, "keys": [
        (0.00, (0, 0, 0), (0, 0, 0)),
        (0.12, (-3, 0, 0), (0.4, -0.2, 1.5)),
        (0.28, (9, 0, 0), (-2.6, 0.7, -8.5)),
        (0.40, (8, 0, 0), (-2.4, 0.6, -8.0)),
        (0.55, (5, 0, 0), (-1.5, 0.4, -5.0)),
        (0.70, (2.5, 0, 0), (-0.8, 0.2, -2.4)),
        (0.85, (1, 0, 0), (-0.3, 0.05, -0.9)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
    # 총 반동: 첫 프레임 화염 + 크게 튐, 잡아 내리며 감속
    "RECOIL": {"n": 7, "keys": [
        (0.00, (9, 0, 1.8), (0.0, 0.7, 2.6)),
        (0.18, (7.5, 0, -1.2), (0.0, 0.6, 2.0)),
        (0.40, (4, 0, 0.5), (0.0, 0.3, 1.0)),
        (0.65, (1.6, 0, 0.2), (0.0, 0.12, 0.4)),
        (0.85, (0.5, 0, 0), (0.0, 0.04, 0.12)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
}
INTERP = "catmullrom"


def build_bbmodel():
    os.makedirs(OUT, exist_ok=True)
    mcp("bbmodel_create", {"file": BB, "format": "free", "name": "fp_anims", "overwrite": True})
    ops = [{"op": "add_group", "name": "item", "origin": [0, 0, 0]},
           {"op": "add_cube", "name": "weapon_proxy", "from": [-0.5, -1, -0.5], "to": [0.5, 12, 0.5], "parent": "item"}]
    for name, c in CLIPS.items():
        ops.append({"op": "add_animation", "name": name, "length": 1.0, "loop": "once", "snapping": 100})
        for t, r, p in c["keys"]:
            ops.append({"op": "set_keyframe", "animation": name, "bone": "item", "channel": "rotation", "time": t, "value": list(r), "interpolation": INTERP})
            ops.append({"op": "set_keyframe", "animation": name, "bone": "item", "channel": "position", "time": t, "value": list(p), "interpolation": INTERP})
    mcp("bbmodel_edit", {"file": BB, "operations": ops})


def sample(name, t):
    out = json.loads(mcp("bbmodel_sample_pose", {"file": BB, "animation": name, "time": round(t, 4)}))
    b = [x for x in out["bones"] if x["bone"] == "item"][0]
    return [round(v, 3) for v in b["rotation"]], [round(v, 3) for v in b["position"]]


def frames():
    """클립마다 n 구간: 구간 k (t ∈ (k/n,(k+1)/n]) 는 쿨다운 임계값 1-(k+1)/n 프레임, 구간 가운데 시각의 자세.
    마지막 구간은 평소 자세(fallback)라 프레임을 만들지 않는다. RECOIL 은 임계값 대신 상대값(1, ...)을 쓴다."""
    jobs = []
    for name, c in CLIPS.items():
        n = c["n"]
        for k in range(n - 1):
            if name == "RECOIL":   # 화염 프레임(쏜 직후 t=0) + 나머지는 화염 뒤 구간을 n-1 등분
                jobs.append((name, k, 0.0 if k == 0 else (k + 0.5) / (n - 1)))
            else:
                jobs.append((name, k, (k + 0.5) / n))
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda j: (j, sample(j[0], j[2])), jobs))
    data = {}
    for (name, k, t), (r, p) in res:
        n = CLIPS[name]["n"]
        th = round(1 - (k + 1) / n, 4) if name != "RECOIL" else round(1 - k / (n - 1), 4)
        data.setdefault(name, []).append([th, r, p, round(t, 4)])
    for v in data.values():
        v.sort(key=lambda e: -e[0])
    json.dump({"_comment": "tools/loop/anim/gen.py 가 블록벤치 MCP 로 만듦 (직접 고치지 말 것)", "clips": data},
              open(FRAMES, "w"), indent=1)
    return data


if __name__ == "__main__":
    build_bbmodel()
    d = frames()
    print({k: len(v) for k, v in d.items()})
