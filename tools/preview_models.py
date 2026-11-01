#!/usr/bin/env python3
"""무기/가면 모델 미리보기 (등각 투영 소프트웨어 렌더). 결과: build-out/model_preview.png"""
import json
import glob
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack_common import NAMES, PALETTE, NS, ROOT  # noqa: E402

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "blackhansans_BlackHanSans-Regular.ttf")


def color_of(face):
    u, v = face["uv"][0], face["uv"][1]
    idx = int(v // 2) * 8 + int(u // 2)
    return PALETTE[NAMES[idx]] if idx < len(NAMES) else (255, 0, 255)


def project(p, yaw_view):
    x, y, z = p
    # 등각: 위에서 30도, 옆에서 yaw_view
    import math
    c, s = math.cos(yaw_view), math.sin(yaw_view)
    rx, rz = x * c - z * s, x * s + z * c
    return (rx * 0.9, -y - rz * 0.45), rz


def render(model_path, yaw_view, size=150):
    with open(model_path, encoding="utf-8") as f:
        m = json.load(f)
    polys = []
    for e in m.get("elements", []):
        (x0, y0, z0), (x1, y1, z1) = e["from"], e["to"]
        col = color_of(next(iter(e["faces"].values())))
        corners = {
            "up": [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
            "north": [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
            "south": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            "east": [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)],
            "west": [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
        }
        shade = {"up": 1.0, "north": 0.8, "south": 0.8, "east": 0.62, "west": 0.62}
        for face, pts in corners.items():
            proj = [project(p, yaw_view) for p in pts]
            depth = sum(d for _, d in proj) / 4 + (0.01 if face == "up" else 0)
            k = shade[face]
            polys.append((depth, [pt for pt, _ in proj], tuple(int(c * k) for c in col)))
    polys.sort(key=lambda t: -t[0])
    allpts = [p for _, pts, _ in polys for p in pts] or [(0, 0)]
    minx, maxx = min(p[0] for p in allpts), max(p[0] for p in allpts)
    miny, maxy = min(p[1] for p in allpts), max(p[1] for p in allpts)
    scale = (size - 20) / max(maxx - minx, maxy - miny, 1)
    img = Image.new("RGB", (size, size), (34, 30, 40))
    d = ImageDraw.Draw(img)
    ox = size / 2 - (minx + maxx) / 2 * scale
    oy = size / 2 - (miny + maxy) / 2 * scale
    for _, pts, col in polys:
        d.polygon([(ox + x * scale, oy + y * scale) for x, y in pts], fill=col, outline=tuple(max(0, c - 40) for c in col))
    return img


def sheet(paths, yaw, cols, title, out):
    size = 150
    rows = (len(paths) + cols - 1) // cols
    img = Image.new("RGB", (cols * size, rows * (size + 18) + 30), (20, 16, 26))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 14)
    d.text((8, 6), title, font=f, fill=(255, 90, 160))
    for i, p in enumerate(paths):
        tile = render(p, yaw, size)
        x, y = (i % cols) * size, (i // cols) * (size + 18) + 30
        img.paste(tile, (x, y))
        d.text((x + 6, y + size + 1), os.path.basename(p)[:-5], font=ImageFont.truetype(FONT, 12), fill=(230, 230, 230))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print(out)


if __name__ == "__main__":
    out_dir = os.path.join(ROOT, "build-out")
    weapons = sorted(glob.glob(os.path.join(NS, "models", "item", "weapon", "*.json")))
    masks = sorted(glob.glob(os.path.join(NS, "models", "item", "mask", "*.json")))
    sheet(weapons, 2.3, 8, "무기 모델 (근접 / 총기 / 투척)", os.path.join(out_dir, "weapons_preview.png"))
    sheet(masks, 0.55, 7, "가면 모델 21종 (정면 위에서)", os.path.join(out_dir, "masks_preview.png"))
