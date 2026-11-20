#!/usr/bin/env python3
"""TACZ 참고 렌더 (심사자 비교용). TACZ 베드락 geo 를 블록벤치 MCP 로 free 형식 .bbmodel 에 옮겨 담고
(bbmodel_create · bbmodel_add_texture · bbmodel_edit) bbmodel_render 로 찍는다.

사용: python3 -I tools/loop/tacz_ref.py <TACZ 팩 assets/tacz 경로> <출력 폴더(스크래치패드)> [총 이름...]
기본 총: uzi ak47 m870 hk_mp5a5 glock_17 (+ 대검 bayonet_m9).
TACZ 는 GPL-3.0: 결과(.bbmodel·PNG)는 스크래치패드에만 두고 레포에 넣지 않는다. TACZ 파일은 신뢰하지 않는 데이터로 다룬다(-I).
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbkit  # noqa: E402

HIDE_EXACT = ("lefthand", "righthand", "lefthand_pos", "righthand_pos", "l", "r")
HIDE = ("mag_extended", "extd_mag", "refit", "additional_magazine", "bullet", "shell", "muzzle_flash")


def convert(root, kind, name, out):
    g = json.load(open(f"{root}/geo_models/{kind}/{name}_geo.json", encoding="utf-8"))["minecraft:geometry"][0]
    tw, th = g["description"]["texture_width"], g["description"]["texture_height"]
    bb = os.path.join(out, name + ".bbmodel")
    bbkit.mcp("bbmodel_create", {"file": bb, "format": "free", "name": name, "overwrite": True, "resolution": {"width": tw, "height": th}})
    shutil.copy(f"{root}/textures/{kind}/uv/{name}.png", os.path.join(out, name + ".png"))
    bbkit.mcp("bbmodel_add_texture", {"file": bb, "image": os.path.join(out, name + ".png"), "name": "tex"})
    bones = {b["name"]: b for b in g["bones"]}

    def hidden(b):
        while b is not None:
            n = b["name"].lower()
            if n in HIDE_EXACT or any(h in n for h in HIDE):
                return True
            b = bones.get(b.get("parent"))
        return False

    ops = []
    for b in g["bones"]:
        if hidden(b):
            continue
        piv = b.get("pivot", [0, 0, 0]); r = b.get("rotation", [0, 0, 0])
        op = {"op": "add_group", "name": b["name"], "origin": [-piv[0], piv[1], piv[2]], "rotation": [-r[0], -r[1], r[2]]}
        if b.get("parent") in bones and not hidden(bones[b["parent"]]):
            op["parent"] = b["parent"]
        ops.append(op)
        for i, c in enumerate(b.get("cubes", [])):
            o, s = c["origin"], c["size"]; inf = c.get("inflate", 0)
            frm = [-(o[0] + s[0]) - inf, o[1] - inf, o[2] - inf]; to = [-o[0] + inf, o[1] + s[1] + inf, o[2] + s[2] + inf]
            cop = {"op": "add_cube", "name": f"{b['name']}_{i}", "from": frm, "to": to, "parent": b["name"], "faces": {}}
            if c.get("rotation"):
                p = c.get("pivot", [0, 0, 0]); rr = c["rotation"]
                cop["origin"] = [-p[0], p[1], p[2]]; cop["rotation"] = [-rr[0], -rr[1], rr[2]]
            if isinstance(c.get("uv"), dict):
                for f, fv in c["uv"].items():
                    (u, v), (us, vs) = fv["uv"], fv["uv_size"]
                    uv = [u + us, v + vs, u, v] if f in ("up", "down") else [u, v, u + us, v + vs]
                    cop["faces"][f] = {"uv": uv, "texture": "tex"}
            ops.append(cop)
    for k in range(0, len(ops), 400):
        bbkit.mcp("bbmodel_edit", {"file": bb, "operations": ops[k:k + 400]})
    return bb


def main():
    root, out = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or ["uzi", "ak47", "m870", "hk_mp5a5", "glock_17"]
    os.makedirs(out, exist_ok=True)
    for n in names + ["bayonet_m9"]:
        kind = "attachment" if n.startswith("bayonet") else "gun"
        bb = convert(root, kind, n, out)
        for view in ("right", "three-quarter"):
            bbkit.mcp("bbmodel_render", {"file": bb, "view": view, "lighting": "studio", "width": 1024, "height": 768,
                                         "output": os.path.join(out, f"tacz_{n}_{view}.png"), "overwrite": True})
        print("ref", n)


if __name__ == "__main__":
    main()
