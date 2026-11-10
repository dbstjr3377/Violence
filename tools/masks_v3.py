"""
가면 21종 (새로 만듦). 머리를 덮는 껍데기 + 주둥이·귀·뿔 같은 덧붙임 상자, 단색 칠하기.
- 눈: 검은 구멍 (개구리만 큰 노란 눈). 한 줄짜리 가는 눈이 아니라 2칸 이상 높이의 모양.
  눈가가 올라간 가면(호랑이·늑대·흑표범·여우·코브라·돼지·쥐)은 바깥 눈꼬리를 올리고 위를 비스듬히 자름.
- 무작위 노이즈 없음 (잡티 없음).
좌표: 머리 0~16, 얼굴 = -Z.
"""
from mask_kit import (BLACK, Mask, ellipse, eye, layers, on_faces, rect, shade, side_eye, spots,
                      stripes)

S0, S1 = -0.5, 16.5        # 머리 껍데기
F = S0                     # 얼굴 앞면 z
WHITE = (244, 242, 236)
PINK = (238, 128, 160)
MOUTH = (150, 30, 70)
YELLOW_BEAK = (246, 196, 52)


def shell(m, color, paint=None, top=S1, name="head"):
    m.add([S0, S0, S0], [S1, top, S1], color, paint, name=name)


def eyes(y=8.6, dx=3.6, rx=1.8, ry=1.85, tilt=0.0, cut=None, z_faces=("north",)):
    return [eye(8 - dx, y, rx, ry, tilt, faces=z_faces, cut_top=cut), eye(8 + dx, y, rx, ry, tilt, faces=z_faces, cut_top=cut)]


def fangs(x0, x1, y_top, n, h, color=WHITE, down=True):
    """정면 이빨 칠하기: 끝이 계단지지 않게 네모난 이빨 n 개 (양 끝은 길게 = 송곳니)"""
    step = (x1 - x0) / n

    def p(x, y, z, f):
        if f != "north" or not (x0 <= x <= x1):
            return None
        k = min(n - 1, int((x - x0) / step))
        if abs((x - x0) - (k + 0.5) * step) > step * 0.32:
            return None
        hh = h if k in (0, n - 1) else h * 0.55
        if down and y_top - hh <= y <= y_top:
            return color
        if not down and y_top <= y <= y_top + hh:
            return color
        return None
    return p


# ───────────────────────── 1. 리처드 (수탉) ─────────────────────────

def richard():
    m = Mask("richard")
    red, comb, white = (226, 58, 52), (204, 28, 36), WHITE
    shell(m, red, layers(*eyes(y=8.8, dx=3.8, rx=1.7, ry=1.4),
                         ellipse(1.0, 6.5, 1.3, 1.6, white, faces=("west",), axes="zy"),
                         ellipse(1.0, 6.5, 1.3, 1.6, white, faces=("east",), axes="zy")))
    # 볏: 이마에서 뒤통수까지 톱니 다섯 개
    for k, (z0, h) in enumerate([(-1.0, 4.2), (2.4, 5.6), (5.8, 6.0), (9.2, 5.0), (12.4, 3.6)]):
        m.add([6.2, S1, z0], [9.8, S1 + h, z0 + 3.0], comb, name=f"comb{k}")
    # 부리 (위아래 두 조각) + 육수
    m.add([5.6, 6.6, -4.4], [10.4, 8.2, S0], YELLOW_BEAK, name="beak_top")
    m.add([6.2, 5.4, -3.4], [9.8, 6.6, S0], shade(YELLOW_BEAK, 0.88), name="beak_low")
    m.add([6.4, 1.2, -1.6], [9.6, 5.4, S0], comb, name="wattle")
    return m


# ───────────────────────── 2. 돈 후안 (말) ─────────────────────────

