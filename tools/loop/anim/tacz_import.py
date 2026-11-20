#!/usr/bin/env python3
"""TACZ(총기) · LRTactical(근접) 공격 애니메이션을 우리 1인칭 프레임으로 옮긴다.

원본: TACZ 기본 총기팩 *.animation.json 의 shoot, LRTactical 근접 *.animation.json 의 melee_1/melee_2
(둘 다 GPL-3.0. 원본 파일은 레포에 넣지 않고 TACZ_DIR / LR_DIR 경로에서 읽기만 한다. 출처는 docs/CREDITS.md).

1. 원본 geo 의 뼈 계층(피벗·기본 회전)과 애니메이션 키를 블록벤치 MCP 로 .bbmodel(free) 에 옮긴다
   (베드록 → 블록벤치 내부 부호: 회전 [-x,-y,z], 이동 [-x,y,z]).
2. bbmodel_sample_pose 로 시각마다 뼈의 애니메이션 값을 뽑고, 뼈 사슬 행렬을 곱해 무기 뼈의 월드 변환을 구한다.
3. 쉬는 자세(시각 0) 대비 변화량을 '무기 쥔 점 기준 회전 R_d + 쥔 점 이동 dg' 로 저장한다.
   build_pack 이 무기마다 기본 1인칭 표시 변환에 이 변화를 합성한다 (tools/anim.py: tacz_frames).

출력: tools/loop/anim/out/tacz_anims.bbmodel, tools/loop/anim/out/tacz_frames.json
사용: TACZ_DIR=<.../tacz_default_gun/assets/tacz> LR_DIR=<.../assets/lrtactical> python3 -I tools/loop/anim/tacz_import.py
"""
import json, math, os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from bbkit import mcp  # noqa: E402

OUT = os.path.join(HERE, "out")
FRAMES = os.path.join(OUT, "tacz_frames.json")
TACZ = os.environ.get("TACZ_DIR", "")
LR = os.environ.get("LR_DIR", "")
# 애니메이션 회전 부호 (블록벤치 내부값 기준). 원본 모델+애니메이션을 bbmodel_render 로 렌더해 비교해 1,1,1 로 확인함
ROT_SIGN = [float(v) for v in os.environ.get("ROT_SIGN", "1,1,1").split(",")]

# 우리 클립 이름 → (원본, geo 종류, 원본 모델, 원본 클립, 무기 뼈, 프레임 수)
SOURCES = {
    "BAT_A": ("lr", "melee", "baseball_bat", "melee_1", "weapon", 22),
    "BAT_B": ("lr", "melee", "baseball_bat", "melee_2", "weapon", 22),
    "DAGGER_A": ("lr", "melee", "dagger", "melee_2", "weapon", 22),
    "DAGGER_B": ("lr", "melee", "dagger", "melee_1", "weapon", 22),
    "SHOOT_M16A4": ("tacz", "gun", "m16a4", "shoot", "root", 7),
    "SHOOT_MP5": ("tacz", "gun", "hk_mp5a5", "shoot", "root", 7),
    "SHOOT_M870": ("tacz", "gun", "m870", "shoot", "root", 7),
    "SHOOT_DB": ("tacz", "gun", "db_short", "shoot", "root", 7),
    "SHOOT_RHINO": ("tacz", "gun", "rhino357", "shoot", "root", 7),
    "SHOOT_MK23": ("tacz", "gun", "hk_mk23", "shoot", "root", 7),
    "SHOOT_UZI": ("tacz", "gun", "uzi", "shoot", "root", 7),
}


def paths(src, kind, model):
    root = TACZ if src == "tacz" else LR
    anim = os.path.join(root, "animations", (kind + "/" if src == "lr" else "") + model + ".animation.json")
    geo = os.path.join(root, "geo_models", kind, model + "_geo.json")
    return anim, geo


def rot_zyx(r):
    """블록벤치 그룹 회전 (도, Z·Y·X 순서 = 행렬 Rz·Ry·Rx)"""
    x, y, z = (math.radians(v) for v in r)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def key_value(v):
    if isinstance(v, dict):
        return v.get("post", v.get("pre")), v.get("lerp_mode", "linear")
    return v, "linear"


def num3(v):
    if isinstance(v, (int, float)):
        return [float(v)] * 3
    return [float(x) if isinstance(x, (int, float)) else 0.0 for x in v]


