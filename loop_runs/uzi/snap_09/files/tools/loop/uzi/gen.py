#!/usr/bin/env python3
"""우지 (루프 제작물, 블록벤치 MCP 로 생성). TACZ풍: 얇은 판·45° 깎기·팔각 원통, 면 단색 + 면 방향 명암.

좌표(기존 팩과 동일): 총구 +Z, 위 +Y, 중심 x=8. 그립 손 (8,5,8.4), 앞손 (8,7.1,12.2), 총구 (8,9.5,17.6).
실행: python3 tools/loop/uzi/gen.py  → out/uzi.bbmodel (블록벤치 MCP), out/uzi.png, out/uzi.json (MCP 내보내기)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from bbkit import Builder, Xf, atlas, build_bbmodel, export_java, validate, render_views  # noqa: E402

PAL = {                         # 검은 회색 + 부품별 명도 단계 (그립·탄창 어둡게 / 리시버 중간 / 총열·가늠자 밝게)
    "steel":   (50, 51, 55),    # 리시버
    "steel_t": (54, 55, 59),    # 윗덮개
    "steel_b": (70, 72, 76),    # 총열 너트·가늠자쇠·방아쇠울 (밝은 단)
    "steel_d": (24, 24, 26),    # 홈·이음선
    "steel_l": (92, 94, 99),    # 핀·노브
    "poly":    (26, 26, 28),    # 폴리머 그립·앞손잡이 (가장 어두운 단)
    "poly_d":  (16, 16, 17),
    "bore":    (8, 8, 9),
    "mag":     (42, 43, 46),
    "polish":  (110, 113, 119), # 연마 금속 (총구 끝·장전 손잡이 머리·방아쇠)
    "brass":   (150, 118, 52),  # 포인트: 그립 황동 띠
    "sight_g": (70, 190, 90),   # 포인트: 가늠쇠 초록 점
}

SCALE, PIVOT = 0.75, (8, 5.0, 8.4)     # 그립 손 자리 기준 0.75배 (길이 ~12px). 팩 적용 시 손·총구 좌표도 같은 변환
b = Builder(SCALE, PIVOT)
X0, X1 = 7.1, 8.9                     # 리시버 폭
# ── 리시버 (프레스 강판 상자) ──
b.chamfer_box([X0, 8.0, 1.6], [X1, 11.0, 14.0], 0.177, "steel", name="receiver")   # 뒤로 길게 (높이:길이 ≈0.65)
for sx in (-1, 1):                      # 옆면 프레스 리브 2줄: 0.18 돌출 + 45° 깎은 모서리
    xa = X0 - 0.18 if sx < 0 else X1
    for y0 in (8.75, 10.05):
        z0, z1 = (2.8, 12.7) if not (sx > 0 and y0 > 10) else (2.8, 7.6)   # 오른쪽 윗 리브는 배출구 앞에서 끊김
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
b.chamfer_box([7.3, 11.0, 1.9], [8.7, 11.45, 13.7], 0.12, "steel_t", name="top_cover")
for x in (7.42, 8.28):                  # 윗덮개 프레스 리브: 납작하게 붙은 돌출
    b.chamfer_box([x, 11.45, 3.2], [x + 0.3, 11.58, 12.4], 0.05, "steel_t", name="cover_rib", edges="z")
b.oct("y", 8.0, 10.9, 0.3, 11.45, 12.05, "steel", name="cocking_knob")
b.oct("y", 8.0, 10.9, 0.34, 11.95, 12.2, "polish", name="cocking_knob_cap")
# 윗덮개 분할선 (앞 1/3 지점 홈) + 앞뒤 경첩 귀
b.put([7.28, 11.05, 9.3], [8.72, 11.47, 9.42], "steel_d", name="cover_split")
for z in (2.05, 13.3):
    b.chamfer_box([7.2, 10.75, z], [8.8, 11.2, z + 0.3], 0.06, "steel", name="cover_hinge")
# ── 가늠자 / 가늠쇠 ──
b.chamfer_box([7.4, 11.45, 2.15], [8.6, 12.0, 2.95], 0.1, "steel_b", name="rear_sight")
for x in (7.4, 8.4):
    b.chamfer_box([x, 12.0, 2.2], [x + 0.2, 12.45, 2.9], 0.06, "steel", name="rear_sight_ear")
b.chamfer_box([7.35, 11.0, 13.0], [8.65, 11.6, 13.75], 0.1, "steel_b", name="front_sight_base")
for x in (7.35, 8.45):
    b.chamfer_box([x, 11.6, 13.05], [x + 0.2, 12.5, 13.7], 0.06, "steel", name="front_sight_ear")
b.chamfer_box([7.35, 12.5, 13.1], [8.65, 12.7, 13.65], 0.06, "steel", name="front_sight_hood")   # 보호 후드 (두 귀를 잇는 다리)
b.put([7.92, 11.6, 13.25], [8.08, 12.3, 13.45], "steel_l", name="front_sight_post")
b.put([7.9, 12.18, 13.22], [8.1, 12.34, 13.48], "sight_g", name="front_sight_dot")      # 포인트 색
# ── 총열 너트 + 총열 ──
b.oct("z", 8.0, 9.5, 0.85, 14.0, 14.3, "steel_b", name="barrel_nut")
b.oct("z", 8.0, 9.5, 0.78, 14.3, 14.45, "steel_d", name="barrel_nut_groove")
b.oct("z", 8.0, 9.5, 0.85, 14.45, 14.75, "steel_b", name="barrel_nut")
b.oct("z", 8.0, 9.5, 0.42, 14.75, 17.2, "steel_b", name="barrel")
b.oct("z", 8.0, 9.5, 0.42, 17.2, 17.6, "polish", name="barrel_crown")
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
b.chamfer_box([7.4, 4.6, 6.8], [8.6, 7.4, 7.45], 0.08, "steel_b", name="grip_safety")   # 손잡이 뒷면에 박힘 (0.45 겹침)
for sx in (-1, 1):                      # 그립 위쪽 황동 띠 (포인트 색)
    xa = 7.2 - 0.14 if sx < 0 else 8.8
    b.put([xa, 7.0, 7.4], [xa + 0.14, 7.3, 9.4], "brass", name="grip_band")
# ── 탄창 + 바닥판 ──
b.chamfer_box([7.45, 0.45, 7.4], [8.55, 2.25, 9.4], 0.1, "mag", name="magazine")   # 손잡이 아래로 짧게만 노출
for x in (7.35, 8.55):
    b.chamfer_box([x, 0.6, 8.2], [x + 0.1, 2.15, 8.6], 0.04, "mag", name="mag_rib", edges="y")
b.chamfer_box([7.3, 0.0, 7.2], [8.7, 0.45, 9.6], 0.1, "steel", name="mag_floor")
# ── 방아쇠울 + 방아쇠 ──
# 방아쇠울: 둥근 고리 — 아래판 → 22.5° 씩 꺾인 판 3장(반지름 0.75 호) → 앞기둥. 하부 프레임과 같은 폴리머
GT, GZ, GY, GR = 0.34, 11.75, 6.6, 0.75          # 두께, 호 중심 z·y, 반지름
b.chamfer_box([7.3, GY - GR - GT / 2, 9.7], [8.7, GY - GR + GT / 2, GZ + 0.02], 0.09, "poly", name="guard_bottom", edges="z")
for k, ang in enumerate((22.5, 45, 67.5)):
    seg = 2 * GR * 0.2 + 0.08                       # 호 한 칸 길이(22.5°) + 겹침
    xf = Xf.rot("x", -ang, (8, GY, GZ))
    b.chamfer_box([7.3, GY - GR - GT / 2, GZ - seg / 2], [8.7, GY - GR + GT / 2, GZ + seg / 2], 0.09, "poly", xf, name="guard_arc", edges="z")
b.chamfer_box([7.3, GY - 0.02, GZ + GR - GT / 2], [8.7, 7.95, GZ + GR + GT / 2], 0.09, "poly", name="guard_front", edges="y")
# 방아쇠: 위는 곧고 아래로 갈수록 뒤로 굽음 (판 2장)
b.chamfer_box([7.86, 6.95, 10.3], [8.14, 7.95, 10.58], 0.05, "polish", name="trigger")
b.chamfer_box([7.86, 6.4, 10.3], [8.14, 7.0, 10.56], 0.05, "polish", Xf.rot("x", 25, (8, 7.0, 10.44)), name="trigger")
# ── 앞손잡이 (폴리머) ──
b.chamfer_box([7.05, 7.05, 12.7], [8.95, 8.05, 13.95], 0.15, "poly", name="forend")
b.chamfer_box([7.05, 7.3, 10.4], [8.95, 8.05, 12.7], 0.12, "poly", name="forend_rear")
# ── 조정간 (왼쪽) ──
b.oct("x", 7.4, 7.7, 0.28, 6.98, 7.12, "steel", name="selector_hub")
b.put([6.98, 7.25, 7.6], [7.06, 7.55, 8.55], "steel_l", Xf.rot("x", -20, (7.0, 7.4, 7.7)), name="selector_lever")
# ── 접이식 개머리판 (접힘) ──
# 리시버 뒤 캡 + 슬링 고리 (뒤·앞)
b.chamfer_box([7.25, 8.15, 1.35], [8.75, 10.85, 1.62], 0.1, "steel_b", name="rear_cap")
for (y, z) in ((8.5, 1.15), (8.3, 14.35)):
    b.oct("x", y, z, 0.26, 7.75, 8.25, "steel_b", name="sling_loop")
    b.oct("x", y, z, 0.12, 7.7, 8.3, "bore", name="sling_hole")
# ── 핀 (팔각) ──
for (y, z) in ((9.0, 5.0), (9.0, 12.4), (8.4, 7.6)):
    b.oct("x", y, z, 0.16, X0 - 0.06, X1 + 0.06, "steel_l", name="pin")


def build(out_dir=os.path.join(HERE, "out"), render_dir=None, stem="uzi"):
    os.makedirs(out_dir, exist_ok=True)
    def seam(p, f, i, j, tw, th):         # 윗덮개 옆면 맨 아래 한 줄 = 리시버와의 판 이음선
        if p.name == "top_cover" and f in ("east", "west", "north", "south") and th >= 2 and j == th - 1:
            return "steel_d"
        return None
    img, uvs = atlas(b.parts, PAL, painter=seam, density=2, style="tacz2", step=10, topline=("steel", "steel_t"))
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