def don_juan():
    m = Mask("don_juan")
    grey, dark, mane = (132, 134, 140), (96, 98, 104), (28, 28, 32)
    shell(m, grey, layers(side_eye(10.2, 4.2, 1.5, 1.6), *eyes(y=10.4, dx=5.2, rx=1.4, ry=1.3)))
    # 긴 주둥이 (앞으로 길게, 끝이 어두움)
    m.add([3.6, 0.5, -8.5], [12.4, 8.8, S0], grey,
          layers(ellipse(5.8, 3.6, 0.9, 1.2, BLACK), ellipse(10.2, 3.6, 0.9, 1.2, BLACK),
                 rect(3.6, 0.5, 12.4, 2.2, dark, faces=("north", "east", "west", "down"), axes="xy")), name="muzzle")
    # 귀
    m.add([2.0, S1, 9.0], [5.0, S1 + 4.0, 11.5], grey, name="ear_l")
    m.add([11.0, S1, 9.0], [14.0, S1 + 4.0, 11.5], grey, name="ear_r")
    # 갈기: 머리 위에서 뒤로
    m.add([6.4, S1, 2.0], [9.6, S1 + 1.6, 17.6], mane, name="mane_top")
    m.add([6.4, 2.0, S1], [9.6, S1 + 1.6, S1 + 1.6], mane, name="mane_back")
    return m


# ───────────────────────── 3. 그레이엄 (토끼) ─────────────────────────

def graham():
    m = Mask("graham")
    orange, inner = (226, 134, 58), (246, 168, 160)
    shell(m, orange, layers(*eyes(y=9.0, dx=3.8, rx=2.0, ry=1.7),
                            ellipse(8.0, 5.2, 1.2, 0.8, PINK)))
    # 앞니 두 개
    m.add([6.6, 1.0, -1.2], [7.9, 4.2, S0], WHITE, name="tooth_l")
    m.add([8.1, 1.0, -1.2], [9.4, 4.2, S0], WHITE, name="tooth_r")
    # 긴 귀 (앞면 안쪽이 분홍)
    for nm, x0 in (("ear_l", 2.6), ("ear_r", 10.4)):
        m.add([x0, S1, 6.0], [x0 + 3.0, S1 + 11.0, 8.0], orange,
              rect(x0 + 0.7, S1 + 0.8, x0 + 2.3, S1 + 10.2, inner, faces=("north",)), name=nm)
    return m


# ───────────────────────── 4. 데니스 (늑대) ─────────────────────────

def dennis():
    m = Mask("dennis")
    grey, light = (116, 118, 126), (196, 198, 204)
    shell(m, grey, layers(*eyes(y=9.4, dx=3.6, rx=2.0, ry=1.8, tilt=16, cut=0.55),
                          ellipse(8.0, 3.0, 6.0, 3.6, light)))
    # 주둥이 + 벌린 입 + 송곳니
    m.add([4.4, 0.4, -5.0], [11.6, 6.4, S0], light,
          layers(ellipse(8.0, 5.4, 1.6, 0.9, BLACK),
                 fangs(4.8, 11.2, 2.6, 3, 1.8, down=True), rect(4.8, 0.4, 11.2, 2.6, MOUTH)), name="muzzle")
    m.add([5.4, 4.6, -5.6], [10.6, 6.6, -4.9], BLACK, name="nose")
    for nm, x0 in (("ear_l", 0.6), ("ear_r", 11.4)):
        m.add([x0, S1, 5.0], [x0 + 4.0, S1 + 4.6, 7.0], grey,
              rect(x0 + 1.0, S1, x0 + 3.0, S1 + 3.4, (60, 60, 66)), name=nm)
    return m


# ───────────────────────── 5. 조지 (기린) ─────────────────────────

