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
    # 오른쪽 → 왼쪽 휘두르기: 빠르게 젖혀 잠깐 버틴 뒤, 화면을 가로질러 왼쪽 아래까지 베고, 천천히 돌아옴
    "SWING": {"n": 14, "keys": [
        (0.00, (0, 0, 0), (0, 0, 0)),
        (0.10, (-2, 14, 38), (2.0, 2.0, 1.0)),
        (0.20, (-6, 12, 32), (2.2, 2.2, 0.8)),
        (0.38, (-30, -20, -35), (-3.0, -0.5, -2.0)),
        (0.52, (-34, -30, -90), (-10.0, -1.5, -2.5)),
        (0.70, (-22, -22, -62), (-6.0, -0.8, -1.5)),
        (0.88, (-6, -6, -15), (-1.2, -0.1, -0.3)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
    # 왼쪽 → 오른쪽 되받아 휘두르기
    "SWING_L2R": {"n": 14, "keys": [
        (0.00, (-20, -20, -75), (-9.0, 1.2, 0.0)),
        (0.12, (-24, -18, -80), (-9.5, 1.4, 0.2)),
        (0.36, (-30, 0, 10), (-1.0, -0.5, -2.5)),
        (0.52, (-10, 14, 40), (3.0, 1.0, 0.0)),
        (0.72, (-6, 10, 28), (2.2, 0.7, 0.0)),
        (0.90, (-2, 3, 8), (0.6, 0.2, 0.0)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
    # 찌르기: 살짝 당겼다가 앞으로 쭉, 천천히 회수
    "STAB": {"n": 12, "keys": [
        (0.00, (0, 0, 0), (0, 0, 0)),
        (0.12, (-3, 0, 0), (0.4, -0.2, 1.2)),
        (0.30, (8, 0, 0), (-2.4, 0.6, -7.0)),
        (0.55, (6, 0, 0), (-1.8, 0.4, -4.0)),
        (0.80, (2, 0, 0), (-0.6, 0.1, -1.4)),
        (1.00, (0, 0, 0), (0, 0, 0))]},
    # 총 반동: 첫 프레임은 화염 (쏜 직후), 위로 튀었다가 잡아 내림
    "RECOIL": {"n": 6, "keys": [
        (0.00, (7, 0, 1.5), (0.0, 0.5, 2.0)),
        (0.30, (5, 0, -1.0), (0.0, 0.35, 1.4)),
        (0.65, (2, 0, 0.6), (0.0, 0.1, 0.5)),
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
