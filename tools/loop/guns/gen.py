#!/usr/bin/env python3
"""총기 6종 루프 제작물 (블록벤치 MCP 로 생성). docs/TACZ_STYLE.md 2판 기준.
좌표는 기존 팩(tools/models_guns.py)과 같다: 총구 +Z, 위 +Y, 중심 x=8. HAND_POS / MUZZLE 자리를 그대로 지킨다.

사용: python3 tools/loop/guns/gen.py <총> [렌더 폴더] [이름]   총: m16 mp5 shotgun double_barrel magnum silenced_pistol
출력: tools/loop/guns/out/<총>/<총>.bbmodel (블록벤치 MCP) / .png / .json (MCP 내보내기)
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import bbkit  # noqa: E402
from bbkit import Builder, Xf, atlas, build_bbmodel, export_java, validate, render_views  # noqa: E402

# 공용 팔레트 (검은 회색 금속 + 부품별 명도 단계, 포인트 색은 아주 작게)
BASE = {
    "rec":    (50, 51, 55),     # 리시버·프레임 (중간 단)
    "rec_t":  (66, 67, 72),     # 윗면 부품 (한 단 밝게)
    "lo":     (40, 41, 44),     # 아래 프레임
    "steel_b": (92, 94, 100),   # 총열·가늠자·링 (밝은 단)
    "steel_d": (24, 24, 26),    # 홈·이음선
    "steel_l": (110, 112, 118), # 핀·노브
    "poly":   (26, 26, 28),     # 폴리머 손잡이·개머리 (가장 어두운 단)
    "rubber": (18, 18, 19),
    "bore":   (8, 8, 9),
    "mag":    (36, 37, 40),
    "brass":  (150, 118, 52),
    "sight_g": (70, 190, 90),
    "wood":   (96, 56, 34),
    "wood_d": (70, 40, 24),
    "blued":  (40, 42, 50),
    "stain":  (84, 86, 92),     # 스테인리스 (리볼버, 밝지만 V≤0.39 안)
}
TOPLINE = ("rec", "rec_t", "blued")


def grooves_z(b, cx, cy, r, z0, z1, n, mat="steel_d"):
    """원통 둘레 홈 링 (z축)"""
    for k in range(n):
        z = z0 + (z1 - z0) * (k + 0.5) / n
        b.oct("z", cx, cy, r, z - 0.07, z + 0.07, mat, name="groove")


# ───────────────────────── M16 ─────────────────────────
def mag_curve(b, x0, x1, top, z0, z1, segs, mat="mag", floor="poly", ribs=True):
    """곡선 탄창: 위 곧은 마디 + 아래로 갈수록 앞으로 휘는 마디들. 각 마디는 이전 마디 뒤 아래 모서리를 회전 중심으로 삼아 틈 없이 이어진다.
    segs = [(높이, 누적 각도), ...]  첫 마디 각도 0."""
    y = top; pz = z0; py = top; ang0 = 0
    for k, (hgt, ang) in enumerate(segs):
        if k == 0:
            b.chamfer_box([x0, top - hgt, z0], [x1, top, z1], 0.12, mat, name="mag")
            py = top - hgt; pz = z0
        else:
            xf = Xf.rot("x", -ang, (8, py, pz))
            b.chamfer_box([x0, py - hgt, pz], [x1, py + 0.25, pz + (z1 - z0)], 0.12, mat, xf, name="mag_seg")
            r = math.radians(ang)
            pz, py = pz + hgt * math.sin(r), py - hgt * math.cos(r)
            last = (py, pz, ang)
    py, pz, ang = last
    b.chamfer_box([x0 - 0.1, py - 0.45, pz - 0.15], [x1 + 0.1, py + 0.1, pz + (z1 - z0) + 0.15], 0.1, floor,
                  Xf.rot("x", -ang, (8, py, pz)), name="mag_floor")


def m16(b):
    # A2 고정 개머리: 윗선 직선, 아랫선 사선 (덩어리 하나 + 아래 쐐기) — 버퍼 튜브는 안에 숨김
    b.chamfer_box([7.1, 8.0, -7.6], [8.9, 10.35, 2.1], 0.35, "poly", name="stock")
    b.chamfer_box([7.12, 5.6, -7.6], [8.88, 7.9, 1.5], 0.3, "poly", Xf.rot("x", -15, (8, 5.6, -7.6)), name="stock_wedge")
    b.chamfer_box([7.0, 5.4, -8.25], [9.0, 10.6, -7.55], 0.15, "rubber", name="butt_pad")
    # 하부 리시버 + 탄창 삽입구
    b.chamfer_box([7.1, 7.4, 2.0], [8.9, 9.55, 10.6], 0.2, "lo", name="lower")
    b.chamfer_box([7.05, 6.4, 6.9], [8.95, 7.6, 10.4], 0.15, "lo", name="magwell")
    b.chamfer_box([6.98, 7.9, 2.6], [7.12, 8.6, 3.6], 0.04, "steel_l", name="selector")
    b.put([6.97, 8.45, 2.8], [7.0, 8.6, 3.0], "white", name="safe_mark")
    b.chamfer_box([8.88, 8.0, 7.4], [9.25, 8.6, 8.4], 0.08, "steel_l", name="mag_release")
    for (y, z) in ((8.9, 3.1), (8.9, 9.6)):
        b.oct("x", y, z, 0.16, 7.05, 8.95, "steel_l", name="pin")
    # 상부 리시버 + 배출구 덮개 + 탄피받이 + 포워드 어시스트 + 장전 손잡이
    b.chamfer_box([7.2, 9.5, 2.0], [8.8, 11.0, 11.2], 0.22, "rec", name="upper")
    b.put([8.8, 9.75, 5.8], [8.92, 10.65, 8.8], "rec_t", name="port_cover")
    b.chamfer_box([8.75, 9.5, 5.2], [9.3, 10.2, 5.8], 0.08, "rec", name="deflector")
    b.oct("z", 8.95, 10.3, 0.32, 8.3, 9.7, "steel_b", name="forward_assist")
    b.chamfer_box([7.4, 10.6, 1.4], [8.6, 11.0, 2.05], 0.08, "steel_b", name="charging_handle")
    # 운반 손잡이 (옆판 일체) + 가늠자 드럼
    b.chamfer_box([7.4, 10.9, 2.6], [8.6, 12.4, 4.3], 0.2, "rec", name="handle_rear")
    b.chamfer_box([7.45, 10.9, 8.0], [8.55, 12.3, 9.0], 0.15, "rec", name="handle_front")
    b.chamfer_box([7.45, 10.6, 8.6], [8.55, 12.0, 9.6], 0.15, "rec", Xf.rot("x", -35, (8, 12.0, 8.6)), name="handle_slope")
    b.chamfer_box([7.42, 10.95, 4.2], [8.58, 11.35, 8.2], 0.1, "rec", name="handle_rail")
    b.chamfer_box([7.35, 12.25, 2.6], [8.65, 12.95, 9.8], 0.2, "rec_t", name="carry_handle")
    b.oct("x", 12.7, 3.3, 0.38, 7.2, 8.8, "steel_b", name="rear_drum")
    b.chamfer_box([7.6, 12.95, 2.8], [8.4, 13.5, 3.9], 0.08, "rec", name="rear_ears")
    b.put([7.94, 13.1, 2.75], [8.06, 13.35, 2.8], "bore", name="aperture")
    # 권총 손잡이 (22.5° 뒤로, 윗부분이 하부 리시버 안으로) + 방아쇠울(앞뒤 고정) + 방아쇠
    gx = Xf.rot("x", 22.5, (8, 7.4, 4.4))
    b.chamfer_box([7.3, 3.6, 3.4], [8.7, 8.2, 5.3], 0.3, "poly", gx, name="grip")
    b.chamfer_box([7.22, 4.0, 4.3], [8.78, 6.8, 5.0], 0.1, "poly_t", gx, name="grip_ridge")
    b.chamfer_box([7.55, 5.95, 5.1], [8.45, 6.3, 8.1], 0.08, "lo", name="guard")
    b.chamfer_box([7.55, 6.0, 7.75], [8.45, 7.5, 8.1], 0.08, "lo", name="guard_front")
    b.chamfer_box([7.55, 6.0, 4.9], [8.45, 7.5, 5.25], 0.08, "lo", name="guard_back")
    b.chamfer_box([7.86, 6.55, 6.0], [8.14, 7.45, 6.35], 0.05, "steel_l", Xf.rot("x", 12, (8, 7.45, 6.2)), name="trigger")
    # 곡선 탄창 (3마디, 이음매가 붙어 있음)
    mag_curve(b, 7.35, 8.65, 7.0, 7.1, 9.9, [(3.0, 0), (1.6, 11), (1.6, 22)])
    for sx in (7.3, 8.6):
        b.put([sx, 4.4, 7.6], [sx + 0.1, 6.6, 8.0], "steel_d", name="mag_rib")
    # 델타 링 + 둥근 총열덮개 (세로 리브) + 덮개 마개
    b.oct("z", 8.0, 9.5, 1.2, 10.9, 11.5, "steel_b", name="delta_ring")
    b.oct("z", 8.0, 9.5, 1.08, 11.5, 18.6, "poly", name="handguard")
    for k in range(8):
        b.put([7.88, 9.5 + 0.95, 11.7], [8.12, 9.5 + 1.3, 18.4], "poly_t", Xf.rot("z", k * 45 + 22.5, (8, 9.5, 0)), name="hg_rib")
    b.oct("z", 8.0, 9.5, 0.98, 18.6, 19.1, "steel_b", name="hg_cap")
    # A2 삼각 가늠쇠 받침 (뒤 사선 + 앞 수직) + 보호 날개 + 대검 꽂이
    b.oct("z", 8.0, 9.6, 0.62, 19.2, 20.9, "rec", name="fsb_ring")
    b.chamfer_box([7.55, 9.6, 19.0], [8.45, 10.6, 20.9], 0.1, "rec", name="fsb_step1")
    b.chamfer_box([7.58, 10.5, 19.5], [8.42, 11.4, 20.9], 0.1, "rec", name="fsb_step2")
    b.chamfer_box([7.6, 11.3, 19.9], [8.4, 12.2, 20.9], 0.1, "rec", name="fsb_step3")
    for sx in (7.5, 8.32):
        b.chamfer_box([sx, 12.0, 19.75], [sx + 0.18, 13.1, 20.7], 0.04, "rec", name="fs_ear")
    b.put([7.92, 12.2, 20.05], [8.08, 13.0, 20.35], "steel_l", name="fs_post")
    b.put([7.94, 12.95, 20.1], [8.06, 13.05, 20.3], "sight_g", name="fs_dot")
    b.chamfer_box([7.6, 8.3, 20.0], [8.4, 9.1, 20.7], 0.08, "rec", name="bayonet_lug")
    b.chamfer_box([7.8, 8.4, 18.9], [8.2, 9.1, 19.4], 0.06, "steel_b", name="sling_front")
    # 총열 + 새장형 소염기
    b.oct("z", 8.0, 9.6, 0.36, 19.1, 27.0, "steel_b", name="barrel")
    b.oct("z", 8.0, 9.6, 0.52, 27.0, 29.4, "rec", name="flash_hider")
    for k in range(4):
        a = k * 90 + 45
        b.put([7.96, 9.6 + 0.42, 27.4], [8.04, 9.6 + 0.56, 28.9], "bore", Xf.rot("z", a, (8, 9.6, 0)), name="hider_slot")
    b.oct("z", 8.0, 9.6, 0.24, 29.38, 29.42, "bore", name="bore")


# ───────────────────────── MP5 ─────────────────────────
def mp5(b):
    # 둥근 윗면 리시버 + 윗 홈 + 프레스 라인
    b.chamfer_box([7.15, 8.2, 2.0], [8.85, 11.0, 14.6], 0.45, "rec", name="receiver")
    b.chamfer_box([7.35, 10.95, 2.4], [8.65, 11.3, 14.2], 0.12, "rec_t", name="top_rib")
    for sx in (7.1, 8.85):
        b.put([sx, 9.5, 3.0], [sx + 0.06, 9.75, 13.8], "steel_d", name="press_line")
    b.put([8.84, 9.85, 6.6], [8.92, 10.6, 9.4], "bore", name="port")
    for (y0, y1) in ((9.7, 9.85), (10.6, 10.75)):
        b.put([8.8, y0, 6.4], [8.95, y1, 9.6], "rec_t", name="port_rim")
    for z0 in (6.45, 9.4):
        b.put([8.8, 9.7, z0], [8.95, 10.75, z0 + 0.15], "rec_t", name="port_rim")
    for sx in (7.08, 8.86):
        b.put([sx, 8.7, 3.0], [sx + 0.06, 8.9, 13.8], "rec_t", name="press_rib")
    # 드럼 가늠자 (받침 위)
    b.chamfer_box([7.3, 11.2, 2.6], [8.7, 11.75, 3.9], 0.1, "rec", name="drum_base")
    b.oct("x", 12.05, 3.25, 0.6, 7.15, 8.85, "steel_b", name="rear_drum")
    # 장전 튜브 + 앞 받침(총열과 이어짐) + 가늠쇠 링 후드 + 장전 손잡이
    b.oct("z", 8.0, 10.5, 0.55, 14.4, 19.0, "rec", name="cocking_tube")
    b.chamfer_box([7.5, 9.3, 18.0], [8.5, 10.6, 19.0], 0.12, "rec", name="tube_bridge")
    b.chamfer_box([7.25, 10.6, 17.3], [8.75, 11.4, 18.7], 0.15, "rec", name="hood_base")
    for k in range(8):   # 팔각 고리 후드 (가운데 구멍 + 기둥)
        b.put([7.72, 11.95 + 0.62, 17.5], [8.28, 11.95 + 0.82, 18.5], "steel_b", Xf.rot("z", k * 45, (8, 11.95, 0)), name="hood_ring")
    b.put([7.92, 11.3, 17.85], [8.08, 12.0, 18.15], "steel_l", name="fs_post")
    b.chamfer_box([6.55, 10.15, 15.0], [7.5, 10.6, 15.6], 0.08, "steel_l", name="cocking_handle")
    # 핸드가드 (아래 45° 깎음 + 손가락 홈)
    b.chamfer_box([7.0, 7.6, 12.4], [9.0, 10.0, 17.6], 0.45, "poly", name="handguard")
    for z in (13.3, 14.5, 15.7, 16.9):
        b.chamfer_box([6.92, 7.9, z], [9.08, 8.4, z + 0.35], 0.08, "poly_t", name="hg_groove")
    b.chamfer_box([7.2, 7.9, 17.6], [8.8, 9.9, 18.2], 0.15, "poly", name="hg_front")
    # 총열 + 3-러그
    b.oct("z", 8.0, 9.35, 0.4, 18.2, 20.2, "steel_b", name="barrel")
    b.oct("z", 8.0, 9.35, 0.55, 20.2, 21.6, "rec", name="lug")
    for k in range(3):
        b.put([7.94, 9.35 + 0.5, 20.3], [8.06, 9.35 + 0.66, 20.9], "rec", Xf.rot("z", k * 120, (8, 9.35, 0)), name="lug_tab")
    b.oct("z", 8.0, 9.35, 0.24, 21.58, 21.62, "bore", name="bore")
    # 곡선 트리거 하우징 (앞 사선) + 손잡이 + 방아쇠울 + 조정간 (빨강/흰 표시)
    b.chamfer_box([7.2, 6.9, 3.2], [8.8, 8.3, 9.4], 0.2, "poly", name="trigger_group")
    b.chamfer_box([7.22, 7.0, 8.6], [8.78, 8.3, 10.0], 0.2, "poly", Xf.rot("x", -30, (8, 8.3, 9.4)), name="tg_front")
    b.chamfer_box([7.22, 7.6, 1.9], [8.78, 8.4, 3.4], 0.2, "poly", name="tg_back")
    gx = Xf.rot("x", 22.5, (8, 7.2, 4.6))
    b.chamfer_box([7.3, 3.4, 3.6], [8.7, 7.5, 5.5], 0.3, "poly", gx, name="grip")
    for k, y in enumerate((4.0, 4.8, 5.6)):
        b.chamfer_box([7.24, y, 5.25], [8.76, y + 0.35, 5.6], 0.08, "poly_t", gx, name="finger")
    b.chamfer_box([7.55, 6.15, 5.8], [8.45, 6.5, 8.6], 0.08, "poly", name="guard")
    b.chamfer_box([7.55, 6.2, 8.25], [8.45, 7.0, 8.6], 0.08, "poly", name="guard_front")
    b.chamfer_box([7.86, 6.5, 6.4], [8.14, 7.0, 6.75], 0.05, "steel_l", Xf.rot("x", 12, (8, 7.0, 6.6)), name="trigger")
    b.oct("x", 7.75, 3.9, 0.32, 6.95, 7.2, "steel_l", name="selector")
    b.put([6.94, 8.0, 4.4], [6.97, 8.15, 4.6], "red", name="sel_red")
    b.put([6.94, 8.0, 3.2], [6.97, 8.15, 3.4], "white", name="sel_white")
    for z in (3.3, 8.8):
        b.oct("x", 8.0, z, 0.16, 7.15, 8.85, "steel_l", name="pin")
    # 탄창 삽입구 + 곡선 탄창 (앞으로 크게 휨, 4마디)
    b.chamfer_box([7.2, 7.3, 9.7], [8.8, 8.4, 11.7], 0.15, "rec", name="magwell")
    mag_curve(b, 7.35, 8.65, 7.5, 9.9, 11.3, [(1.6, 0), (1.3, 10), (1.3, 20), (1.3, 30)])
    b.chamfer_box([7.4, 8.2, 11.6], [8.6, 8.6, 12.4], 0.08, "steel_b", name="mag_catch")
    # 접이식 개머리 (지지대 2개 + 개머리 판)
    for sx in (7.42, 8.58):
        b.oct("z", sx, 9.15, 0.22, -5.6, 2.1, "steel_b", name="stock_strut")
        b.chamfer_box([sx - 0.25, 8.6, 1.4], [sx + 0.25, 9.7, 2.3], 0.08, "rec", name="strut_mount")
    b.chamfer_box([7.1, 7.0, -6.25], [8.9, 10.8, -5.5], 0.2, "rubber", name="butt_pad")


# ───────────────────────── 샷건 (펌프) ─────────────────────────
def stock_drop(b, x0, x1, top, front_z, back_z, wrist_h, butt_h, drop, mat="wood", pad="rubber"):
    """한 덩어리 개머리: 윗선(콤)이 뒤로 갈수록 drop 만큼 내려가고, 아랫선은 손목(wrist_h)에서 개머리 바닥(butt_h)까지
    쐐기로 이어져 내려간다. 쐐기는 개머리 앞 아래 모서리를 회전 중심으로 앞이 들려 손목 아랫선에 닿는다."""
    L = front_z - back_z
    ang = math.degrees(math.atan2(drop, L))
    xf = Xf.rot("x", -ang, (8, top, front_z))
    mid = back_z + L * 0.5
    b.chamfer_box([x0, top - wrist_h, back_z], [x1, top, front_z], 0.35, mat, xf, name="stock")
    b.chamfer_box([x0 + 0.02, top - butt_h, back_z], [x1 - 0.02, top - 0.5, mid], 0.35, mat, xf, name="stock_butt")
    run = (front_z - 1.2) - mid
    al = math.degrees(math.atan2(butt_h - wrist_h, run))
    h = butt_h - wrist_h + 0.6
    b.chamfer_box([x0 + 0.04, top - butt_h, mid - 1.0], [x1 - 0.04, top - butt_h + h, mid + run / math.cos(math.radians(al))], 0.3, mat,
                  xf * Xf.rot("x", -al, (8, top - butt_h, mid)), name="stock_wedge")
    b.chamfer_box([x0 - 0.1, top - butt_h - 0.15, back_z - 0.65], [x1 + 0.1, top + 0.15, back_z + 0.05], 0.15, pad, xf, name="butt_pad")
    return xf


def shotgun(b):
    sx = stock_drop(b, 7.15, 8.85, 10.3, 3.0, -9.2, 2.6, 4.8, 1.3)
    b.chamfer_box([7.75, 6.3, -6.4], [8.25, 6.9, -5.2], 0.08, "steel_b", sx, name="sling")
    # 리시버 (앞 아래 경사) + 배출구 + 윗 홈
    b.chamfer_box([7.1, 7.9, 2.6], [8.9, 11.0, 10.6], 0.25, "blued", name="receiver")
    b.chamfer_box([7.12, 7.4, 9.4], [8.88, 8.4, 11.2], 0.2, "blued", Xf.rot("x", 30, (8, 8.4, 10.6)), name="rec_slope")
    b.put([8.82, 9.2, 4.4], [8.95, 10.4, 7.8], "bore", name="port")
    for (y0, y1) in ((9.0, 9.2), (10.4, 10.6)):
        b.put([8.85, y0, 4.2], [9.0, y1, 8.0], "rec_t", name="port_rim")
    b.chamfer_box([7.35, 10.95, 3.0], [8.65, 11.25, 10.4], 0.1, "rec_t", name="top_groove")
    for (y, z) in ((7.6, 3.6), (7.6, 8.0)):
        b.oct("x", y, z, 0.16, 7.05, 8.95, "steel_l", name="pin")
    # 방아쇠 뭉치 + 방아쇠울 (앞뒤 고정 고리) + 방아쇠 + 안전 버튼
    b.chamfer_box([7.3, 7.0, 3.0], [8.7, 8.0, 8.6], 0.15, "lo", name="trigger_group")
    b.chamfer_box([7.55, 6.05, 4.9], [8.45, 6.45, 7.1], 0.1, "lo", name="guard")
    b.chamfer_box([7.55, 6.6, 7.35], [8.45, 7.2, 7.75], 0.1, "lo", name="guard_front")
    b.chamfer_box([7.55, 6.6, 4.2], [8.45, 7.2, 4.6], 0.1, "lo", name="guard_back")
    for (z, a) in ((7.1, 45), (4.9, -45)):
        b.chamfer_box([7.55, 6.1, z - 0.2], [8.45, 6.85, z + 0.2], 0.08, "lo", Xf.rot("x", a, (8, 6.45, z)), name="guard_corner")
    b.chamfer_box([7.86, 6.5, 5.35], [8.14, 7.05, 5.75], 0.05, "steel_l", Xf.rot("x", 12, (8, 7.05, 5.55)), name="trigger")
    b.oct("x", 7.6, 4.0, 0.2, 7.2, 8.8, "red", name="safety")
    # 총열 + 튜브 탄창 + 고정 링 + 마개 + 가늠쇠 구슬
    b.oct("z", 8.0, 10.3, 0.46, 10.6, 30.0, "barrel_c", name="barrel")
    b.oct("z", 8.0, 10.3, 0.26, 29.98, 30.02, "bore", name="bore")
    b.oct("z", 8.0, 9.03, 0.42, 10.6, 26.6, "blued", name="mag_tube")
    b.oct("z", 8.0, 9.03, 0.55, 26.6, 27.6, "rec", name="tube_cap")
    b.chamfer_box([7.6, 8.5, 25.6], [8.4, 10.8, 26.4], 0.12, "rec", name="barrel_clamp")
    b.oct("y", 8.0, 29.35, 0.16, 10.7, 11.05, "brass", name="bead")
    # 펌프 (나무, 홈 4줄)
    b.chamfer_box([6.95, 7.9, 13.0], [9.05, 10.05, 20.4], 0.45, "wood", name="pump")
    for z in (14.0, 15.6, 17.2, 18.8):
        b.chamfer_box([6.88, 8.3, z], [9.12, 9.6, z + 0.35], 0.1, "wood_d", name="pump_groove")
    for sx_ in (7.4, 8.4):
        b.put([sx_, 8.4, 10.6], [sx_ + 0.2, 8.7, 13.0], "steel_b", name="action_bar")


# ───────────────────────── 더블배럴 ─────────────────────────
def double_barrel(b):
    sx = stock_drop(b, 7.15, 8.85, 10.1, 3.3, -9.2, 2.5, 5.0, 1.5)

    # 박스 락 (어두운 블루드) + 톱 레버 + 힌지 핀 + 측판 선
    b.chamfer_box([7.0, 7.8, 3.0], [9.0, 11.0, 8.2], 0.25, "blued", name="action")
    b.chamfer_box([7.05, 7.4, 3.4], [8.95, 8.2, 8.0], 0.2, "blued", Xf.rot("x", -10, (8, 8.2, 3.4)), name="action_belly")
    b.chamfer_box([7.4, 10.9, 3.1], [8.6, 11.35, 4.8], 0.1, "steel_b", name="top_lever")
    b.chamfer_box([7.75, 10.9, 4.6], [8.25, 11.3, 5.6], 0.06, "steel_b", name="safety")
    b.oct("x", 8.4, 7.9, 0.32, 6.95, 9.05, "steel_l", name="hinge_pin")
    b.oct("x", 9.6, 4.2, 0.18, 6.95, 9.05, "steel_l", name="pin")
    # 쌍열 총열 + 리브 + 구슬
    for cx in (7.33, 8.67):
        b.oct("z", cx, 9.88, 0.66, 8.2, 29.0, "barrel_c", name="barrel")
        b.oct("z", cx, 9.88, 0.42, 28.98, 29.02, "bore", name="bore")
    b.chamfer_box([7.7, 10.35, 8.2], [8.3, 10.85, 29.0], 0.08, "blued", name="rib")
    b.oct("y", 8.0, 28.45, 0.15, 10.85, 11.1, "brass", name="bead")
    b.chamfer_box([7.6, 9.0, 8.2], [8.4, 9.6, 29.0], 0.06, "blued", name="under_rib")
    # 앞나무 (총열 아래에 붙음) + 고정쇠
    b.chamfer_box([6.9, 8.0, 8.4], [9.1, 9.6, 15.8], 0.45, "wood", name="forend")
    b.chamfer_box([6.95, 8.2, 15.0], [9.05, 9.6, 16.8], 0.4, "wood", Xf.rot("x", -25, (8, 9.6, 15.0)), name="forend_tip")
    b.chamfer_box([7.5, 7.75, 15.6], [8.5, 8.1, 16.4], 0.08, "steel_b", name="forend_latch")
    # 방아쇠 두 개 + 방아쇠울 (팔각 고리)
    b.chamfer_box([7.55, 5.95, 4.3], [8.45, 6.3, 6.6], 0.08, "blued", name="guard")
    b.chamfer_box([7.55, 5.95, 6.3], [8.45, 7.9, 6.65], 0.08, "blued", name="guard_front")
    b.chamfer_box([7.55, 5.95, 3.95], [8.45, 7.9, 4.3], 0.08, "blued", name="guard_back")
    b.chamfer_box([7.4, 7.6, 3.6], [8.6, 8.0, 6.9], 0.1, "blued", name="trigger_plate")
    for z in (4.6, 5.6):
        b.chamfer_box([7.86, 6.7, z], [8.14, 7.9, z + 0.3], 0.05, "steel_l", Xf.rot("x", 12, (8, 7.9, z)), name="trigger")


# ───────────────────────── 매그넘 (리볼버) ─────────────────────────
def magnum(b):
    b.chamfer_box([7.3, 8.0, 5.6], [8.7, 11.4, 11.2], 0.25, "stain", name="frame")
    b.chamfer_box([7.35, 6.6, 4.6], [8.65, 8.4, 7.2], 0.25, "stain", name="grip_frame")
    # 실린더 (한 단 어둡게) + 홈 6줄 + 앞뒤 틈
    b.oct("z", 8.0, 9.7, 1.4, 6.6, 10.8, "stain_d", name="cylinder")
    for k in range(6):
        b.put([7.94, 9.7 + 1.2, 7.1], [8.06, 9.7 + 1.36, 10.3], "steel_d", Xf.rot("z", k * 60 + 30, (8, 9.7, 0)), name="flute")
    b.oct("z", 8.0, 9.7, 0.5, 10.75, 11.25, "steel_d", name="cyl_gap")
    b.chamfer_box([8.65, 8.6, 6.4], [8.85, 9.3, 7.4], 0.05, "steel_l", name="cyl_latch")
    # 총열 (밝은 단) + 통풍 리브 + 언더러그 (어두운 단)
    b.chamfer_box([7.5, 9.6, 11.2], [8.5, 10.85, 21.6], 0.2, "stain_l", name="barrel")
    b.chamfer_box([7.75, 10.8, 11.2], [8.25, 11.35, 21.6], 0.06, "stain", name="vent_rib")
    for z in (11.8, 13.6, 15.4, 17.2, 19.0):
        b.put([7.84, 10.95, z], [8.16, 11.36, z + 1.1], "steel_d", name="vent")
    b.chamfer_box([7.55, 8.45, 11.2], [8.45, 9.65, 21.6], 0.25, "stain_d", name="underlug")
    b.oct("z", 8.0, 10.2, 0.26, 21.58, 21.62, "bore", name="bore")
    b.chamfer_box([7.7, 11.3, 20.3], [8.3, 12.1, 21.4], 0.06, "stain", Xf.rot("x", -10, (8, 11.3, 20.8)), name="front_sight")
    b.put([7.92, 11.6, 20.85], [8.08, 11.95, 21.1], "red", name="sight_insert")
    b.chamfer_box([7.55, 11.35, 5.8], [8.45, 11.9, 6.8], 0.08, "steel_b", name="rear_sight")
    for sx in (7.62, 8.28):
        b.put([sx, 11.9, 6.0], [sx + 0.1, 11.92, 6.6], "sight_g", name="rear_dot")
    # 공이치기 (프레임에 박힌 몸통 + 뒤로 뻗은 스퍼)
    b.chamfer_box([7.72, 10.2, 5.0], [8.28, 11.7, 5.9], 0.1, "steel_b", name="hammer")
    b.chamfer_box([7.72, 11.35, 4.2], [8.28, 11.75, 5.3], 0.08, "steel_b", Xf.rot("x", -20, (8, 11.55, 5.3)), name="hammer_spur")
    # 둥근 방아쇠울 (아래 + 앞/뒤 사선) + 곡선 방아쇠
    b.chamfer_box([7.55, 6.4, 6.6], [8.45, 6.75, 8.7], 0.08, "stain", name="guard")
    b.chamfer_box([7.55, 6.45, 8.4], [8.45, 8.1, 8.75], 0.08, "stain", Xf.rot("x", 28, (8, 6.6, 8.6)), name="guard_front")
    b.chamfer_box([7.55, 6.45, 6.3], [8.45, 7.0, 6.65], 0.08, "stain", Xf.rot("x", -35, (8, 6.6, 6.6)), name="guard_back")
    b.chamfer_box([7.86, 7.4, 7.0], [8.14, 8.1, 7.35], 0.05, "steel_l", name="trigger")
    b.chamfer_box([7.86, 6.9, 7.0], [8.14, 7.5, 7.35], 0.05, "steel_l", Xf.rot("x", 22, (8, 7.45, 7.2)), name="trigger_tip")
    for (y, z) in ((10.6, 6.2), (8.8, 7.6)):
        b.oct("x", y, z, 0.22, 7.25, 8.75, "steel_l", name="pin")
    # 나무 손잡이 2마디 (아래로 갈수록 더 뒤로 휨) + 손가락 홈 + 메달
    g1 = Xf.rot("x", 12, (8, 8.2, 5.6))
    b.chamfer_box([7.2, 5.2, 4.0], [8.8, 8.2, 6.8], 0.35, "wood", g1, name="grip")
    g2 = Xf.rot("x", 26, (8, 5.4, 4.75))
    b.chamfer_box([7.2, 3.0, 3.5], [8.8, 5.8, 6.1], 0.35, "wood", g2, name="grip_low")
    for sx in (7.13, 8.8):
        b.oct("x", 6.6, 5.1, 0.2, sx, sx + 0.07, "brass", g1, name="medallion")


# ───────────────────────── 소음기 권총 ─────────────────────────
def silenced_pistol(b):
    # 슬라이드 + 뒤 톱니 + 3점 가늠자·가늠쇠 + 배출구
    b.chamfer_box([7.25, 9.6, 4.6], [8.75, 11.2, 13.0], 0.25, "rec", name="slide")
    for z in (4.9, 5.4, 5.9, 6.4):
        for sx in (7.2, 8.75):
            b.put([sx, 9.9, z], [sx + 0.05, 11.0, z + 0.2], "steel_d", name="serration")
    b.chamfer_box([7.3, 11.15, 5.0], [8.7, 11.7, 5.6], 0.08, "steel_b", name="rear_sight")
    for sx in (7.5, 8.38):
        b.put([sx, 11.3, 5.62], [sx + 0.12, 11.45, 5.64], "sight_g", name="rear_dot")
    b.chamfer_box([7.8, 11.15, 12.2], [8.2, 11.7, 12.7], 0.06, "steel_b", name="front_sight")
    b.put([7.93, 11.6, 12.35], [8.07, 11.72, 12.55], "sight_g", name="sight_dot")
    b.put([8.72, 10.0, 8.0], [8.8, 10.9, 10.4], "bore", name="port")
    # 프레임 (뒤가 아래로 이어져 백스트랩·비버테일과 하나) + 레일 블록 + 해머
    b.chamfer_box([7.3, 8.6, 5.0], [8.7, 9.65, 12.6], 0.15, "lo", name="frame")
    b.chamfer_box([7.3, 8.2, 3.9], [8.7, 9.65, 5.6], 0.2, "lo", name="beavertail")
    b.chamfer_box([7.4, 8.1, 10.5], [8.6, 8.7, 12.6], 0.08, "lo", name="rail")
    b.put([7.38, 8.25, 11.2], [8.62, 8.35, 11.4], "steel_d", name="rail_slot")
    b.put([7.38, 8.25, 11.9], [8.62, 8.35, 12.1], "steel_d", name="rail_slot")
    b.chamfer_box([7.75, 9.5, 4.1], [8.25, 10.6, 4.8], 0.08, "steel_b", Xf.rot("x", -15, (8, 9.6, 4.8)), name="hammer")
    b.chamfer_box([7.15, 9.0, 7.0], [7.3, 9.6, 8.6], 0.04, "steel_b", name="slide_stop")
    b.chamfer_box([7.12, 9.7, 5.2], [7.28, 10.2, 6.0], 0.04, "steel_b", name="safety")
    b.put([7.1, 9.85, 5.3], [7.12, 10.0, 5.45], "red", name="safety_dot")
    # 손잡이 (15°, 윗부분이 프레임 안으로) + 결 + 탄창 바닥
    gx = Xf.rot("x", 15, (8, 8.6, 5.6))
    b.chamfer_box([7.25, 3.8, 4.0], [8.75, 9.2, 6.8], 0.3, "poly", gx, name="grip")
    for sx in (7.18, 8.76):
        b.chamfer_box([sx, 4.6, 4.5], [sx + 0.06, 7.6, 6.4], 0.02, "poly_t", gx, name="grip_panel")
    b.chamfer_box([7.3, 3.35, 4.0], [8.7, 3.9, 6.8], 0.1, "mag", gx, name="mag_base")
    # 방아쇠울 + 방아쇠
    b.chamfer_box([7.5, 7.0, 6.8], [8.5, 7.5, 9.7], 0.12, "lo", name="guard")
    b.chamfer_box([7.5, 7.1, 9.2], [8.5, 8.7, 9.7], 0.12, "lo", name="guard_front")
    b.chamfer_box([7.86, 7.6, 7.4], [8.14, 8.6, 7.8], 0.05, "steel_l", Xf.rot("x", 12, (8, 8.6, 7.6)), name="trigger")
    for (y, z) in ((9.1, 7.0), (9.1, 11.6)):
        b.oct("x", y, z, 0.18, 7.25, 8.75, "steel_l", name="pin")
    # 소음기 (팔각) + 고정 칼라 + 홈 + 마개
    b.oct("z", 8.0, 10.2, 0.3, 13.0, 13.65, "steel_b", name="thread")
    b.oct("z", 8.0, 10.2, 0.95, 13.6, 14.15, "steel_b", name="sil_collar")
    b.oct("z", 8.0, 10.2, 0.85, 14.1, 21.65, "sil", name="silencer")
    for z in (16.0, 19.0):
        b.oct("z", 8.0, 10.2, 0.88, z, z + 0.16, "steel_d", name="sil_groove")
    b.oct("z", 8.0, 10.2, 0.9, 21.6, 22.0, "steel_b", name="sil_cap")
    b.oct("z", 8.0, 10.2, 0.22, 21.98, 22.02, "bore", name="bore")


GUNS = {"m16": m16, "mp5": mp5, "shotgun": shotgun, "double_barrel": double_barrel,
        "magnum": magnum, "silenced_pistol": silenced_pistol}
PAL_EXTRA = {"poly_t": (38, 38, 41), "red": (170, 40, 36), "white": (196, 196, 192), "sil": (44, 45, 48),
             "stain_d": (70, 72, 77), "stain_l": (96, 98, 104), "barrel_c": (56, 58, 62)}
# 총마다 부품 명도 단계 조정 (2회차~): 리시버 > 총열덮개·개머리 > 탄창 단계가 0.03 V 이상 벌어지게
GUN_PAL = {
    "m16": {"rec": (66, 67, 72), "rec_t": (80, 81, 86), "lo": (52, 53, 57), "poly": (27, 27, 29), "poly_t": (40, 40, 43), "mag": (40, 41, 44), "steel_b": (100, 102, 108)},
    "mp5": {"rec": (52, 53, 58), "lo": (44, 45, 48), "rec_t": (72, 73, 78), "poly": (30, 30, 32), "poly_t": (42, 42, 45), "mag": (40, 41, 44)},
    "shotgun": {"blued": (54, 55, 59), "barrel_c": (40, 41, 45), "lo": (38, 39, 42), "rec": (58, 59, 63), "wood": (88, 52, 38), "wood_d": (66, 38, 28)},
    "double_barrel": {"blued": (62, 63, 69), "barrel_c": (46, 47, 53), "steel_b": (78, 80, 86), "wood": (88, 52, 38), "wood_d": (66, 38, 28)},
    "magnum": {"stain": (64, 66, 71), "stain_d": (48, 49, 53), "stain_l": (80, 82, 88), "steel_b": (90, 92, 98)},
    "silenced_pistol": {"rec": (50, 51, 55), "lo": (66, 67, 71), "poly": (36, 36, 39), "poly_t": (46, 46, 50), "mag": (44, 45, 48), "sil": (60, 61, 64)},
}
GUN_TOPLINE = {"magnum": ("stain_l", "stain"), "double_barrel": ("rec", "rec_t", "blued", "steel_b")}


def build(gun, render_dir=None, stem=None):
    bbkit.DOT_MOD = 14   # 2회차~: 점 얼룩 20% → 14% (사각 패치처럼 보인다는 지적)
    bbkit.DOT_MODE = "cell"   # 3회차~: 점이 서로 붙어 2~4텍셀 사각 덩어리가 되던 것 → 4x2 칸마다 하나
    b = Builder()
    GUNS[gun](b)
    out = os.path.join(HERE, "out", gun); os.makedirs(out, exist_ok=True)
    pal = dict(BASE, **PAL_EXTRA); pal.update(GUN_PAL.get(gun, {}))
    img, uvs = atlas(b.parts, pal, density=2, style="tacz2", step=14, topline=GUN_TOPLINE.get(gun, TOPLINE))
    png = os.path.join(out, gun + ".png"); img.save(png)
    bb = os.path.join(out, gun + ".bbmodel")
    build_bbmodel(bb, gun, b.parts, png, uvs, gun)
    v = validate(bb)
    export_java(bb, os.path.join(out, gun + ".json"))
    if render_dir:
        render_views(bb, render_dir, stem or gun)
    print(f"{gun}: parts={len(b.parts)} tex={img.size} valid_errors={v.count('\"severity\": \"error\"') and v.split('\"errors\":')[1].split(',')[0].strip()}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)