def george():
    m = Mask("george")
    yellow, brown = (244, 218, 84), (156, 94, 38)
    pts = [(2, 13, -0.5), (12, 3, -0.5), (16.5, 12, 4), (16.5, 4, 11), (-0.5, 10, 6), (-0.5, 3, 13),
           (6, 16.5, 9), (12, 16.5, 13), (8, 2, 16.5), (3, 7, 16.5), (13, 12, 16.5)]
    shell(m, yellow, layers(*eyes(y=9.6, dx=4.6, rx=1.5, ry=1.4), spots(pts, 1.9, brown)))
    m.add([4.0, 0.2, -7.0], [12.0, 7.0, S0], yellow,
          layers(ellipse(6.0, 4.0, 0.8, 1.0, BLACK), ellipse(10.0, 4.0, 0.8, 1.0, BLACK),
                 spots([(4.0, 3.6, -4.0), (12.0, 3.6, -3.4)], 1.4, brown, faces=("east", "west"))), name="muzzle")
    # 오시콘(작은 뿔) + 귀
    for nm, x0 in (("horn_l", 4.4), ("horn_r", 9.8)):
        m.add([x0, S1, 6.0], [x0 + 1.8, S1 + 4.2, 7.8], yellow,
              rect(x0, S1 + 3.0, x0 + 1.8, S1 + 4.2, brown, faces=("north", "south", "east", "west", "up")), name=nm)
    m.add([-2.6, 11.0, 7.0], [S0, 13.0, 9.6], yellow, name="ear_l")
    m.add([S1, 11.0, 7.0], [18.6, 13.0, 9.6], yellow, name="ear_r")
    return m


# ───────────────────────── 6. 루퍼스 (코끼리) ─────────────────────────

def rufus():
    m = Mask("rufus")
    teal, dark = (44, 152, 164), (30, 110, 120)
    shell(m, teal, layers(*eyes(y=9.6, dx=4.2, rx=1.6, ry=1.4)))
    # 코: 세 마디가 아래로 길게
    m.add([5.6, 2.0, -3.0], [10.4, 8.0, S0], teal, name="trunk1")
    m.add([6.0, -2.6, -3.4], [10.0, 2.0, -0.4], teal, name="trunk2")
    m.add([6.4, -6.4, -3.8], [9.6, -2.6, -1.0], teal,
          rect(6.4, -6.4, 9.6, -5.6, dark, faces=("north", "east", "west", "south", "down")), name="trunk3")
    # 상아
    m.add([2.6, -1.6, -2.6], [4.2, 3.0, -0.8], WHITE, name="tusk_l")
    m.add([11.8, -1.6, -2.6], [13.4, 3.0, -0.8], WHITE, name="tusk_r")
    # 큰 귀
    m.add([-3.0, 3.0, 4.0], [S0, 15.0, 9.0], teal, rect(-3.0, 4.0, S0, 14.0, dark, faces=("north",)), name="ear_l")
    m.add([S1, 3.0, 4.0], [19.0, 15.0, 9.0], teal, rect(S1, 4.0, 19.0, 14.0, dark, faces=("north",)), name="ear_r")
    return m


# ───────────────────────── 7. 라미 (낙타) ─────────────────────────

def rami():
    m = Mask("rami")
    tan, cream, hair = (196, 120, 50), (242, 206, 138), (150, 78, 30)
    shell(m, tan, layers(*eyes(y=9.6, dx=3.8, rx=1.6, ry=1.4), rect(S0, S0, S1, 7.0, cream)))
    m.add([3.6, 0.0, -7.4], [12.4, 7.0, S0], cream,
          layers(ellipse(5.8, 4.6, 0.8, 1.1, BLACK), ellipse(10.2, 4.6, 0.8, 1.1, BLACK),
                 rect(4.4, 0.0, 11.6, 1.4, (120, 60, 50))), name="muzzle")
    # 머리 위 털 뭉치 + 귀
    m.add([2.0, S1, 1.0], [14.0, S1 + 2.4, 12.0], hair, name="tuft")
    m.add([-1.6, 11.0, 6.0], [S0, 14.0, 8.4], tan, name="ear_l")
    m.add([S1, 11.0, 6.0], [17.6, 14.0, 8.4], tan, name="ear_r")
    return m


# ───────────────────────── 8. 윌럼 (원숭이) ─────────────────────────

