#!/usr/bin/env python3
"""가면 21종 미리보기: 정면·3/4·옆 렌더 + 잡티(외톨이 픽셀) 수. python3 tools/mask_preview.py [출력.png]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_sim  # noqa: E402
import mask_kit  # noqa: E402
import masks_v3  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

DISPLAY = {"head": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]}}


def main(out):
    tiles = []
    report = []
    for name, make in masks_v3.MASKS.items():
        model, atlas, placed = mask_kit.build(make(), DISPLAY)
        n, _ = mask_kit.check_speckles(placed)
        report.append((name, n, len(model["elements"]), atlas.width))
        row = []
        for rot in ([8, 180, 0], [12, 215, 0], [6, 270, 0]):
            row.append(fp_sim.turntable(model, atlas, rot, size=220, dist=3.0, bg=(36, 30, 44), scale=1.0))
        im = Image.new("RGB", (660, 236), (20, 18, 24))
        for k, r in enumerate(row):
            im.paste(r, (k * 220, 16))
        ImageDraw.Draw(im).text((4, 2), f"{name}  잡티 {n}  큐브 {len(model['elements'])}", fill=(255, 255, 255))
        tiles.append(im)
    cols = 3
    W = Image.new("RGB", (660 * cols, 236 * ((len(tiles) + cols - 1) // cols)), (0, 0, 0))
    for i, t in enumerate(tiles):
        W.paste(t, ((i % cols) * 660, (i // cols) * 236))
    W.save(out)
    for r in report:
        print(*r)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build-out/masks.png")
