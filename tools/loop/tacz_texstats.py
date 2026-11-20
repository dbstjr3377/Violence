#!/usr/bin/env python3
"""TACZ풍 텍스처 수치 검사 (docs/TACZ_STYLE.md 2판 B 표).

사용: python3 tools/loop/tacz_texstats.py --model <Java 모델.json> <텍스처.png> [--json out.json]
      python3 tools/loop/tacz_texstats.py --geo <베드락 geo.json> <텍스처.png>   (TACZ 원본 비교용)
4×4텍셀 이상 큰 면만 잰다: 단색 비율, 색 수, 그라데이션 폭, 그라데이션 뺀 얼룩, 윗줄 밝음, 텍셀 밀도, 평균 V, 면끼리 명도 대비.
통과: 5개 검사 중 1개까지 어긋나도 됨 (TACZ 원본 71정 중 61정 통과, 1판 기준으로 만든 우지·소방도끼는 3~4개 어긋나 불합격).
"""
import argparse, json, math, statistics as st, sys
from PIL import Image


def _V(p):
    return max(p[:3]) / 255


def rects_java(m, W, H):
    out = []
    for e in m["elements"]:
        for f, fv in (e.get("faces") or {}).items():
            u0, v0, u1, v1 = fv["uv"]
            x0, x1 = sorted((u0 * W / 16, u1 * W / 16)); y0, y1 = sorted((v0 * H / 16, v1 * H / 16))
            fr, to = e["from"], e["to"]
            dims = {"north": (to[0] - fr[0], to[1] - fr[1]), "south": (to[0] - fr[0], to[1] - fr[1]),
                    "east": (to[2] - fr[2], to[1] - fr[1]), "west": (to[2] - fr[2], to[1] - fr[1]),
                    "up": (to[0] - fr[0], to[2] - fr[2]), "down": (to[0] - fr[0], to[2] - fr[2])}[f]
            out.append((f, x0, y0, x1, y1, dims))
    return out


def rects_geo(g, W, H):
    k = W / g["description"]["texture_width"]
    out = []
    for b in g["bones"]:
        if b["name"].lower() in ("lefthand", "righthand"):
            continue
        for c in b.get("cubes", []):
            if not isinstance(c.get("uv"), dict):
                continue
            sx, sy, sz = c["size"]
            for f, fv in c["uv"].items():
                (u, v), (us, vs) = fv["uv"], fv["uv_size"]
                x0, x1 = sorted((u * k, (u + us) * k)); y0, y1 = sorted((v * k, (v + vs) * k))
                dims = {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}[f]
                out.append((f, x0, y0, x1, y1, dims))
    return out


def stats(rects, im):
    W, H = im.size; px = im.load()
    big = 0; flat = 0; ncol = []; spans = []; res = []; topline = 0; dens = []; fmeans = []
    for f, x0, y0, x1, y1, dims in rects:
        if dims[0] >= 1 and x1 - x0 >= 1:
            dens.append((x1 - x0) / dims[0])
        xa, ya, xb, yb = int(math.floor(x0 + 1e-6)), int(math.floor(y0 + 1e-6)), int(math.ceil(x1 - 1e-6)), int(math.ceil(y1 - 1e-6))
        if xb - xa < 4 or yb - ya < 4:
            continue
        grid = [[px[min(x, W - 1), min(y, H - 1)] for x in range(xa, xb)] for y in range(ya, yb)]
        if all(p[3] == 0 for r in grid for p in r):
            continue
        big += 1
        fmeans.append(st.mean(_V(p) for r in grid for p in r if p[3]))
        cols = set(p[:3] for r in grid for p in r if p[3]); ncol.append(len(cols))
        if len(cols) == 1:
            flat += 1
        vals = [[_V(p) for p in r] for r in grid]
        h, w = len(vals), len(vals[0])
        pts = [(i, j, vals[j][i]) for j in range(h) for i in range(w)]
        mx = (w - 1) / 2; my = (h - 1) / 2; mv = st.mean(p[2] for p in pts)
        sxx = sum((p[0] - mx) ** 2 for p in pts) or 1; syy = sum((p[1] - my) ** 2 for p in pts) or 1
        a = sum((p[0] - mx) * (p[2] - mv) for p in pts) / sxx; b = sum((p[1] - my) * (p[2] - mv) for p in pts) / syy
        spans.append(max(abs(a) * (w - 1), abs(b) * (h - 1)))
        res.append(st.pstdev([p[2] - (mv + a * (p[0] - mx) + b * (p[1] - my)) for p in pts]))
        inner = [x for r in vals[1:-1] for x in r[1:-1]]
        if inner and st.mean(vals[0]) > st.mean(inner) + 0.04:
            topline += 1
    allpx = [p for p in (im.getpixel((x, y)) for y in range(H) for x in range(W)) if p[3]]
    r = {"big_faces": big, "flat_ratio": round(flat / big, 3) if big else None,
         "colors_median": st.median(ncol) if ncol else None,
         "gradient_span_median": round(st.median(spans), 3) if spans else None,
         "mottle_std_median": round(st.median(res), 4) if res else None,
         "topline_ratio": round(topline / big, 3) if big else None,
         "texel_per_px_median": round(st.median(dens), 2) if dens else None,
         "face_contrast": round(st.pstdev(fmeans), 3) if len(fmeans) > 1 else None,
         "mean_V": round(st.mean(_V(p) for p in allpx), 3) if allpx else None}
    # TACZ 기본 건팩 71정 분포의 p10~p90 (docs/TACZ_STYLE.md 2판)
    checks = {
        "flat_ratio<=0.62": r["flat_ratio"] is not None and r["flat_ratio"] <= 0.62,
        "mottle>=0.01 or gradient>=0.02": (r["mottle_std_median"] or 0) >= 0.01 or (r["gradient_span_median"] or 0) >= 0.02,
        "topline 0.05~0.37": r["topline_ratio"] is not None and 0.05 <= r["topline_ratio"] <= 0.37,
        "texel/px 1.5~4.5": r["texel_per_px_median"] is not None and 1.5 <= r["texel_per_px_median"] <= 4.5,
        "mean_V 0.2~0.39": r["mean_V"] is not None and 0.2 <= r["mean_V"] <= 0.39,
    }
    r["checks"] = checks
    r["fails"] = sum(1 for v in checks.values() if not v)
    r["pass"] = r["fails"] <= 1          # TACZ 71정 중 61정(86%)이 통과하는 선
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--model"); g.add_argument("--geo")
    ap.add_argument("--json")
    a = ap.parse_args()
    im = Image.open(a.png).convert("RGBA")
    if a.model:
        rects = rects_java(json.load(open(a.model, encoding="utf-8")), *im.size)
    else:
        rects = rects_geo(json.load(open(a.geo, encoding="utf-8"))["minecraft:geometry"][0], *im.size)
    r = stats(rects, im)
    print(json.dumps(r, ensure_ascii=False))
    if a.json:
        json.dump(r, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    sys.exit(0 if r["pass"] else 1)


if __name__ == "__main__":
    main()