def willem():
    m = Mask("willem")
    fur, face, lip = (110, 66, 30), (226, 176, 116), (198, 132, 98)
    face_p = ellipse(8.0, 7.0, 6.4, 6.8, face)
    shell(m, fur, layers(*eyes(y=9.2, dx=3.0, rx=1.9, ry=1.9), rect(4.0, 2.4, 12.0, 3.6, lip), face_p))
    # 이마 털, 입 주변 돌출, 귀
    m.add([5.0, 1.6, -1.8], [11.0, 6.0, S0], face,
          layers(rect(5.0, 2.8, 11.0, 3.4, lip), ellipse(7.0, 5.2, 0.5, 0.5, (150, 100, 70)),
                 ellipse(9.0, 5.2, 0.5, 0.5, (150, 100, 70))), name="mouth")
    m.add([-2.4, 6.0, 6.0], [S0, 11.0, 9.0], face, name="ear_l")
    m.add([S1, 6.0, 6.0], [18.4, 11.0, 9.0], face, name="ear_r")
    return m


# ───────────────────────── 9. 피터 (유니콘) ─────────────────────────

def peter():
    m = Mask("peter")
    white, mane, horn = (242, 244, 248), (150, 210, 236), (236, 226, 190)
    shell(m, white, layers(side_eye(10.0, 4.2, 1.5, 1.6), *eyes(y=10.4, dx=5.0, rx=1.4, ry=1.3)))
    m.add([3.8, 0.6, -7.6], [12.2, 8.6, S0], white,
          layers(ellipse(6.0, 3.6, 0.8, 1.1, (90, 90, 100)), ellipse(10.0, 3.6, 0.8, 1.1, (90, 90, 100))), name="muzzle")
    # 뿔: 세 마디로 가늘어지며 앞으로 기울어짐
    for k, (w, h) in enumerate([(3.0, 3.0), (2.2, 3.0), (1.4, 3.0)]):
        y0 = S1 + k * 3.0
        m.add([8 - w / 2, y0, 2.0 - w / 2 - k * 1.2], [8 + w / 2, y0 + h, 2.0 + w / 2 - k * 1.2], horn,
              rect(0, y0 + 1.2, 16, y0 + 1.8, shade(horn, 0.86), faces=("north", "south", "east", "west")), name=f"horn{k}")
    m.add([6.2, S1, 5.0], [9.8, S1 + 1.8, 17.2], mane, name="mane_top")
    m.add([6.2, 1.0, S1], [9.8, S1 + 1.8, S1 + 1.8], mane, name="mane_back")
    m.add([2.4, S1, 9.0], [5.0, S1 + 3.4, 11.0], white, name="ear_l")
    m.add([11.0, S1, 9.0], [13.6, S1 + 3.4, 11.0], white, name="ear_r")
    return m


# ───────────────────────── 10. 잭 (개구리, 큰 눈) ─────────────────────────

def zack():
    m = Mask("zack")
    green, lip, eye_y = (108, 210, 44), (238, 214, 80), (250, 226, 40)
    shell(m, green, layers(rect(S0, 3.6, S1, 4.6, lip, faces=("north", "east", "west")),
                           rect(S0, S0, S1, 3.6, (232, 210, 110), faces=("north", "east", "west", "down"))))
    # 머리 위로 튀어나온 큰 눈 (노란 눈알 + 검은 가로 동공)
    for nm, x0 in (("eye_l", 0.6), ("eye_r", 10.4)):
        pupil = rect(x0 + 0.8, S1 + 1.6, x0 + 4.2, S1 + 3.0, BLACK, faces=("north",))
        m.add([x0, S1 - 2.0, -0.8], [x0 + 5.0, S1 + 4.0, 4.2], eye_y,
              layers(pupil, rect(0, S1 - 2.0, 20, S1 - 0.6, green, faces=("north", "east", "west", "south"))), name=nm)
    return m


# ───────────────────────── 11. 릭 (여우) ─────────────────────────

