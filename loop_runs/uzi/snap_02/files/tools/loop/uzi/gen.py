#!/usr/bin/env python3
"""우지 (루프 제작물, 블록벤치 MCP 로 생성). TACZ풍: 얇은 판·45° 깎기·팔각 원통, 면 단색 + 면 방향 명암.

좌표(기존 팩과 동일): 총구 +Z, 위 +Y, 중심 x=8. 그립 손 (8,5,8.4), 앞손 (8,7.1,12.2), 총구 (8,9.5,17.6).
실행: python3 tools/loop/uzi/gen.py  → out/uzi.bbmodel (블록벤치 MCP), out/uzi.png, out/uzi.json (MCP 내보내기)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from bbkit import Builder, Xf, atlas, build_bbmodel, export_java, validate, render_views  # noqa: E402

PAL = {
    "steel":   (58, 61, 66),    # 파커라이징 강철 (리시버)
    "steel_d": (42, 44, 48),    # 눌러 찍은 홈·그늘
    "steel_l": (88, 92, 98),    # 핀·노브 끝·마모
    "poly":    (34, 34, 36),    # 폴리머 그립·앞손잡이
    "poly_d":  (24, 24, 26),
    "bore":    (12, 12, 13),
    "mag":     (50, 52, 56),
}

b = Builder()
X0, X1 = 7.1, 8.9                     # 리시버 폭
# ── 리시버 (프레스 강판 상자) ──
b.chamfer_box([X0, 8.0, 3.0], [X1, 11.0, 14.0], 0.177, "steel", name="receiver")
for sx in (-1, 1):                      # 옆면 프레스 리브 2줄: 0.18 돌출 + 45° 깎은 모서리
    xa = X0 - 0.18 if sx < 0 else X1
    for y0 in (8.75, 10.05):
        z0, z1 = (4.3, 12.7) if not (sx > 0 and y0 > 10) else (4.3, 7.6)   # 오른쪽 윗 리브는 배출구 앞에서 끊김
        b.chamfer_box([xa, y0, z0], [xa + 0.18, y0 + 0.42, z1], 0.07, "steel", name="press_rib", edges="z")
        if sx > 0 and y0 > 10:
            b.chamfer_box([xa, y0, 11.0], [xa + 0.18, y0 + 0.42, 12.7], 0.07, "steel", name="press_rib", edges="z")
# 오른쪽 탄피 배출구: 둘레 테 (돌출) + 안쪽 어두운 창 + 노리쇠 면
b.put([X1, 9.45, 7.75], [X1 + 0.12, 9.6, 10.85], "steel", name="port_rim")
b.put([X1, 10.8, 7.75], [X1 + 0.12, 10.95, 10.85], "steel", name="port_rim")
b.put([X1, 9.45, 7.75], [X1 + 0.12, 10.95, 7.9], "steel", name="port_rim")
b.put([X1, 9.45, 10.7], [X1 + 0.12, 10.95, 10.85], "steel", name="port_rim")
b.put([X1 - 0.35, 9.6, 7.9], [X1 + 0.01, 10.8, 10.7], "bore", name="ejection_port")
b.put([X1 - 0.3, 9.75, 8.3], [X1 - 0.05, 10.65, 9.6], "steel_l", name="bolt_face")
# ── 윗덮개 + 장전 손잡이 ──
b.chamfer_box([7.3, 11.0, 3.3], [8.7, 11.45, 13.7], 0.12, "steel", name="top_cover")
for x in (7.5, 8.35):
    b.put([x, 11.45, 4.6], [x + 0.15, 11.6, 12.4], "steel_d", name="cover_rib")
b.oct("y", 8.0, 10.9, 0.3, 11.45, 12.05, "steel", name="cocking_knob")
b.oct("y", 8.0, 10.9, 0.34, 11.95, 12.2, "steel_l", name="cocking_knob_cap")
# ── 가늠자 / 가늠쇠 ──
b.chamfer_box([7.4, 11.45, 3.55], [8.6, 12.0, 4.35], 0.1, "steel", name="rear_sight")
for x in (7.4, 8.4):
    b.chamfer_box([x, 12.0, 3.6], [x + 0.2, 12.45, 4.3], 0.06, "steel", name="rear_sight_ear")
b.chamfer_box([7.35, 11.0, 13.0], [8.65, 11.6, 13.75], 0.1, "steel", name="front_sight_base")
for x in (7.35, 8.45):
    b.chamfer_box([x, 11.6, 13.05], [x + 0.2, 12.5, 13.7], 0.06, "steel", name="front_sight_ear")
b.put([7.92, 11.6, 13.25], [8.08, 12.3, 13.45], "steel_l", name="front_sight_post")
# ── 총열 너트 + 총열 ──
b.oct("z", 8.0, 9.5, 0.85, 14.0, 14.75, "steel", name="barrel_nut")
for k in range(8):                    # 너트 미끄럼 방지 홈
    import math
    a = k * 45 + 22.5
    b.put([7.96, 9.5 + 0.8, 14.1], [8.04, 9.5 + 0.88, 14.65], "steel_d", Xf.rot("z", a, (8, 9.5, 0)), name="nut_knurl")
b.oct("z", 8.0, 9.5, 0.42, 14.75, 17.6, "steel", name="barrel")
b.oct("z", 8.0, 9.5, 0.22, 17.58, 17.62, "bore", name="muzzle_bore")
# ── 그립 겸 탄창집 ──
b.chamfer_box([7.2, 2.2, 7.0], [8.8, 7.95, 9.8], 0.177, "poly", name="grip")
for sx in (-1, 1):                      # 그립 판: 돌출 패널 + 가로 미끄럼 방지 마디 (마디 사이가 홈)
    xa = 7.2 - 0.12 if sx < 0 else 8.8
    b.chamfer_box([xa, 2.6, 7.3], [xa + 0.12, 7.3, 9.5], 0.05, "poly", name="grip_panel", edges="y")
    xb = xa - 0.1 if sx < 0 else xa + 0.12
    for y in (3.0, 3.65, 4.3, 4.95, 5.6, 6.25):
        b.chamfer_box([xb, y, 7.45], [xb + 0.1, y + 0.32, 9.35], 0.045, "poly", name="grip_rib", edges="z")
b.chamfer_box([7.15, 7.5, 6.6], [8.85, 7.95, 10.2], 0.1, "poly", name="grip_cap")
b.chamfer_box([7.6, 4.6, 6.55], [8.4, 7.35, 7.05], 0.08, "steel", name="grip_safety")
# ── 탄창 + 바닥판 ──
b.chamfer_box([7.45, -1.6, 7.4], [8.55, 2.25, 9.4], 0.1, "mag", name="magazine")
for x in (7.42, 8.55):
    b.put([x, -1.4, 8.25], [x + 0.03, 2.1, 8.55], "steel_d", name="mag_rib")
b.chamfer_box([7.3, -2.05, 7.2], [8.7, -1.6, 9.6], 0.1, "steel", name="mag_floor")
# ── 방아쇠울 + 방아쇠 ──
# 방아쇠울: 두께 0.35 고리. 아래 막대 → 22.5° 두 번 꺾여 앞 기둥으로 (둥근 앞 모서리)
GT = 0.35
b.chamfer_box([7.55, 5.6, 9.75], [8.45, 5.6 + GT, 11.6], 0.08, "steel", name="guard_bottom", edges="z")
gx = Xf.rot("x", -22.5, (8, 5.6 + GT / 2, 11.6))
b.chamfer_box([7.55, 5.6, 11.5], [8.45, 5.6 + GT, 12.25], 0.08, "steel", gx, name="guard_bend")
gx2 = Xf.rot("x", -67.5, (8, 5.6 + GT / 2, 11.6))
b.chamfer_box([7.55, 5.6, 11.9], [8.45, 5.6 + GT, 12.55], 0.08, "steel", gx2, name="guard_bend")
b.chamfer_box([7.55, 6.35, 12.25], [8.45, 7.95, 12.25 + GT], 0.08, "steel", name="guard_front", edges="y")
# 방아쇠: 위는 곧고 아래로 갈수록 뒤로 굽음 (판 2장)
b.chamfer_box([7.86, 6.95, 10.3], [8.14, 7.95, 10.58], 0.05, "steel_l", name="trigger")
b.chamfer_box([7.86, 6.3, 10.3], [8.14, 7.0, 10.56], 0.05, "steel_l", Xf.rot("x", 25, (8, 7.0, 10.44)), name="trigger")
# ── 앞손잡이 (폴리머) ──
b.chamfer_box([7.05, 7.05, 12.7], [8.95, 8.05, 13.95], 0.15, "poly", name="forend")
b.chamfer_box([7.05, 7.3, 10.4], [8.95, 8.05, 12.7], 0.12, "poly", name="forend_rear")
# ── 조정간 (왼쪽) ──
b.oct("x", 7.4, 7.7, 0.28, 6.98, 7.12, "steel", name="selector_hub")
b.put([6.98, 7.25, 7.6], [7.06, 7.55, 8.55], "steel_l", Xf.rot("x", -20, (7.0, 7.4, 7.7)), name="selector_lever")
# ── 접이식 개머리판 (접힘) ──
# 접이식 개머리판: 뒤쪽 경첩에서 리시버 아래로 앞을 향해 접힘, 개머리 판은 앞손잡이 아래
b.chamfer_box([7.3, 7.35, 2.55], [8.7, 8.25, 3.35], 0.12, "steel", name="stock_hinge_block")
b.oct("x", 7.8, 2.95, 0.3, 6.98, 9.02, "steel_l", name="stock_hinge")
for x0 in (6.85, 8.8):                  # 양쪽 지지대 (리시버 바깥으로 얇게)
    b.chamfer_box([x0, 7.45, 2.6], [x0 + 0.35, 7.85, 12.2], 0.08, "steel", name="stock_arm", edges="z")
b.chamfer_box([6.85, 6.55, 12.0], [9.15, 7.85, 12.45], 0.12, "steel", name="stock_butt")
b.chamfer_box([6.95, 6.3, 12.05], [9.05, 6.6, 12.4], 0.08, "poly", name="stock_butt_pad")
# ── 핀 (팔각) ──
for (y, z) in ((9.0, 5.0), (9.0, 12.4), (8.4, 7.6)):
    b.oct("x", y, z, 0.16, X0 - 0.06, X1 + 0.06, "steel_l", name="pin")


def build(out_dir=os.path.join(HERE, "out"), render_dir=None, stem="uzi"):
    os.makedirs(out_dir, exist_ok=True)
    img, uvs = atlas(b.parts, PAL)
    png = os.path.join(out_dir, "uzi.png"); img.save(png)
    bb = os.path.join(out_dir, "uzi.bbmodel")
    build_bbmodel(bb, "uzi", b.parts, png, uvs, "uzi")
    print(validate(bb)[:600])
    export_java(bb, os.path.join(out_dir, "uzi.json"))
    if render_dir:
        print(render_views(bb, render_dir, stem))
    print(f"parts={len(b.parts)} tex={img.size}")


if __name__ == "__main__":
    build(render_dir=sys.argv[1] if len(sys.argv) > 1 else None, stem=sys.argv[2] if len(sys.argv) > 2 else "uzi")