def build(bb):
    os.makedirs(OUT, exist_ok=True)
    mcp("bbmodel_create", {"file": bb, "format": "free", "name": "tacz_anims", "overwrite": True})
    geos, made = {}, set()
    ops = []
    for clip, (src, kind, model, aname, wbone, n) in SOURCES.items():
        anim_p, geo_p = paths(src, kind, model)
        g = json.load(open(geo_p, encoding="utf-8"))["minecraft:geometry"][0]
        bones = {b["name"]: b for b in g["bones"]}
        geos[clip] = bones
        pre = model + "__"
        if model not in made:
            made.add(model)
            for b in g["bones"]:
                p, r = b.get("pivot", [0, 0, 0]), b.get("rotation", [0, 0, 0])
                op = {"op": "add_group", "name": pre + b["name"], "origin": [-p[0], p[1], p[2]], "rotation": [-r[0], -r[1], r[2]]}
                if b.get("parent") in bones:
                    op["parent"] = pre + b["parent"]
                ops.append(op)
        a = json.load(open(anim_p, encoding="utf-8"))["animations"]
        a = a[aname] if aname in a else a[[k for k in a if k.endswith("." + aname)][0]]
        length = float(a.get("animation_length", 1.0))
        ops.append({"op": "add_animation", "name": clip, "length": length, "loop": "once", "snapping": 120})
        for bname, chans in a.get("bones", {}).items():
            if bname not in bones:
                continue
            for ch in ("rotation", "position"):
                if ch not in chans:
                    continue
                keys = chans[ch]
                items = [(0.0, keys)] if not isinstance(keys, dict) else [(float(t), v) for t, v in keys.items()]
                for t, v in items:
                    val, mode = key_value(v)
                    val = num3(val)
                    val = [-val[0], -val[1], val[2]] if ch == "rotation" else [-val[0], val[1], val[2]]
                    ops.append({"op": "set_keyframe", "animation": clip, "bone": pre + bname, "channel": ch, "time": round(t, 4),
                                "value": [round(x, 4) for x in val], "interpolation": "catmullrom" if mode == "catmullrom" else "linear"})
    for k in range(0, len(ops), 450):
        mcp("bbmodel_edit", {"file": bb, "operations": ops[k:k + 450]})
    return geos


def bone_matrix(bones, model, name, pose):
    """뼈 월드 행렬 (4x4, 블록벤치 내부 좌표, 단위 px). 그룹 = T(P+pos)·R·S·T(-P)"""
    pre = model + "__"
    chain = []
    b = bones[name]
    while b is not None:
        chain.append(b)
        b = bones.get(b.get("parent"))
    M = np.eye(4)
    for b in reversed(chain):
        p = b.get("pivot", [0, 0, 0]); r0 = b.get("rotation", [0, 0, 0])
        P = np.array([-p[0], p[1], p[2]], float)
        rot = np.array([-r0[0], -r0[1], r0[2]], float)
        pos = np.zeros(3); sc = np.ones(3)
        if pre + b["name"] in pose:
            v = pose[pre + b["name"]]
            rot = rot + np.array(v[0]) * np.array(ROT_SIGN); pos = np.array(v[1])
            if len(v) > 2:
                sc = np.array(v[2], float)
        L = np.eye(4)
        RS = rot_zyx(rot) @ np.diag(sc)
        L[:3, :3] = RS
        L[:3, 3] = P + pos - RS @ P
        M = M @ L
    return M


def world(bones, model, wbone, pose):
    M = bone_matrix(bones, model, wbone, pose)
    pv = bones[wbone].get("pivot", [0, 0, 0])
    return M, M @ np.array([-pv[0], pv[1], pv[2], 1.0])


def arm_ends(bones, model, name, pose):
    """팔 큐브(…hand_pos) 의 긴 축 양 끝 (월드 px). 큐브가 없으면 None"""
    b = bones.get(name)
    if not b or not b.get("cubes"):
        return None
    c = b["cubes"][0]
    o, sz = c["origin"], c["size"]
    ctr = np.array([-(o[0] + sz[0] / 2), o[1] + sz[1] / 2, o[2] + sz[2] / 2, 1.0])
    ax = int(np.argmax(sz))
    d = np.zeros(4); d[ax] = sz[ax] / 2
    M = bone_matrix(bones, model, name, pose)
    return (M @ (ctr - d))[:3], (M @ (ctr + d))[:3]


def sample(bb, clip, t):
    out = json.loads(mcp("bbmodel_sample_pose", {"file": bb, "animation": clip, "time": round(t, 4)}))
    return {b["bone"]: (b["rotation"], b["position"], b.get("scale", [1, 1, 1])) for b in out["bones"]}


def main():
    bb = os.path.join(OUT, "tacz_anims.bbmodel")
    cache = os.path.join(OUT, "tacz_poses.json")
    if os.environ.get("REUSE") and os.path.exists(cache):
        res = [((c, i, t), p) for c, i, t, p in json.load(open(cache))]
        geos = {clip: {b["name"]: b for b in json.load(open(paths(s[0], s[1], s[2])[1], encoding="utf-8"))["minecraft:geometry"][0]["bones"]}
                for clip, s in SOURCES.items()}
        return finish(res, geos)
    geos = build(bb)
    info = json.loads(mcp("bbmodel_info", {"file": bb}))
    lengths = {a["name"]: a.get("length", 1.0) for a in info.get("animations", [])}
    jobs = []
    for clip, (src, kind, model, aname, wbone, n) in SOURCES.items():
        L = lengths.get(clip, 1.0)
        times = [0.0]
        if clip.startswith("SHOOT"):
            # 0 = 화염 프레임(반동 정점 1/30 초), 나머지는 그 뒤를 n-1 등분한 구간 가운데
            peak = min(1 / 30, L)
            times += [peak] + [peak + (L - peak) * (k + 0.5) / (n - 1) for k in range(1, n)]
        else:
            times += [L * (k + 0.5) / n for k in range(n - 1)]
        for i, t in enumerate(times):
            jobs.append((clip, i, t))
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda j: (j, sample(bb, j[0], j[2])), jobs))
    json.dump([[c, i, t, p] for (c, i, t), p in res], open(cache, "w"))
    return finish(res, geos)


