#!/usr/bin/env python3
"""총기 6종 루프 제작물 (블록벤치 MCP 로 생성). docs/TACZ_STYLE.md 2판 기준.
좌표는 기존 팩(tools/models_guns.py)과 같다: 총구 +Z, 위 +Y, 중심 x=8. HAND_POS / MUZZLE 자리를 그대로 지킨다.

사용: python3 tools/loop/guns/gen.py <총> [렌더 폴더] [이름]   총: m16 mp5 shotgun double_barrel magnum silenced_pistol
출력: tools/loop/guns/out/<총>/<총>.bbmodel (블록벤치 MCP) / .png / .json (MCP 내보내기)
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
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
    "stain":  (104, 106, 112),  # 스테인리스 (리볼버)
}
TOPLINE = ("rec", "rec_t", "blued", "stain")


def grooves_z(b, cx, cy, r, z0, z1, n, mat="steel_d"):
    """원통 둘레 홈 링 (z축)"""
    for k in range(n):
        z = z0 + (z1 - z0) * (k + 0.5) / n
        b.oct("z", cx, cy, r, z - 0.07, z + 0.07, mat, name="groove")


# ───────────────────────── M16 ─────────────────────────
def m16(b):
    # 고정 개머리판 + 버퍼 튜브
    b.chamfer_box([7.1, 6.3, -7.5], [8.9, 10.2, -1.6], 0.35, "poly", name="stock")
    b.chamfer_box([7.2, 5.9, -8.2], [8.8, 10.5, -7.45], 0.15, "rubber", name="butt_pad")
    b.oct("z", 8.0, 9.55, 0.62, -1.7, 2.1, "lo", name="buffer_tube")
    b.chamfer_box([7.75, 6.9, -6.9], [8.25, 7.45, -5.7], 0.08, "steel_b", name="sling")
    # 하부 리시버 + 탄창 삽입구
    b.chamfer_box([7.1, 7.4, 2.0], [8.9, 9.5, 10.6], 0.2, "lo", name="lower")
    b.chamfer_box([7.05, 6.4, 6.9], [8.95, 7.45, 10.4], 0.15, "lo", name="magwell")
    b.chamfer_box([7.0, 7.9, 2.6], [7.12, 8.6, 3.6], 0.04, "steel_l", name="selector")
    b.chamfer_box([8.88, 8.0, 7.4], [9.25, 8.6, 8.4], 0.08, "steel_l", name="mag_release")
    # 상부 리시버 + 배출구 덮개 + 포워드 어시스트 + 장전 손잡이
    b.chamfer_box([7.2, 9.5, 2.0], [8.8, 11.0, 11.2], 0.22, "rec", name="upper")
    b.put([8.8, 9.75, 5.8], [8.92, 10.65, 8.8], "steel_b", name="port_cover")
    b.oct("z", 8.95, 10.3, 0.32, 8.3, 9.7, "steel_b", name="forward_assist")
    b.chamfer_box([7.4, 10.6, 1.3], [8.6, 11.0, 2.05], 0.08, "steel_b", name="charging_handle")
    # 운반 손잡이 + 가늠자 드럼
    for z0 in (3.2, 8.4):
        b.chamfer_box([7.45, 11.0, z0], [8.55, 12.3, z0 + 1.1], 0.15, "rec", name="handle_post")
    b.chamfer_box([7.35, 12.25, 3.0], [8.65, 12.95, 9.8], 0.2, "rec_t", name="carry_handle")
    b.oct("x", 12.7, 3.7, 0.35, 7.3, 8.7, "steel_b", name="rear_drum")
    b.chamfer_box([7.75, 12.95, 3.3], [8.25, 13.5, 4.1], 0.08, "steel_b", name="rear_aperture")
    # 권총 손잡이 (22.5° 뒤로) + 방아쇠울 + 방아쇠
    gx = Xf.rot("x", 22.5, (8, 7.4, 4.4))
    b.chamfer_box([7.3, 3.6, 3.4], [8.7, 7.5, 5.3], 0.3, "poly", gx, name="grip")
    b.chamfer_box([7.22, 4.0, 4.3], [8.78, 6.8, 5.0], 0.1, "poly", gx, name="grip_ridge")
    b.chamfer_box([7.55, 5.95, 5.1], [8.45, 6.3, 8.1], 0.08, "lo", name="guard")
    b.chamfer_box([7.55, 6.0, 7.75], [8.45, 7.4, 8.1], 0.08, "lo", name="guard_front")
    b.chamfer_box([7.86, 6.55, 6.0], [8.14, 7.45, 6.35], 0.05, "steel_l", name="trigger")
    # 탄창 (곧은 윗부분 + 22.5° 휜 아랫부분 + 바닥판)
    b.chamfer_box([7.35, 3.6, 7.1], [8.65, 6.45, 9.9], 0.12, "mag", name="mag")
    mx = Xf.rot("x", -22.5, (8, 3.6, 8.5))
    b.chamfer_box([7.35, 0.65, 6.4], [8.65, 3.7, 9.2], 0.12, "mag", mx, name="mag_low")
    b.chamfer_box([7.25, 0.2, 6.25], [8.75, 0.7, 9.35], 0.1, "poly", mx, name="mag_floor")
    for sx in (7.3, 8.6):
        b.put([sx, 3.8, 7.6], [sx + 0.1, 6.2, 8.0], "steel_d", name="mag_rib")
    # 델타 링 + 둥근 총열덮개 (냉각 구멍 줄) + 덮개 마개
    b.oct("z", 8.0, 9.5, 1.18, 10.9, 11.5, "steel_b", name="delta_ring")
    b.oct("z", 8.0, 9.5, 1.08, 11.5, 18.6, "poly", name="handguard")
    for z in (12.4, 13.6, 14.8, 16.0, 17.2):
        for y in (9.15, 9.85):
            b.put([6.88, y - 0.12, z], [7.0, y + 0.12, z + 0.55], "rubber", name="vent")
            b.put([9.0, y - 0.12, z], [9.12, y + 0.12, z + 0.55], "rubber", name="vent")
    b.oct("z", 8.0, 9.5, 0.95, 18.6, 19.1, "steel_b", name="hg_cap")
    # 가늠쇠 (A자 기둥) + 대검 꽂이
    b.chamfer_box([7.5, 8.9, 19.6], [8.5, 10.35, 20.8], 0.12, "rec", name="fsb")
    for sgn in (1, -1):
        b.chamfer_box([7.75, 10.2, 19.9], [8.25, 12.6, 20.5], 0.06, "rec", Xf.rot("z", sgn * 9, (8, 10.3, 20.2)), name="fs_wing")
    b.chamfer_box([7.62, 11.6, 19.85], [8.38, 12.7, 20.55], 0.08, "rec", name="fs_top")
    b.put([7.92, 12.7, 20.05], [8.08, 13.15, 20.35], "steel_l", name="fs_post")
    b.chamfer_box([7.6, 8.2, 20.0], [8.4, 8.95, 20.6], 0.08, "rec", name="bayonet_lug")
    # 총열 + 새장형 소염기
    b.oct("z", 8.0, 9.6, 0.36, 19.1, 27.0, "steel_b", name="barrel")
    b.oct("z", 8.0, 9.6, 0.52, 27.0, 29.4, "rec", name="flash_hider")
    for k in range(4):
        a = k * 90 + 45
        b.put([7.96, 9.6 + 0.42, 27.4], [8.04, 9.6 + 0.56, 28.9], "bore", Xf.rot("z", a, (8, 9.6, 0)), name="hider_slot")
    b.oct("z", 8.0, 9.6, 0.24, 29.38, 29.42, "bore", name="bore")
    b.chamfer_box([7.8, 7.65, 18.0], [8.2, 8.4, 18.6], 0.06, "steel_b", name="sling_front")


# ───────────────────────── MP5 ─────────────────────────
def mp5(b):
    # 둥근 윗면 리시버 (크게 깎은 상자) + 윗 홈
    b.chamfer_box([7.15, 8.2, 2.0], [8.85, 11.0, 14.6], 0.45, "rec", name="receiver")
    b.chamfer_box([7.35, 10.95, 2.4], [8.65, 11.3, 14.2], 0.12, "rec_t", name="top_rib")
    for sx in (7.1, 8.85):
        b.put([sx, 9.5, 3.0], [sx + 0.06, 9.75, 13.8], "steel_d", name="press_line")
    # 드럼 가늠자
    b.oct("x", 11.95, 3.25, 0.62, 7.1, 8.9, "steel_b", name="rear_drum")
    b.chamfer_box([7.35, 11.3, 2.7], [8.65, 11.65, 3.8], 0.08, "rec", name="drum_base")
    # 가늠쇠 링 후드 (팔각 고리 반쪽) + 기둥
    for sx in (7.35, 8.65):
        b.oct("z", sx, 11.3, 0.22, 17.4, 18.6, "steel_b", name="hood_side")
    b.chamfer_box([7.3, 12.0, 17.4], [8.7, 12.4, 18.6], 0.12, "steel_b", name="hood_top")
    b.put([7.92, 10.4, 17.8], [8.08, 11.5, 18.2], "steel_l", name="fs_post")
    # 장전 튜브 + 장전 손잡이 (왼쪽)
    b.oct("z", 8.0, 10.5, 0.55, 14.6, 19.0, "rec", name="cocking_tube")
    b.chamfer_box([6.55, 10.15, 15.0], [7.35, 10.6, 15.6], 0.08, "steel_l", name="cocking_handle")
    # 핸드가드 (손가락 홈)
    b.chamfer_box([7.0, 7.6, 12.4], [9.0, 10.0, 17.6], 0.35, "poly", name="handguard")
    for z in (13.3, 14.5, 15.7, 16.9):
        b.chamfer_box([6.92, 7.9, z], [9.08, 8.4, z + 0.35], 0.08, "poly", name="hg_groove")
    b.chamfer_box([7.2, 7.9, 17.6], [8.8, 9.9, 18.2], 0.15, "poly", name="hg_front")
    # 총열 + 3-러그
    b.oct("z", 8.0, 9.35, 0.4, 18.2, 20.2, "steel_b", name="barrel")
    b.oct("z", 8.0, 9.35, 0.55, 20.2, 21.6, "rec", name="lug")
    for k in range(3):
        b.put([7.94, 9.35 + 0.5, 20.3], [8.06, 9.35 + 0.66, 20.9], "rec", Xf.rot("z", k * 120, (8, 9.35, 0)), name="lug_tab")
    b.oct("z", 8.0, 9.35, 0.24, 21.58, 21.62, "bore", name="bore")
    # 방아쇠 뭉치 + 손잡이 + 방아쇠울
    b.chamfer_box([7.2, 6.9, 3.2], [8.8, 8.25, 10.6], 0.2, "poly", name="trigger_group")
    gx = Xf.rot("x", 22.5, (8, 7.2, 4.6))
    b.chamfer_box([7.3, 3.4, 3.6], [8.7, 7.4, 5.5], 0.3, "poly", gx, name="grip")
    for k, y in enumerate((4.0, 4.8, 5.6)):
        b.chamfer_box([7.24, y, 5.25], [8.76, y + 0.35, 5.6], 0.08, "poly", gx, name="finger")
    b.chamfer_box([7.55, 6.15, 5.8], [8.45, 6.5, 8.6], 0.08, "poly", name="guard")
    b.chamfer_box([7.55, 6.2, 8.25], [8.45, 6.95, 8.6], 0.08, "poly", name="guard_front")
    b.chamfer_box([7.86, 6.5, 6.4], [8.14, 7.0, 6.75], 0.05, "steel_l", name="trigger")
    b.chamfer_box([6.98, 7.3, 4.0], [7.12, 7.8, 4.6], 0.04, "steel_l", name="selector")
    # 탄창 (휘어짐)
    b.chamfer_box([7.35, 4.6, 9.8], [8.65, 8.2, 11.2], 0.12, "mag", name="mag")
    mx = Xf.rot("x", -22.5, (8, 4.6, 10.5))
    b.chamfer_box([7.35, 1.45, 9.4], [8.65, 4.7, 10.8], 0.12, "mag", mx, name="mag_low")
    b.chamfer_box([7.25, 1.0, 9.25], [8.75, 1.5, 10.95], 0.1, "poly", mx, name="mag_floor")
    b.chamfer_box([7.4, 8.2, 11.4], [8.6, 8.6, 12.4], 0.08, "steel_b", name="mag_catch")
    # 접이식 개머리 (지지대 2개 + 개머리 판)
    for sx in (7.42, 8.58):
        b.oct("z", sx, 9.15, 0.2, -5.6, 2.1, "steel_b", name="stock_strut")
    b.chamfer_box([7.1, 7.0, -6.25], [8.9, 10.8, -5.5], 0.2, "rubber", name="butt_pad")


# ───────────────────────── 샷건 (펌프) ─────────────────────────
def shotgun(b):
    # 나무 개머리판 (손목 부분 가늘게)
    b.chamfer_box([7.1, 5.7, -9.0], [8.9, 10.4, -4.0], 0.4, "wood", name="stock")
    b.chamfer_box([7.2, 6.7, -4.1], [8.8, 10.2, -0.5], 0.35, "wood", name="stock_mid")
    b.chamfer_box([7.25, 7.6, -0.6], [8.75, 10.0, 2.7], 0.3, "wood", name="wrist")
    b.chamfer_box([7.0, 5.3, -9.6], [9.0, 10.8, -8.95], 0.18, "rubber", name="butt_pad")
    b.chamfer_box([7.75, 6.8, -6.4], [8.25, 7.4, -5.0], 0.08, "steel_b", name="sling")
    # 리시버 + 배출구 + 윗 홈
    b.chamfer_box([7.1, 7.9, 2.6], [8.9, 11.0, 10.6], 0.25, "blued", name="receiver")
    b.put([8.82, 9.2, 4.4], [8.95, 10.4, 7.8], "bore", name="port")
    b.chamfer_box([7.35, 10.95, 3.0], [8.65, 11.25, 10.4], 0.1, "rec_t", name="top_groove")
    # 방아쇠 뭉치 + 방아쇠울
    b.chamfer_box([7.3, 7.0, 3.4], [8.7, 7.95, 8.6], 0.15, "blued", name="trigger_group")
    b.chamfer_box([7.55, 6.05, 4.4], [8.45, 6.4, 7.6], 0.08, "blued", name="guard")
    b.chamfer_box([7.55, 6.1, 7.25], [8.45, 7.0, 7.6], 0.08, "blued", name="guard_front")
    b.chamfer_box([7.86, 6.5, 5.35], [8.14, 7.05, 5.75], 0.05, "steel_l", name="trigger")
    # 총열 + 튜브 탄창 + 고정 링 + 마개 + 가늠쇠 구슬
    b.oct("z", 8.0, 10.3, 0.46, 10.6, 30.0, "blued", name="barrel")
    b.oct("z", 8.0, 10.3, 0.26, 29.98, 30.02, "bore", name="bore")
    b.oct("z", 8.0, 9.03, 0.42, 10.6, 26.6, "blued", name="mag_tube")
    b.oct("z", 8.0, 9.03, 0.55, 26.6, 27.6, "steel_b", name="tube_cap")
    b.chamfer_box([7.6, 8.5, 25.6], [8.4, 10.8, 26.4], 0.12, "steel_b", name="barrel_clamp")
    b.oct("y", 8.0, 29.35, 0.16, 10.7, 11.05, "brass", name="bead")
    # 펌프 (나무, 홈 링)
    b.chamfer_box([6.95, 7.9, 13.0], [9.05, 10.05, 20.4], 0.4, "wood", name="pump")
    for z in (13.6, 14.6, 15.6, 16.6, 17.6, 18.6, 19.6):
        b.chamfer_box([6.88, 8.3, z], [9.12, 9.6, z + 0.3], 0.1, "wood_d", name="pump_groove")
    for sx in (7.4, 8.4):
        b.put([sx, 8.4, 10.6], [sx + 0.2, 8.7, 13.0], "steel_b", name="action_bar")


# ───────────────────────── 더블배럴 ─────────────────────────
def double_barrel(b):
    b.chamfer_box([7.1, 5.5, -9.0], [8.9, 10.2, -3.6], 0.4, "wood", name="stock")
    b.chamfer_box([7.2, 6.8, -3.7], [8.8, 10.0, 0.0], 0.35, "wood", name="stock_mid")
    b.chamfer_box([7.25, 7.6, -0.1], [8.75, 9.8, 3.05], 0.3, "wood", name="wrist")
    for z in (0.3, 1.0, 1.7, 2.4):                       # 손목 체크링 홈
        b.put([7.2, 8.0, z], [8.8, 9.4, z + 0.18], "wood_d", name="checker")
    b.chamfer_box([7.0, 5.1, -9.6], [9.0, 10.6, -8.95], 0.18, "rubber", name="butt_pad")
    # 박스 락 (밝은 강철)
    b.chamfer_box([7.0, 7.8, 3.0], [9.0, 11.0, 8.2], 0.25, "stain", name="action")
    b.chamfer_box([7.4, 10.95, 2.4], [8.6, 11.4, 4.2], 0.1, "blued", name="top_lever")
    for (y, z) in ((9.4, 4.0), (8.4, 6.8)):
        b.oct("x", y, z, 0.2, 6.95, 9.05, "steel_l", name="pin")
    # 쌍열 총열 + 리브 + 구슬
    for cx in (7.33, 8.67):
        b.oct("z", cx, 9.88, 0.66, 8.2, 29.0, "blued", name="barrel")
        b.oct("z", cx, 9.88, 0.42, 28.98, 29.02, "bore", name="bore")
    b.chamfer_box([7.75, 10.4, 8.2], [8.25, 10.85, 29.0], 0.08, "blued", name="rib")
    b.oct("y", 8.0, 28.45, 0.15, 10.85, 11.1, "brass", name="bead")
    for z in (12.0, 20.0, 26.0):
        b.put([7.8, 8.8, z], [8.2, 9.2, z + 0.6], "steel_b", name="spacer")
    # 앞나무 + 고정쇠
    b.chamfer_box([6.9, 8.0, 8.4], [9.1, 9.35, 16.6], 0.3, "wood", name="forend")
    b.chamfer_box([7.5, 7.4, 16.6], [8.5, 8.05, 17.2], 0.08, "steel_b", name="forend_latch")
    # 방아쇠 두 개 + 방아쇠울
    b.chamfer_box([7.55, 6.15, 3.8], [8.45, 6.5, 7.0], 0.08, "blued", name="guard")
    b.chamfer_box([7.55, 6.2, 6.65], [8.45, 7.8, 7.0], 0.08, "blued", name="guard_front")
    for z in (4.6, 5.6):
        b.chamfer_box([7.86, 6.7, z], [8.14, 7.8, z + 0.3], 0.05, "steel_l", name="trigger")


# ───────────────────────── 매그넘 (리볼버) ─────────────────────────
def magnum(b):
    b.chamfer_box([7.3, 8.0, 5.6], [8.7, 11.4, 11.2], 0.25, "stain", name="frame")
    # 실린더: 팔각 원통 + 홈 6줄
    b.oct("z", 8.0, 9.7, 1.4, 6.6, 10.8, "stain", name="cylinder")
    for k in range(6):
        b.put([7.94, 9.7 + 1.2, 7.1], [8.06, 9.7 + 1.36, 10.3], "steel_d", Xf.rot("z", k * 60 + 30, (8, 9.7, 0)), name="flute")
    b.oct("z", 8.0, 9.7, 0.5, 10.75, 11.25, "steel_d", name="cyl_gap")
    # 총열 + 통풍 리브 + 언더러그 (이젝터 하우징)
    b.chamfer_box([7.5, 9.6, 11.2], [8.5, 10.85, 21.6], 0.2, "stain", name="barrel")
    b.chamfer_box([7.75, 10.8, 11.2], [8.25, 11.35, 21.6], 0.06, "stain", name="vent_rib")
    for z in range(12, 21, 2):
        b.put([7.72, 10.95, z], [8.28, 11.36, z + 0.6], "steel_d", name="vent")
    b.chamfer_box([7.55, 8.45, 11.2], [8.45, 9.65, 21.6], 0.25, "stain", name="underlug")
    b.oct("z", 8.0, 10.2, 0.26, 21.58, 21.62, "bore", name="bore")
    b.chamfer_box([7.7, 11.3, 20.3], [8.3, 12.1, 21.4], 0.06, "stain", Xf.rot("x", -10, (8, 11.3, 20.8)), name="front_sight")
    b.put([7.92, 11.6, 20.9], [8.08, 11.95, 21.15], "brass", name="sight_insert")
    b.chamfer_box([7.55, 11.35, 5.8], [8.45, 11.9, 6.8], 0.08, "steel_b", name="rear_sight")
    # 공이치기 + 방아쇠울 + 방아쇠
    b.chamfer_box([7.7, 10.8, 4.6], [8.3, 12.4, 5.6], 0.1, "steel_b", Xf.rot("x", -22.5, (8, 11, 5.4)), name="hammer")
    b.chamfer_box([7.55, 6.55, 6.0], [8.45, 6.9, 9.2], 0.08, "stain", name="guard")
    b.chamfer_box([7.55, 6.6, 8.85], [8.45, 8.0, 9.2], 0.08, "stain", name="guard_front")
    b.chamfer_box([7.86, 7.0, 7.0], [8.14, 8.0, 7.4], 0.05, "steel_l", name="trigger")
    for (y, z) in ((10.6, 6.2), (8.8, 7.6)):
        b.oct("x", y, z, 0.22, 7.25, 8.75, "steel_l", name="pin")
    # 나무 손잡이 (22.5°) + 손가락 홈 + 금 메달
    gx = Xf.rot("x", 22.5, (8, 8, 5.6))
    b.chamfer_box([7.2, 3.4, 4.0], [8.8, 8.2, 6.6], 0.35, "wood", gx, name="grip")
    for y in (4.4, 5.3, 6.2):
        b.chamfer_box([7.25, y, 6.45], [8.75, y + 0.35, 6.75], 0.1, "wood_d", gx, name="finger")
    for sx in (7.13, 8.8):
        b.oct("x", 6.0, 5.0, 0.28, sx, sx + 0.07, "brass", gx, name="medallion")


# ───────────────────────── 소음기 권총 ─────────────────────────
def silenced_pistol(b):
    # 슬라이드 + 뒤 톱니 + 가늠자·가늠쇠 + 배출구
    b.chamfer_box([7.25, 9.6, 4.6], [8.75, 11.2, 13.0], 0.25, "rec", name="slide")
    for z in (4.9, 5.3, 5.7, 6.1, 6.5):
        for sx in (7.2, 8.75):
            b.put([sx, 9.9, z], [sx + 0.05, 11.0, z + 0.18], "steel_d", name="serration")
    b.chamfer_box([7.3, 11.15, 5.0], [8.7, 11.7, 5.6], 0.08, "steel_b", name="rear_sight")
    b.chamfer_box([7.8, 11.15, 12.2], [8.2, 11.7, 12.7], 0.06, "steel_b", name="front_sight")
    b.put([7.93, 11.6, 12.35], [8.07, 11.72, 12.55], "sight_g", name="sight_dot")
    b.put([8.72, 10.0, 8.0], [8.8, 10.9, 10.4], "bore", name="port")
    # 프레임 + 레일
    b.chamfer_box([7.3, 8.6, 5.2], [8.7, 9.65, 12.6], 0.15, "poly", name="frame")
    for z in (10.8, 11.3, 11.8, 12.3):
        b.chamfer_box([7.4, 8.2, z], [8.6, 8.62, z + 0.3], 0.06, "poly", name="rail")
    b.chamfer_box([7.15, 9.0, 7.0], [7.3, 9.6, 8.6], 0.04, "steel_b", name="slide_stop")
    # 손잡이 (15°) + 탄창 바닥
    gx = Xf.rot("x", 15, (8, 8.6, 5.6))
    b.chamfer_box([7.25, 3.8, 4.0], [8.75, 8.8, 6.8], 0.3, "poly", gx, name="grip")
    for y in (4.4, 5.2, 6.0, 6.8):
        for sx in (7.2, 8.74):
            b.put([sx, y, 4.6], [sx + 0.06, y + 0.4, 6.3], "poly_t", gx, name="stipple")
    b.chamfer_box([7.3, 3.35, 3.8], [8.7, 3.9, 6.6], 0.1, "mag", gx, name="mag_base")
    # 방아쇠울 + 방아쇠
    b.chamfer_box([7.55, 7.15, 6.8], [8.45, 7.5, 9.6], 0.08, "poly", name="guard")
    b.chamfer_box([7.55, 7.2, 9.25], [8.45, 8.65, 9.6], 0.08, "poly", name="guard_front")
    b.chamfer_box([7.86, 7.6, 7.4], [8.14, 8.6, 7.8], 0.05, "steel_l", name="trigger")
    for (y, z) in ((9.1, 7.0), (9.1, 11.6)):
        b.oct("x", y, z, 0.18, 7.25, 8.75, "steel_l", name="pin")
    # 소음기 (팔각) + 고정 칼라 + 홈 + 마개
    b.oct("z", 8.0, 10.2, 0.3, 13.0, 13.65, "steel_b", name="thread")
    b.oct("z", 8.0, 10.2, 0.95, 13.6, 14.15, "steel_b", name="sil_collar")
    b.oct("z", 8.0, 10.2, 0.85, 14.1, 21.65, "poly", name="silencer")
    for z in (16.0, 19.0):
        b.oct("z", 8.0, 10.2, 0.88, z, z + 0.16, "steel_d", name="sil_groove")
    b.oct("z", 8.0, 10.2, 0.9, 21.6, 22.0, "steel_b", name="sil_cap")
    b.oct("z", 8.0, 10.2, 0.22, 21.98, 22.02, "bore", name="bore")


GUNS = {"m16": m16, "mp5": mp5, "shotgun": shotgun, "double_barrel": double_barrel,
        "magnum": magnum, "silenced_pistol": silenced_pistol}
PAL_EXTRA = {"poly_t": (38, 38, 41)}


def build(gun, render_dir=None, stem=None):
    b = Builder()
    GUNS[gun](b)
    out = os.path.join(HERE, "out", gun); os.makedirs(out, exist_ok=True)
    pal = dict(BASE, **PAL_EXTRA)
    img, uvs = atlas(b.parts, pal, density=2, style="tacz2", step=14, topline=TOPLINE)
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
