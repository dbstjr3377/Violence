#!/usr/bin/env python3
"""소음기 우지: 루프 최종 우지(gen.py, snap_12)에 소음기만 끼움 (루프 없음). 모델 작업은 블록벤치 MCP.
총구 (8, 9.5, 24.0) — 기존 팩 silenced_uzi 와 같은 자리(축소 전 좌표)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
import gen  # noqa: E402  (우지 부품이 gen.b 에 이미 들어 있음)
from bbkit import atlas, build_bbmodel, export_java, validate, render_views  # noqa: E402

b = gen.b
PAL = dict(gen.PAL, sil=(36, 37, 40), sil_d=(26, 26, 28))
# 소음기: 팔각 원통 몸통 + 뒤 고정 칼라 + 앞 마개 + 몸통 홈 2줄 + 총구 구멍
b.oct("z", 8.0, 9.5, 1.02, 14.7, 15.25, "steel_b", name="sil_collar")
b.oct("z", 8.0, 9.5, 0.95, 15.2, 23.65, "sil", name="silencer")
for z in (17.6, 21.3):
    b.oct("z", 8.0, 9.5, 0.98, z, z + 0.18, "sil_d", name="sil_groove")
b.oct("z", 8.0, 9.5, 1.0, 23.6, 24.0, "steel_b", name="sil_cap")
b.oct("z", 8.0, 9.5, 0.25, 23.98, 24.02, "bore", name="sil_bore")


def build(out_dir=os.path.join(HERE, "out_silenced"), render_dir=None):
    os.makedirs(out_dir, exist_ok=True)
    img, uvs = atlas(b.parts, PAL, density=2, style="tacz2", step=14, topline=("steel", "steel_t"))
    png = os.path.join(out_dir, "silenced_uzi.png"); img.save(png)
    bb = os.path.join(out_dir, "silenced_uzi.bbmodel")
    build_bbmodel(bb, "silenced_uzi", b.parts, png, uvs, "silenced_uzi")
    print(validate(bb)[:300])
    export_java(bb, os.path.join(out_dir, "silenced_uzi.json"))
    if render_dir:
        print(render_views(bb, render_dir, "silenced"))
    print(f"parts={len(b.parts)} tex={img.size}")


if __name__ == "__main__":
    build(render_dir=sys.argv[1] if len(sys.argv) > 1 else None)