def rick():
    m = Mask("rick")
    orange, white, dark = (240, 128, 30), WHITE, (60, 36, 24)
    shell(m, orange, layers(*eyes(y=9.4, dx=3.6, rx=2.0, ry=1.8, tilt=20, cut=0.55),
                            ellipse(8.0, 2.4, 7.0, 4.0, white)))
    m.add([5.0, 0.6, -6.0], [11.0, 5.6, S0], white,
          layers(rect(6.6, 4.0, 9.4, 5.6, BLACK, faces=("north", "up")), rect(5.0, 0.6, 11.0, 1.4, (200, 70, 90))), name="muzzle")
    m.add([5.0, 5.6, -5.0], [11.0, 7.0, S0], orange, name="bridge")
    for nm, x0 in (("ear_l", 0.4), ("ear_r", 11.6)):
        m.add([x0, S1, 5.0], [x0 + 4.0, S1 + 5.0, 7.0], orange,
              layers(rect(x0, S1 + 3.4, x0 + 4.0, S1 + 5.0, dark, faces=("north", "south", "east", "west", "up")),
                     rect(x0 + 1.0, S1, x0 + 3.0, S1 + 3.4, white)), name=nm)
    return m


# ───────────────────────── 12. 브랜던 (흑표범) ─────────────────────────

def brandon():
    m = Mask("brandon")
    purple, dark = (118, 40, 140), (82, 24, 100)
    shell(m, purple, layers(*eyes(y=9.6, dx=3.8, rx=2.2, ry=1.8, tilt=18, cut=0.55)))
    m.add([4.0, 0.4, -4.4], [12.0, 6.4, S0], purple,
          layers(rect(6.6, 5.0, 9.4, 6.4, (220, 120, 200), faces=("north", "up")),
                 fangs(4.4, 11.6, 3.2, 3, 1.8, down=True), rect(4.4, 0.4, 11.6, 3.2, MOUTH)), name="muzzle")
    for nm, x0 in (("ear_l", 0.8), ("ear_r", 11.6)):
        m.add([x0, S1, 6.0], [x0 + 3.6, S1 + 2.8, 8.0], purple, rect(x0 + 0.8, S1, x0 + 2.8, S1 + 2.0, dark), name=nm)
    return m


# ───────────────────────── 13. 얼 (바다코끼리) ─────────────────────────

def earl():
    m = Mask("earl")
    grey, whisk, pink = (74, 74, 80), (214, 190, 110), (230, 150, 150)
    shell(m, grey, layers(*eyes(y=10.0, dx=3.8, rx=1.6, ry=1.4)))
    pad = shade(grey, 1.35)
    lines = [rect(x0, y, x0 + 3.0, y + 0.5, whisk) for x0 in (2.8, 10.2) for y in (1.6, 3.0, 4.4)]
    m.add([2.4, 0.6, -2.6], [13.6, 6.6, S0], pad,
          layers(rect(6.4, 5.0, 9.6, 6.6, pink, faces=("north", "up")), *lines), name="muzzle")
    m.add([4.2, -6.0, -2.4], [5.8, 1.0, -0.8], WHITE, name="tusk_l")
    m.add([10.2, -6.0, -2.4], [11.8, 1.0, -0.8], WHITE, name="tusk_r")
    return m


# ───────────────────────── 14. 제이크 (코브라) ─────────────────────────

def jake():
    m = Mask("jake")
    green, hood, belly = (64, 200, 70), (226, 142, 44), (232, 214, 120)
    shell(m, green, layers(*eyes(y=10.0, dx=3.6, rx=2.0, ry=1.8, tilt=22, cut=0.55),
                           rect(6.0, S0, 10.0, 6.0, belly)))
    m.add([3.6, 0.6, -4.0], [12.4, 6.0, S0], green,
          layers(fangs(4.4, 11.6, 3.6, 2, 2.4, down=True), rect(4.4, 0.6, 11.6, 3.6, MOUTH),
                 rect(6.2, 4.6, 7.4, 5.4, BLACK), rect(8.6, 4.6, 9.8, 5.4, BLACK)), name="muzzle")
    # 머리를 둘러싼 후드 (옆·뒤로 넓게)
    m.add([-3.0, -2.0, 6.0], [S0, 18.0, 13.0], hood, rect(-3.0, -2.0, S0, 18.0, green, faces=("west",)), name="hood_l")
    m.add([S1, -2.0, 6.0], [19.0, 18.0, 13.0], hood, rect(S1, -2.0, 19.0, 18.0, green, faces=("east",)), name="hood_r")
    m.add([-3.0, S1, 6.0], [19.0, 19.0, 13.0], hood, name="hood_top")
    return m