def finish(res, geos):
    poses = {}
    for (clip, i, t), pose in res:
        poses.setdefault(clip, {})[i] = (t, pose)
    data = {}
    for clip, (src, kind, model, aname, wbone, n) in SOURCES.items():
        bones = geos[clip]
        M0, g0 = world(bones, model, wbone, poses[clip][0][1])
        frames = []
        for i in sorted(poses[clip])[1:]:
            t, pose = poses[clip][i]
            M, g = world(bones, model, wbone, pose)
            Rd = M[:3, :3] @ M0[:3, :3].T
            frames.append({"t": round(t, 4), "Rd": [[round(x, 5) for x in row] for row in Rd], "dg": [round(x, 3) for x in (g - g0)[:3]]})
        entry = {"source": f"{src}:{model}:{aname}", "frames": frames}
        if not clip.startswith("SHOOT"):
            # 근접: 무기 절대 자세 (눈 = camera 뼈 피벗 기준). 무기 길이 방향 = 큐브 중심 - 무기 뼈 피벗 (원본 바인드 좌표)
            cam = bones["camera"]["pivot"]; E = np.array([-cam[0], cam[1], cam[2]], float)
            wb = bones[wbone]; pv = wb.get("pivot", [0, 0, 0]); P = np.array([-pv[0], pv[1], pv[2]], float)
            cs = []
            def collect(b):
                for c in b.get("cubes", []):
                    o, sz = c["origin"], c["size"]
                    cs.append(np.array([-(o[0] + sz[0] / 2), o[1] + sz[1] / 2, o[2] + sz[2] / 2]))
                for ch in bones.values():
                    if ch.get("parent") == b["name"]:
                        collect(ch)
            collect(wb)
            # 길이 방향 = 큐브 상자에서 피벗으로부터 가장 먼 끝 (손잡이 쪽 작은 큐브가 많아도 날 쪽을 가리키게)
            lo = np.min([c - 0 for c in cs], axis=0)
            pts = []
            def corners(b):
                for c in b.get("cubes", []):
                    o, sz = c["origin"], c["size"]
                    for dx in (0, sz[0]):
                        for dy in (0, sz[1]):
                            for dz in (0, sz[2]):
                                pts.append(np.array([-(o[0] + dx), o[1] + dy, o[2] + dz]))
                for ch in bones.values():
                    if ch.get("parent") == b["name"]:
                        corners(ch)
            corners(wb)
            far = max(pts, key=lambda q: np.linalg.norm(q - P))
            tip = (far - P) / np.linalg.norm(far - P)
            ab = []
            for i in sorted(poses[clip]):
                t, pose = poses[clip][i]
                M, g = world(bones, model, wbone, pose)
                fr = {"t": round(t, 4), "R": [[round(x, 5) for x in row] for row in M[:3, :3]], "g": [round(x, 3) for x in (g[:3] - E)]}
                Rn = M[:3, :3] / np.linalg.norm(M[:3, :3], axis=0)   # 크기 빼고 회전만
                fr["R"] = [[round(x, 5) for x in row] for row in Rn]
                for side, bn in (("r", "righthand_pos"), ("l", "lefthand_pos")):
                    e = arm_ends(bones, model, bn, pose)
                    if e is None:
                        continue
                    a, b2 = e
                    # 1인칭 팔은 눈 쪽에서 앞으로 뻗는다: 눈에서 먼 끝 = 손
                    if np.linalg.norm(a - E) > np.linalg.norm(b2 - E):
                        a, b2 = b2, a
                    u = (b2 - a) / np.linalg.norm(b2 - a)
                    near = a                    # 원본 팔 그대로
                    fr["arm_" + side] = [[round(x, 3) for x in (near - E)], [round(x, 3) for x in (b2 - E)]]
                    if side == "r":
                        fr["hand"] = [round(x, 3) for x in (b2 - u * 2 - E)]   # 주먹 가운데 (끝에서 굵기 절반 안쪽)
                ab.append(fr)
            entry["abs"] = ab
            entry["tip"] = [round(x, 4) for x in tip]
        data[clip] = entry
    json.dump({"_comment": "tools/loop/anim/tacz_import.py 가 블록벤치 MCP 로 만듦. 원본: TACZ / LRTactical (GPL-3.0)", "clips": data},
              open(FRAMES, "w"), indent=1)
    for c, d in data.items():
        mx = max(math.degrees(math.acos(max(-1, min(1, (np.trace(np.array(f["Rd"])) - 1) / 2)))) for f in d["frames"])
        print(c, d["source"], len(d["frames"]), "max rot", round(mx, 1), "max dg", round(max(np.linalg.norm(f["dg"]) for f in d["frames"]), 2))


if __name__ == "__main__":
    main()
