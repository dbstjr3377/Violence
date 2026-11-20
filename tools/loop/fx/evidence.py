#!/usr/bin/env python3
"""총구 화염·탄 궤적 심사 자료: 1인칭 사격 프레임(실제 리소스팩) + 3인칭 화염/궤적을 화면에 놓은 모습.
python3 tools/loop/fx/evidence.py <출력 폴더> <회차>"""
import json, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fp_gallery as G, fp_sim  # noqa: E402
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")


def fx_view(model, disp, label):
    m = json.load(open(os.path.join(NS, "models", "fx", model + ".json")))
    tex = Image.open(os.path.join(NS, "textures", "fx", model + ".png")).convert("RGBA")
    img = fp_sim.background(); d = ImageDraw.Draw(img); items = []
    for dp in disp:
        fp_sim.render_items(items, m, tex, dp, hand=(0, 0, 0))
    items.sort(key=lambda t: t[0])
    for _, vq, col in items:
        d.polygon([fp_sim.project(v) for v in vq], fill=col)
    d.rectangle([0, 0, fp_sim.W, 40], fill=(0, 0, 0)); d.text((14, 6), label, font=G.ImageFont.truetype(G.FONT, 24), fill=(255, 220, 90))
    return img


def main(outdir, n):
    os.makedirs(outdir, exist_ok=True)
    guns = ["m16", "magnum", "shotgun", "silenced_pistol", "uzi", "mp5"]
    tiles = [G.view(g + "_fp_fire", f"1인칭 사격 순간 (화염 프레임): {g}").resize((640, 360), Image.LANCZOS) for g in guns]
    sh = Image.new("RGB", (1920, 720))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % 3) * 640, (i // 3) * 360))
    sh.save(os.path.join(outdir, f"r{n}_fp_flash.png"))
    # 3인칭: 다른 사람이 쏠 때 — 화염 판(빌보드)과 탄 궤적(늘인 줄기)을 3블록 앞 옆쪽에서 본 모습
    def disp(t, s, r=(0, 0, 0)):
        return {"rotation": list(r), "translation": [t[0] * 16, t[1] * 16, t[2] * 16], "scale": list(s)}
    a = fx_view("muzzle", [disp((-0.6, 0.0, -3.0), (0.42, 0.42, 0.42))], "3인칭 총구 화염 (다른 사람이 쏠 때, 3블록 앞)")
    b = fx_view("tracer", [disp((0.4, -0.2, -6.0), (0.055, 0.055, 4.0), (0, -70, 0))], "탄 궤적 (4블록 줄기, 옆에서)")
    c = fx_view("tracer", [disp((0.25, -0.15, -5.0), (0.055, 0.055, 4.0), (0, -20, 0))], "탄 궤적 (쏜 사람 시선 근처)")
    d = fx_view("tracer_orange", [disp((0.4, -0.2, -6.0), (0.07, 0.07, 4.0), (0, -70, 0))], "매그넘 탄 궤적 (주황)")
    sh2 = Image.new("RGB", (1280, 720))
    for i, t in enumerate((a, b, c, d)):
        sh2.paste(t.resize((640, 360), Image.LANCZOS), ((i % 2) * 640, (i // 2) * 360))
    sh2.save(os.path.join(outdir, f"r{n}_world_fx.png"))
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