# ───────────────────────── 15. 리히터 (쥐) ─────────────────────────

def richter():
    m = Mask("richter")
    fur, pink = (54, 54, 60), (236, 164, 176)
    shell(m, fur, layers(*eyes(y=9.6, dx=3.4, rx=1.8, ry=1.8, tilt=14, cut=0.55)))
    m.add([4.6, 1.0, -6.4], [11.4, 6.6, S0], fur,
          layers(rect(6.6, 4.8, 9.4, 6.6, pink, faces=("north", "up")),
                 rect(6.8, 1.0, 9.2, 2.6, WHITE)), name="snout")
    for nm, x0 in (("ear_l", -0.6), ("ear_r", 11.6)):
        m.add([x0, S1 - 1.0, 7.0], [x0 + 5.0, S1 + 4.0, 8.6], fur,
              ellipse(x0 + 2.5, S1 + 1.6, 1.8, 2.0, pink), name=nm)
    return m


# ───────────────────────── 16. 돼지 학살자 (돼지) ─────────────────────────

def pig_butcher():
    m = Mask("pig_butcher")
    skin, snout = (246, 232, 196), (240, 152, 150)
    shell(m, skin, layers(*eyes(y=9.6, dx=3.8, rx=2.0, ry=1.8, tilt=18, cut=0.55)))
    m.add([4.4, 2.0, -3.6], [11.6, 7.6, S0], snout,
          layers(ellipse(6.6, 4.8, 0.8, 1.3, (110, 50, 56)), ellipse(9.4, 4.8, 0.8, 1.3, (110, 50, 56))), name="snout")
    for nm, x0, xr in (("ear_l", 0.0, -1), ("ear_r", 12.0, 1)):
        m.add([x0, S1 - 0.5, 4.0], [x0 + 4.0, S1 + 3.6, 6.4], skin,
              rect(x0 + 1.0, S1, x0 + 3.0, S1 + 2.6, (236, 190, 170)),
              rot={"axis": "z", "angle": 22.5 * xr, "origin": [x0 + 2.0, S1, 5.0]}, name=nm)
    return m


# ───────────────────────── 17. 코리 (얼룩말) ─────────────────────────

def cory():
    m = Mask("cory")
    white, black = (240, 240, 240), (24, 24, 28)
    st = stripes(black, period=3.0, width=1.5, angle_deg=0, wobble=0.0, faces=("east", "west", "south", "up", "north"))
    shell(m, white, layers(*eyes(y=10.4, dx=5.0, rx=1.4, ry=1.3), side_eye(10.2, 4.2, 1.5, 1.6),
                           rect(5.6, 11.6, 10.4, S1, white), st))
    m.add([3.8, 0.6, -7.6], [12.2, 8.6, S0], white,
          layers(rect(3.8, 0.6, 12.2, 3.6, black, faces=("north", "east", "west", "down", "up")),
                 stripes(black, 3.0, 1.5, angle_deg=0, faces=("east", "west"))), name="muzzle")
    m.add([6.4, S1, 2.0], [9.6, S1 + 2.0, 17.6], black,
          name="mane")
    m.add([2.4, S1, 9.0], [5.0, S1 + 3.6, 11.0], white, name="ear_l")
    m.add([11.0, S1, 9.0], [13.6, S1 + 3.6, 11.0], white, name="ear_r")
    return m


# ───────────────────────── 18. 마크 (곰) ─────────────────────────

