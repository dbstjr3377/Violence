#!/usr/bin/env python3
"""텍스처 잡티 검사 (루프 2단계).

사용:
  python3 tools/loop/speck_check.py --model <모델> <텍스처.png> [--json out.json]
  python3 tools/loop/speck_check.py <png...>          (모델 없이: 그림/맵 텍스처용)
모델: .bbmodel, Java 모델 .json(elements), Bedrock geo .json(minecraft:geometry).
종료코드 0 = 통과, 1 = 잡티 발견.

모델이 있으면 UV 면 사각형 안에서만 검사한다(아틀라스 면 경계·면 사이 빈칸은 무시).
  speck      면 안에서 상하좌우 4이웃이 모두 같은 색인데 자신만 다른 고립 픽셀
  pinhole    면 안에서 4방향이 불투명으로 둘러싸인 투명 구멍 (면 전체가 투명한 숨김 면은 제외)
  semi_alpha 면 안의 반투명 픽셀(알파 1~254) 비율
  near_dup   면 안에서 거의 같은 색(채널 차 1~6)이 맞붙은 비율 = 노이즈/디더링 흔적
  noisy_face 5색 이상 쓰인 면 비율 (TACZ는 10% 미만)
기준값은 TACZ 기본 건팩(AK47·M870·M9 대검 등) 실측으로 맞췄다. 원본은 통과해야 한다.
"""
import argparse, json, math, sys
from PIL import Image

NEAR = 6
LIMITS = {"speck_ratio": 0.004, "pinhole": 0, "semi_alpha_ratio": 0.001,
          "near_dup_ratio": 0.30, "noisy_face_ratio": 0.12}


def _rect(x0, y0, x1, y1):
    xa, xb = sorted((x0, x1)); ya, yb = sorted((y0, y1))
    return (int(math.floor(xa + 1e-6)), int(math.floor(ya + 1e-6)),
            int(math.ceil(xb - 1e-6)), int(math.ceil(yb - 1e-6)))


def face_rects(model_path, tex_w, tex_h):
    with open(model_path, encoding="utf-8") as f:
        m = json.load(f)
    rects = []
    if "minecraft:geometry" in m:
        g = m["minecraft:geometry"][0]
        d = g["description"]
        k = tex_w / d.get("texture_width", tex_w)
        for b in g.get("bones", []):
            for c in b.get("cubes", []):
                uv = c.get("uv")
                if isinstance(uv, dict):
                    for fv in uv.values():
                        (u, v), (us, vs) = fv["uv"], fv["uv_size"]
                        rects.append(_rect(u * k, v * k, (u + us) * k, (v + vs) * k))
                elif isinstance(uv, list):
                    sx, sy, sz = [math.floor(s) for s in c["size"]]
                    u, v = uv
                    for (a, bb, w_, h_) in ((u + sz, v, sx, sz), (u + sz + sx, v, sx, sz),
                                             (u, v + sz, sz, sy), (u + sz, v + sz, sx, sy),
                                             (u + sz + sx, v + sz, sz, sy), (u + 2 * sz + sx, v + sz, sx, sy)):
                        rects.append(_rect(a * k, bb * k, (a + w_) * k, (bb + h_) * k))
    elif "elements" in m:
        if "meta" in m or "resolution" in m:  # bbmodel
            res = m.get("resolution", {})
            tx = (m.get("textures") or [{}])[0]
            uw = tx.get("uv_width", res.get("width", 16)); uh = tx.get("uv_height", res.get("height", 16))
        else:  # Java 모델
            uw = uh = 16
        kx, ky = tex_w / uw, tex_h / uh
        for e in m["elements"]:
            for fv in (e.get("faces") or {}).values():
                uv = fv.get("uv")
                if uv and fv.get("texture") is not None:
                    rects.append(_rect(uv[0] * kx, uv[1] * ky, uv[2] * kx, uv[3] * ky))
    return [r for r in rects if r[2] > r[0] and r[3] > r[1]]


def check(path, model=None):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    rects = face_rects(model, w, h) if model else [(0, 0, w, h)]
    seen = set()
    total = speck = pinhole = semi = near = noisy = faces = 0
    where = []
    for (x0, y0, x1, y1) in rects:
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        faces += 1
        cols = set()
        if model and all(px[x, y][3] == 0 for y in range(y0, y1) for x in range(x0, x1)):
            continue  # 면 전체가 투명 = 의도적으로 숨긴 면
        for y in range(y0, y1):
            for x in range(x0, x1):
                p = px[x, y]
                cols.add(p[:3])
                if (x, y) in seen:
                    continue
                seen.add((x, y))
                a = p[3]
                if a == 0:
                    if model and all(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] == 255
                                     and x0 <= x + dx < x1 and y0 <= y + dy < y1
                                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        pinhole += 1
                        if len(where) < 20: where.append(("pinhole", x, y))
                    continue
                total += 1
                if a < 255:
                    semi += 1
                inside = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                          if x0 <= x + dx < x1 and y0 <= y + dy < y1]
                if len(inside) == 4:
                    nb = [px[q] for q in inside]
                    if all(n[3] == 255 for n in nb):
                        c0 = nb[0][:3]
                        if all(n[:3] == c0 for n in nb) and p[:3] != c0:
                            speck += 1
                            if len(where) < 20: where.append(("speck", x, y))
                for dx, dy in ((1, 0), (0, 1)):
                    if x + dx < x1 and y + dy < y1:
                        q = px[x + dx, y + dy]
                        if q[3] and 0 < max(abs(p[i] - q[i]) for i in range(3)) <= NEAR:
                            near += 1
        if model and len(cols) >= 5:
            noisy += 1
    r = {"file": path, "model": model, "size": [w, h], "faces": faces, "pixels": total,
         "speck": speck, "speck_ratio": round(speck / total, 5) if total else 0,
         "pinhole": pinhole, "semi_alpha": semi,
         "semi_alpha_ratio": round(semi / total, 5) if total else 0,
         "near_dup_ratio": round(near / total, 4) if total else 0,
         "noisy_face_ratio": round(noisy / faces, 4) if (model and faces) else 0,
         "examples": where}
    fails = [k for k in ("speck_ratio", "pinhole", "semi_alpha_ratio", "near_dup_ratio", "noisy_face_ratio")
             if r[k] > LIMITS[k]]
    r["fails"] = fails
    r["pass"] = not fails
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", nargs="+")
    ap.add_argument("--model")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = [check(p, a.model) for p in a.png]
    for r in out:
        print(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['file']} speck={r['speck']}({r['speck_ratio']}) "
              f"pinhole={r['pinhole']} semi_alpha={r['semi_alpha']} near_dup={r['near_dup_ratio']} "
              f"noisy_face={r['noisy_face_ratio']} {('-> ' + ','.join(r['fails'])) if r['fails'] else ''}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"pass": all(r["pass"] for r in out), "limits": LIMITS, "files": out},
                      f, ensure_ascii=False, indent=2)
    sys.exit(0 if all(r["pass"] for r in out) else 1)


if __name__ == "__main__":
    main()
