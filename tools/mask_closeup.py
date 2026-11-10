#!/usr/bin/env python3
"""가면 확대 미리보기 (3/4 시점 큰 그림 7x3). python3 tools/mask_closeup.py 출력.png [rotY]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_sim  # noqa: E402
import mask_kit  # noqa: E402
import masks_v3  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

out = sys.argv[1]
ry = float(sys.argv[2]) if len(sys.argv) > 2 else 205
names = sys.argv[3].split(",") if len(sys.argv) > 3 else list(masks_v3.MASKS)
S = 300
tiles = []
for name in names:
    model, atlas, placed = mask_kit.build(masks_v3.MASKS[name](), {})
    im = fp_sim.turntable(model, atlas, [10, ry, 0], size=S, dist=2.2, bg=(40, 34, 50))
    ImageDraw.Draw(im).text((4, 4), name, fill=(255, 255, 255))
    tiles.append(im)
cols = 7
W = Image.new("RGB", (S * cols, S * ((len(tiles) + cols - 1) // cols)))
for i, t in enumerate(tiles):
    W.paste(t, ((i % cols) * S, (i // cols) * S))
W.save(out)