def mark():
    m = Mask("mark")
    brown, muzzle = (104, 66, 38), (186, 136, 88)
    shell(m, brown, layers(*eyes(y=9.6, dx=3.6, rx=1.8, ry=1.5)))
    m.add([4.4, 1.0, -4.0], [11.6, 7.0, S0], muzzle,
          layers(rect(6.4, 4.8, 9.6, 7.0, BLACK, faces=("north", "up")), rect(7.6, 2.4, 8.4, 4.8, (90, 56, 40)),
                 rect(5.6, 1.6, 10.4, 2.4, (90, 56, 40))), name="muzzle")
    for nm, x0 in (("ear_l", 0.6), ("ear_r", 11.4)):
        m.add([x0, S1 - 0.6, 6.0], [x0 + 4.0, S1 + 3.0, 8.2], brown,
              ellipse(x0 + 2.0, S1 + 0.8, 1.2, 1.2, muzzle), name=nm)
    return m


# ───────────────────────── 19. 토니 (호랑이) ─────────────────────────

def tony():
    m = Mask("tony")
    gold, stripe, light = (248, 194, 40), (226, 104, 20), (252, 238, 170)
    st = stripes(stripe, period=3.6, width=1.5, angle_deg=0, wobble=0.0, faces=("east", "west", "south"))
    fore = layers(rect(7.2, 12.0, 8.8, S1, stripe), rect(4.6, 13.4, 6.0, S1, stripe), rect(10.0, 13.4, 11.4, S1, stripe))
    shell(m, gold, layers(*eyes(y=9.6, dx=3.8, rx=2.2, ry=1.8, tilt=20, cut=0.55), fore, st,
                          ellipse(8.0, 2.6, 6.6, 3.4, light)))
    m.add([3.8, 0.2, -4.6], [12.2, 6.6, S0], light,
          layers(rect(6.4, 5.0, 9.6, 6.6, (210, 90, 110), faces=("north", "up")),
                 fangs(4.4, 11.6, 3.4, 3, 2.0, down=True), rect(4.4, 0.2, 11.6, 3.4, MOUTH)), name="muzzle")
    for nm, x0 in (("ear_l", 0.6), ("ear_r", 11.8)):
        m.add([x0, S1, 6.0], [x0 + 3.6, S1 + 2.6, 8.0], gold, rect(x0 + 0.8, S1, x0 + 2.8, S1 + 1.8, light), name=nm)
    return m


# ───────────────────────── 20. 형사 (중절모) ─────────────────────────

def detective():
    m = Mask("detective")
    felt, band = (78, 58, 44), (32, 24, 20)
    m.add([-3.4, 14.6, -3.4], [19.4, 15.8, 19.4], felt, name="brim")
    m.add([0.4, 15.8, 0.4], [15.6, 20.6, 15.6], felt,
          layers(rect(0, 15.8, 16, 17.2, band, faces=("north", "south", "east", "west")),
                 rect(7.0, 20.6, 9.0, 20.6, shade(felt, 0.8), faces=("up",))), name="crown")
    m.add([5.6, 20.6, 2.0], [10.4, 21.2, 14.0], shade(felt, 0.9), name="pinch")
    return m


# ───────────────────────── 21. 바이커 (헬멧) ─────────────────────────

def biker():
    m = Mask("biker")
    shell_c, visor, trim = (196, 40, 168), (16, 16, 22), (240, 240, 244)
    stripe = rect(7.0, S0, 9.0, S1, trim, faces=("up",), axes="xz")
    shell(m, shell_c, layers(rect(1.0, 4.6, 15.0, 11.6, visor), stripe,
                             rect(7.0, 11.6, 9.0, S1, trim, faces=("north",)),
                             rect(7.0, S0, 9.0, S1, trim, faces=("south",), axes="xy")))
    m.add([-1.2, 4.0, -1.2], [17.2, 12.2, S0], visor, rect(-1.2, 10.6, 17.2, 12.2, shell_c), name="visor")
    m.add([-1.2, -1.2, -1.2], [17.2, 4.0, S0], shell_c, name="chin")
    return m


MASKS = {f.__name__: f for f in [richard, don_juan, graham, dennis, george, rufus, rami, willem, peter, zack, rick,
                                 brandon, earl, jake, richter, pig_butcher, cory, mark, tony, detective, biker]}
