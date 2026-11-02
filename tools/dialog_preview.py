#!/usr/bin/env python3
"""
컷씬 다이얼로그 미리보기 GIF (게임 캡처가 아닌 시뮬레이션).
클럽 댄스홀에서 NPC 두 명이 대화한다. 플러그인 DialogService 와 같은 시간표/공식을 따른다.
 - 카메라: 대사마다 말하는 NPC 를 비추는 자리(shotFor)로 easeOutExpo 28틱
 - 위아래 띠: 레터박스 오버레이 8프레임 (리소스팩 텍스처 그대로)
 - 패널/초상화: 타이틀 글리프 배치(DialogLayout.panel), 패널 16틱 easeOutExpo, 초상화 ±15° easeInOutSine
 - 대사: 패널이 들어오고 5틱 뒤부터 틱당 1글자, 두 줄 가운데 정렬 (액션바 글꼴 위치)
 - 배경: 클럽 조명 쉐이더 계산(club_preview), NPC 는 엔티티라 쉐이더 색이 입혀지지 않음(게임과 같음)
결과: build-out/dialog/dialog_npc.gif
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import club_preview as CP  # noqa: E402
import render_maps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = os.path.join(ROOT, "resourcepack", "assets", "violence")
OUT = os.path.join(ROOT, "build-out", "dialog")
FONT_KR = os.path.join(ROOT, "tools", "fonts", "blackhansans_BlackHanSans-Regular.ttf")
FONT_EN = os.path.join(ROOT, "tools", "fonts", "bungee_Bungee-Regular.ttf")

OW, OH = 960, 540          # 출력 크기
GUI = 2                    # GUI 배율 (GUI 480x270 = 1080p 에서 배율 4 와 같은 비율)
STEP = 2                   # GIF 한 장 = 2틱 (10fps)
CP.W, CP.H = 480, 270      # 배경 광선 추적 해상도

# DialogService / DialogLayout 상수
MOVE_TICKS, PANEL_IN, PANEL_OUT, SWAY_HALF = 28, 16, 7, 20
PANEL_X, PORTRAIT_X, SLIDE = 16, 26, 110
CUT = json.load(open(os.path.join(ROOT, "bukkit", "plugins", "ViolenceCore", "cutscene.json"), encoding="utf-8"))
PANEL_ASCENT, PORTRAIT_ASCENT, PORTRAIT_H, PANEL_H = 23, 17, 32, 44
DIALOG_SIZE, SHIFTS = 12.0, (24.0, 44.0)


def out_expo(t):
    t = min(1.0, max(0.0, t))
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def in_out_sine(t):
    t = min(1.0, max(0.0, t))
    return -(math.cos(math.pi * t) - 1) / 2


def sway(ticks, half=SWAY_HALF, amp=15.0):
    ph = ticks % (2 * half)
    return -amp + 2 * amp * in_out_sine(ph / half) if ph < half else amp - 2 * amp * in_out_sine((ph - half) / half)


def lerp_angle(a, b, t):
    d = ((b - a) % 360 + 540) % 360 - 180
    return a + d * t


def yaw_of(v):
    return math.degrees(math.atan2(-v[0], v[2]))


def pitch_of(v):
    return math.degrees(math.atan2(-v[1], math.hypot(v[0], v[2])))


def shot_for(eye, yaw):
    """DialogService.shotFor 와 같은 계산: 얼굴을 비스듬히 앞에서, 오른쪽 패널을 피해 화면 왼쪽에"""
    y = math.radians(yaw)
    fwd = np.array([-math.sin(y), 0, math.cos(y)])
    right = np.array([-fwd[2], 0, fwd[0]])            # fwd × up
    right /= np.linalg.norm(right)
    c = eye + fwd * 2.4 - right * 0.55 + np.array([0, 0.25, 0])
    to_eye = (eye - c) / np.linalg.norm(eye - c)
    cam_right = np.array([-to_eye[2], 0, to_eye[0]])
    cam_right /= np.linalg.norm(cam_right)
    look = eye + cam_right * 0.85 - c
    look /= np.linalg.norm(look)
    return c, yaw_of(look), pitch_of(look)


# ───────────────────────── NPC (엔티티: 상자 몇 개) ─────────────────────────

SKIN = (226, 176, 136)


def npc_boxes(feet, facing, kind):
    """+x 또는 -x 를 바라보는 사람 모양 상자들 (머리 0.5, 몸 0.5x0.75x0.25, 팔다리)"""
    fx, fy, fz = feet
    s = 1 if facing > 0 else -1
    bx = []

    def box(x0, y0, z0, x1, y1, z1, col, tag=""):
        # x 는 앞뒤(바라보는 방향), z 는 좌우
        xa, xb = fx + s * x0, fx + s * x1
        bx.append((np.array([min(xa, xb), fy + y0, fz + z0]), np.array([max(xa, xb), fy + y1, fz + z1]), np.array(col) / 255.0, tag))

    suit = (236, 236, 236) if kind == "npc" else (40, 70, 140)
    pants = (30, 30, 34) if kind == "npc" else (54, 54, 64)
    box(-0.125, 0.0, -0.25, 0.125, 0.75, 0.0, pants)                       # 다리
    box(-0.125, 0.0, 0.0, 0.125, 0.75, 0.25, pants)
    box(-0.125, 0.75, -0.25, 0.125, 1.5, 0.25, suit)                        # 몸
    box(-0.125, 0.8, -0.5, 0.125, 1.5, -0.25, suit)                         # 팔
    box(-0.125, 0.8, 0.25, 0.125, 1.5, 0.5, suit)
    if kind == "npc":
        box(-0.25, 1.5, -0.25, 0.25, 2.0, 0.25, SKIN, "face")               # 민머리 + 선글라스(얼굴 앞면에 칠함)
        box(0.12, 1.25, -0.06, 0.135, 1.5, 0.06, (20, 20, 24))             # 넥타이
    else:
        # 닭 가면 (흰 깃털 + 붉은 볏/뺨/육수 + 노란 부리)
        box(-0.27, 1.48, -0.27, 0.27, 2.02, 0.27, (244, 242, 234), "rooster")
        box(-0.05, 2.02, -0.06, 0.25, 2.3, 0.06, (232, 36, 40))
        box(0.27, 1.78, -0.1, 0.48, 1.88, 0.1, (250, 196, 40))
        box(0.27, 1.6, -0.06, 0.34, 1.76, 0.06, (214, 30, 36))
    return bx


def trace_boxes(eye, d, boxes):
    t_best = np.full(len(d), np.inf)
    col = np.zeros((len(d), 3))
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / d
    for lo, hi, c, tag in boxes:
        t0 = (lo - eye) * inv
        t1 = (hi - eye) * inv
        tn = np.nanmax(np.minimum(t0, t1), axis=1)
        tf = np.nanmin(np.maximum(t0, t1), axis=1)
        h = (tn <= tf) & (tn > 0) & (tn < t_best)
        if not h.any():
            continue
        p = eye + d[h] * tn[h][:, None]
        eps = 1e-4
        nx = (np.abs(p[:, 0] - lo[0]) < eps) | (np.abs(p[:, 0] - hi[0]) < eps)
        ny = (np.abs(p[:, 1] - lo[1]) < eps) | (np.abs(p[:, 1] - hi[1]) < eps)
        shade = np.where(ny, np.where(np.abs(p[:, 1] - hi[1]) < eps, 1.0, 0.5), np.where(nx, 0.8, 0.6))
        cc = np.tile(c, (h.sum(), 1))
        if tag == "face":            # 선글라스 띠
            band = (p[:, 1] > lo[1] + 0.26) & (p[:, 1] < lo[1] + 0.34)
            cc[band] = (0.06, 0.06, 0.08)
        if tag == "rooster":         # 붉은 뺨과 검은 눈 (양옆)
            cheek = (p[:, 1] > lo[1] + 0.16) & (p[:, 1] < lo[1] + 0.40) & (np.abs(p[:, 2] - (lo[2] + hi[2]) / 2) > 0.17)
            cc[cheek] = (0.88, 0.17, 0.17)
            eye_px = (p[:, 1] > lo[1] + 0.30) & (p[:, 1] < lo[1] + 0.36) & cheek
            cc[eye_px] = (0.04, 0.04, 0.04)
        col[h] = cc * shade[:, None] * 0.92
        t_best[h] = tn[h]
    return t_best, col


# ───────────────────────── 화면 UI (리소스팩 그대로) ─────────────────────────

class UI:
    def __init__(self):
        self.bars = [None] + [Image.open(os.path.join(NS, "textures", "misc", f"letterbox_{i}.png")).convert("RGBA").resize((OW, OH), Image.NEAREST)
                              for i in range(1, CUT["letterbox_frames"] + 1)]
        self.panel = Image.open(os.path.join(NS, "textures", "font", "cut_panel.png")).convert("RGBA")
        u = 4 * GUI                                             # 타이틀 글꼴 1단위 = 4 GUI 픽셀
        self.panel = self.panel.resize((round(self.panel.width * PANEL_H * u / self.panel.height), PANEL_H * u), Image.NEAREST)
        self.portraits = {}
        for pid in ("richard", "npc"):
            strip = Image.open(os.path.join(NS, "textures", "font", f"portrait_{pid}.png")).convert("RGBA")
            n = CUT["portrait"]["frames"]
            w = strip.width // n
            self.portraits[pid] = [strip.crop((i * w, 0, (i + 1) * w, strip.height)).resize((PORTRAIT_H * u, PORTRAIT_H * u), Image.NEAREST) for i in range(n)]
        from fontTools.ttLib import TTFont
        self.fonts = {}
        for key, path, size in (("kr", FONT_KR, DIALOG_SIZE), ("en", FONT_EN, DIALOG_SIZE * 0.92)):
            f = TTFont(path)
            span = f["hhea"].ascent - f["hhea"].descent
            em = f["head"].unitsPerEm
            px = size * GUI * em / span                          # 마인크래프트 size = (상승-하강) 높이
            self.fonts[key] = (ImageFont.truetype(path, round(px)), size * GUI * f["hhea"].ascent / span)
        self.metrics = CUT["dialog"]["metrics"]

    def width(self, ch):
        m = self.metrics
        if ch in m["ascii"]:
            return m["ascii"][ch]
        return m["hangul"] if "가" <= ch <= "힣" else m["extra"].get(ch, m["default"])

    def draw(self, img, bar, panel_slide, portrait, angle, lines, revealed):
        if bar > 0:
            img.alpha_composite(self.bars[bar])
        cx, cy = OW // 2, OH // 2
        u = 4 * GUI
        if panel_slide < 0.999:
            off = round(SLIDE * panel_slide)
            img.alpha_composite(self.panel, (cx + (PANEL_X + off) * u, cy + (-3 - PANEL_ASCENT) * u))
            if portrait:
                frames = self.portraits[portrait]
                f = round((angle + 15) / 30 * (len(frames) - 1))
                img.alpha_composite(frames[max(0, min(len(frames) - 1, f))], (cx + (PORTRAIT_X + off) * u, cy + (-3 - PORTRAIT_ASCENT) * u))
        d = ImageDraw.Draw(img)
        left = revealed
        for i, line in enumerate(lines):
            if left <= 0:
                break
            shown = line[:left]
            left -= len(shown)
            x = cx - sum(self.width(c) for c in line) / 2 * GUI
            top = OH - (72 - SHIFTS[i]) * GUI
            for ch in shown:
                key = "en" if ord(ch) < 128 else "kr"
                font, asc = self.fonts[key]
                for dx, dy, col in ((GUI, GUI, (63, 63, 63)), (0, 0, (255, 255, 255))):   # 마인크래프트 글자 그림자
                    d.text((x + dx, top + asc + dy), ch, font=font, fill=col, anchor="ls")
                x += self.width(ch) * GUI


# ───────────────────────── 시간표 ─────────────────────────

LINES = [
    ("A", "richard", "오늘 밤 손님이 많군. 준비는 됐나?"),
    ("B", "npc", "위층에 놈들이 50명이나 있어요. 정말 혼자 가실 겁니까?"),
    ("A", "richard", "혼자가 아니지. 네가 문을 열어."),
    ("B", "npc", "...알겠습니다. 행운을 빌죠."),
]


def wrap(ui, text, max_w=300):
    out, line = [], ""
    for word in text.split(" "):
        cand = word if not line else line + " " + word
        if sum(ui.width(c) for c in cand) <= max_w:
            line = cand
        else:
            out.append(line)
            line = word
    out.append(line)
    return out[:2]


def main():
    os.makedirs(OUT, exist_ok=True)
    _, _, bounds, grid, *_ = render_maps.load(os.path.join(ROOT, "build-out", "maps", "club.txt"))
    vox = CP.Voxels(bounds, grid)
    floor = CP.Y0 + 1
    # 댄스 플로어 위, 서로 마주 봄 (빈자리 확인)
    a_feet, b_feet = np.array([-1.0, floor, -4.5]), np.array([1.6, floor, -4.5])
    for f in (a_feet, b_feet):
        for dy in (0, 1):
            assert (int(math.floor(f[0])), int(f[1]) + dy, int(math.floor(f[2]))) not in grid, f"NPC 자리가 막힘 {f}"
    npcs = {"A": (a_feet, -90.0, "rooster"), "B": (b_feet, 90.0, "npc")}
    boxes = npc_boxes(a_feet, 1, "rooster") + npc_boxes(b_feet, -1, "npc")
    eyes = {k: v[0] + np.array([0, 1.62, 0]) for k, v in npcs.items()}
    ui = UI()

    # 이벤트 시간표 (틱)
    wide = (np.array([0.3, floor + 2.6, 3.2]), 180.0, 18.0)
    events = []
    t = 10
    for who, por, text in LINES:
        lines = wrap(ui, text)
        n = sum(len(x) for x in lines)
        events.append((t, who, por, lines, n))
        t += 26 + n + 22                                      # 등장 + 타자 + 읽을 시간
    end_t = t
    total = end_t + 20

    cam_pos, cam_yaw, cam_pitch = wide
    cam_from = cam_to = None
    move_start = -1
    panel_from, panel_target, panel_start, panel_dur = 1.0, 1.0, 0, 1
    portrait = pending = None
    bar, bar_target = 0, 8
    cur = None
    revealed = 0.0
    line_start = 0
    frames = []
    scene_cache = {}
    ev = list(events)

    def panel_pos(tk):
        return panel_from + (panel_target - panel_from) * out_expo((tk - panel_start) / panel_dur)

    for tk in range(total):
        # 이벤트: 다음 대사 (어드민 왼클릭)
        if ev and tk == ev[0][0]:
            _, who, por, lines, n = ev.pop(0)
            cur = (who, por, lines, n)
            revealed = 0.0
            line_start = tk
            c, yw, pt = shot_for(eyes[who], npcs[who][1])
            cam_from = (cam_pos.copy(), cam_yaw, cam_pitch)
            cam_to = (c, yw, pt)
            move_start = tk
            if portrait is None or panel_target >= 1:
                portrait = por
                panel_from, panel_target, panel_start, panel_dur = panel_pos(tk), 0.0, tk, PANEL_IN
            elif portrait != por:
                pending = por
                panel_from, panel_target, panel_start, panel_dur = panel_pos(tk), 1.0, tk, PANEL_OUT
        if tk == end_t:
            cur = None
            bar_target = 0
            panel_from, panel_target, panel_start, panel_dur = panel_pos(tk), 1.0, tk, PANEL_OUT
        # 매 틱 (DialogService.tick)
        if move_start >= 0:
            e = out_expo((tk - move_start) / MOVE_TICKS)
            cam_pos = cam_from[0] + (cam_to[0] - cam_from[0]) * e
            cam_yaw = lerp_angle(cam_from[1], cam_to[1], e)
            cam_pitch = cam_from[2] + (cam_to[2] - cam_from[2]) * e
            if tk - move_start >= MOVE_TICKS:
                move_start = -1
        if bar != bar_target:
            bar += 1 if bar < bar_target else -1
        if pending and panel_target >= 1 and tk - panel_start >= panel_dur:
            portrait, pending = pending, None
            panel_from, panel_target, panel_start, panel_dur = panel_pos(tk), 0.0, tk, PANEL_IN
        if cur and not pending and panel_target <= 0 and tk - panel_start >= PANEL_IN // 3:
            revealed = min(cur[3], revealed + 1.0)
        if tk % STEP:
            continue
        # 배경 (카메라가 멈춰 있으면 광선 추적 재사용)
        key = (round(cam_pos[0], 3), round(cam_pos[1], 3), round(cam_pos[2], 3), round(cam_yaw, 2), round(cam_pitch, 2))
        sc = scene_cache.get(key)
        if sc is None:
            sc = CP.Scene(vox, cam_pos, cam_yaw, cam_pitch)
            sc.samples = np.linspace(0.04, 1.0, 14)
            scene_cache = {key: sc}
        s = 8.2 + tk / 20.0
        bg = np.asarray(sc.frame(s)).reshape(-1, 3).astype(float) / 255.0
        nt, ncol = trace_boxes(sc.eye, sc.d, boxes)
        scene_t = np.where(sc.hit, sc.t, np.inf)
        front = nt < scene_t
        bg[front] = ncol[front]
        img = Image.fromarray((np.clip(bg, 0, 1).reshape(CP.H, CP.W, 3) * 255).astype(np.uint8)).resize((OW, OH), Image.BILINEAR).convert("RGBA")
        lines = cur[2] if cur else []
        ui.draw(img, bar, panel_pos(tk), portrait, sway(tk - line_start), lines, int(revealed))
        d = ImageDraw.Draw(img)
        d.text((8, 6), "시뮬레이션 (게임 캡처 아님) · 어드민 왼클릭으로 대사 넘김", font=ImageFont.truetype(FONT_KR, 14), fill=(255, 255, 255, 160))
        frames.append(img.convert("RGB"))
        print(f"\r{tk}/{total}", end="", flush=True)
    print()
    pal = [f.quantize(colors=200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    path = os.path.join(OUT, "dialog_npc.gif")
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=50 * STEP, loop=0, optimize=True)
    frames[len(frames) // 3].save(os.path.join(OUT, "dialog_still.png"))
    print(path, os.path.getsize(path) // 1024, "KB", len(frames), "장")


if __name__ == "__main__":
    main()
