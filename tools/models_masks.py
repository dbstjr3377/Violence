"""
가면 21종 (참고 그림을 복셀로 옮긴 모습).
좌표: 0..16 정육면체가 머리를 감싸고, 얼굴은 북쪽(-Z)을 향한다. 위는 +Y.
면 무늬는 painter 로 직접 그린다 (pt = 면 위의 3D 좌표).
"""
import math

from voxel import Material, Model, hnoise, rot

BLACK = (12, 10, 12)
WHITE = (245, 245, 240)


def fur(base, noise=0.12, edge=0.8):
    return Material(base, noise=noise, edge=edge, top=1.08)


def dark(c, k=0.6):
    return tuple(int(v * k) for v in c)


def light(c, k=1.25):
    return tuple(min(255, int(v * k)) for v in c)


def ellipse(px, py, cx, cy, rx, ry):
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1


def fur_streaks(base, seed=0, amt=0.18):
    """털 결 (세로 줄무늬 노이즈)"""
    def p(face, pt, fu, fv):
        n = hnoise(round(pt[0] * 3 + pt[2] * 3), round(pt[1] * 1.2), 0, seed)
        k = 1 + (n - 0.5) * amt * 2
        return tuple(max(0, min(255, int(v * k))) for v in base)
    return p


def chain(*ps):
    def p(face, pt, fu, fv):
        for q in ps:
            if q is None:
                continue
            c = q(face, pt, fu, fv)
            if c is not None:
                return c
        return None
    return p


def eyes_front(cx_list, cy, rx, ry, color=BLACK, pupil=None):
    """정면(north)의 눈 구멍"""
    def p(face, pt, fu, fv):
        if face != "north":
            return None
        for cx in cx_list:
            if ellipse(pt[0], pt[1], cx, cy, rx, ry):
                if pupil and ellipse(pt[0], pt[1], cx, cy, rx * 0.45, ry * 0.45):
                    return pupil
                return color
        return None
    return p


def eyes_side(cz, cy, rz, ry, color=BLACK, pupil=None, ring=None):
    """옆면(east/west)의 눈"""
    def p(face, pt, fu, fv):
        if face not in ("east", "west"):
            return None
        if ring and ellipse(pt[2], pt[1], cz, cy, rz * 1.3, ry * 1.3) and not ellipse(pt[2], pt[1], cz, cy, rz, ry):
            return ring
        if ellipse(pt[2], pt[1], cz, cy, rz, ry):
            if pupil and ellipse(pt[2], pt[1], cz, cy, rz * 0.5, ry * 0.5):
                return pupil
            return color
        return None
    return p


def spots(color, seed, freq=0.9, thresh=0.82):
    def p(face, pt, fu, fv):
        n = hnoise(int(pt[0] * freq), int(pt[1] * freq), int(pt[2] * freq), seed)
        if n > thresh:
            return color
        return None
    return p


def stripes(color, period=3.0, width=0.9, axis_mix=(1, 0.35, 0.6)):
    def p(face, pt, fu, fv):
        v = pt[1] * axis_mix[0] + pt[0] * axis_mix[1] + pt[2] * axis_mix[2] + math.sin(pt[0] + pt[2]) * 0.6
        if v % period < width:
            return color
        return None
    return p


def teeth_row(face_set, y_top, y_bot, x0, x1, axis="x", tooth=1.0, color=WHITE, gum=(150, 30, 60)):
    """이빨 줄 (뾰족한 송곳니 모양)"""
    def p(face, pt, fu, fv):
        if face not in face_set:
            return None
        a = pt[0] if axis == "x" else pt[2]
        if not (min(x0, x1) <= a <= max(x0, x1) and y_bot <= pt[1] <= y_top):
            return None
        phase = ((a - min(x0, x1)) % tooth) / tooth
        tip = abs(phase - 0.5) * 2
        h = (y_top - y_bot)
        if pt[1] >= y_top - h * (1 - tip * 0.85):
            return color
        return gum
    return p


# ───────────────────────── 가면 ─────────────────────────

def richard():
    m = Model("richard", seed=301)
    red = (225, 52, 48)
    m.box([0, 0, 0], [16, 16, 16], fur(red, 0.1),
          painter=chain(eyes_side(4.5, 10.5, 1.4, 1.2, BLACK, ring=(250, 230, 120)),
                        lambda f, p, u, v: (245, 245, 235) if f in ("east", "west") and ellipse(p[2], p[1], 7.5, 6.5, 1.3, 1.0) else None,
                        fur_streaks(red, 1, 0.12)))
    # 볏 (톱니)
    for i, (z0, h) in enumerate([(1, 5), (3.5, 7), (6, 6.2), (8.5, 7.4), (11, 5.6), (13, 4)]):
        m.box([6.4, 15.5, z0], [9.6, 16 + h, z0 + 2.6], fur((235, 40, 40), 0.08))
    m.box([6.6, 13, -1], [9.4, 18, 2], fur((235, 40, 40), 0.08))
    # 부리 (벌어짐)
    m.box([5.4, 7.6, -5], [10.6, 10.0, 0.2], Material((250, 200, 40), noise=0.05))
    m.box([6.0, 5.4, -3.6], [10.0, 6.8, 0.2], Material((240, 180, 30), noise=0.05))
    m.box([6.2, 6.8, -3.0], [9.8, 7.6, 0.1], Material((90, 10, 20), noise=0.05))
    # 볏 아래 육수
    m.box([6.4, 0.5, -2.6], [9.6, 5.4, 0.4], fur((210, 30, 36), 0.08))
    m.box([7.0, -2.0, -2.0], [9.0, 0.6, 0.2], fur((200, 26, 32), 0.08))
    return m


def don_juan():
    m = Model("don_juan", seed=302)
    gray = (128, 128, 134)
    m.box([0, 0, 0], [16, 16, 16], fur(gray), painter=chain(eyes_side(5.5, 10.5, 1.6, 1.1), fur_streaks(gray, 2)))
    m.box([3.0, 0.5, -9.5], [13.0, 9.5, 0.5], fur(gray), painter=chain(
        lambda f, p, u, v: BLACK if f == "north" and (ellipse(p[0], p[1], 5.4, 6.2, 1.0, 1.4) or ellipse(p[0], p[1], 10.6, 6.2, 1.0, 1.4)) else None,
        lambda f, p, u, v: (40, 40, 44) if f == "north" and abs(p[1] - 2.5) < 0.35 and abs(p[0] - 8) < 3 else None,
        lambda f, p, u, v: (98, 98, 104) if p[2] < -6.0 or f == "north" else None,
        fur_streaks(gray, 22)))
    # 귀
    m.box([2.5, 16, 7], [5.0, 21, 9], fur(gray))
    m.box([11.0, 16, 7], [13.5, 21, 9], fur(gray))
    # 갈기
    mane = fur((26, 26, 30), 0.15)
    m.box([6.0, 15.5, 3], [10.0, 19, 16.5], mane)
    m.box([6.5, 4, 15.5], [9.5, 17, 18.5], mane)
    m.box([4.5, 13, 0], [11.5, 17.5, 4], mane)
    return m


def graham():
    m = Model("graham", seed=303)
    orange = (220, 140, 66)
    m.box([0, 0, 0], [16, 16, 16], fur(orange), painter=chain(
        eyes_front([4.2, 11.8], 10.0, 2.0, 2.2, (40, 22, 12)),
        lambda f, p, u, v: light(orange, 1.18) if f == "north" and p[1] < 7 else None,
        lambda f, p, u, v: (120, 70, 40) if f == "north" and p[1] < 6 and int(p[0] * 2) % 3 == 0 and int(p[1] * 2) % 3 == 0 else None,
        fur_streaks(orange, 3)))
    # 귀 (긴, 안쪽 분홍)
    for x0 in (2.5, 10.0):
        m.box([x0, 16, 6], [x0 + 3.5, 30, 8.5], fur(orange), painter=lambda f, p, u, v, x0=x0: (240, 150, 160) if f == "north" and x0 + 0.7 < p[0] < x0 + 2.8 and 17 < p[1] < 29 else None)
    m.box([6.6, 5.6, -1.2], [9.4, 7.4, 0.2], Material((240, 130, 150), noise=0.04))   # 코
    m.box([6.4, 1.2, -0.8], [9.6, 4.8, 0.1], Material((248, 246, 236), noise=0.03),
          painter=lambda f, p, u, v: (150, 140, 120) if f == "north" and abs(p[0] - 8) < 0.15 else None)  # 앞니
    return m


def dennis():
    m = Model("dennis", seed=304)
    gray = (118, 118, 124)
    m.box([0, 0, 0], [16, 16, 16], fur(gray, 0.18), painter=chain(
        eyes_front([4.0, 12.0], 10.5, 1.6, 1.1, BLACK),
        lambda f, p, u, v: (200, 200, 205) if f == "north" and p[1] < 8 else None,
        fur_streaks(gray, 4, 0.25)))
    # 주둥이 + 벌린 입
    m.box([4.0, 5.2, -6.0], [12.0, 9.6, 0.5], fur((175, 175, 180)), painter=lambda f, p, u, v: BLACK if p[2] < -5 and p[1] > 7.6 and abs(p[0] - 8) < 1.6 else None)
    m.box([4.6, 4.2, -5.6], [11.4, 5.2, 0.4], Material((220, 70, 140), noise=0.06))       # 입 안/혀
    m.box([4.6, 3.2, -5.2], [11.4, 4.2, 0.4], fur((170, 170, 176)))
    m.box([4.8, 4.1, -5.9], [11.2, 5.4, -5.3], Material(WHITE, noise=0.02),
          painter=teeth_row(("north",), 5.4, 4.1, 4.8, 11.2, tooth=1.6, gum=(200, 60, 120)))
    m.box([2.0, 16, 6], [6.0, 21, 9], fur(gray, 0.15))
    m.box([10.0, 16, 6], [14.0, 21, 9], fur(gray, 0.15))
    # 볼 털
    m.box([-1.5, 2, 2], [0.5, 9, 10], fur((150, 150, 156), 0.2))
    m.box([15.5, 2, 2], [17.5, 9, 10], fur((150, 150, 156), 0.2))
    return m


def george():
    m = Model("george", seed=305)
    yel = (238, 214, 90)
    sp = spots((150, 90, 30), 5, 0.55, 0.78)
    m.box([0, 0, 0], [16, 16, 16], fur(yel, 0.06), painter=chain(eyes_side(4.5, 10.5, 1.3, 1.0), sp))
    m.box([3.5, 0.5, -7.0], [12.5, 8.0, 0.5], fur(yel, 0.06), painter=chain(
        lambda f, p, u, v: BLACK if f == "north" and (ellipse(p[0], p[1], 5.6, 4.8, 0.7, 1.2) or ellipse(p[0], p[1], 10.4, 4.8, 0.7, 1.2)) else None,
        lambda f, p, u, v: (210, 160, 70) if p[1] < 2.6 else None, sp))
    for x0 in (4.0, 10.5):
        m.box([x0, 16, 6], [x0 + 1.6, 22.5, 7.6], fur(yel, 0.05))
        m.box([x0 - 0.4, 22.5, 5.6], [x0 + 2.0, 24.5, 8.0], fur((110, 70, 30), 0.05))
    m.box([-3, 11, 7], [0, 13, 9], fur(yel))
    m.box([16, 11, 7], [19, 13, 9], fur(yel))
    return m


def rufus():
    m = Model("rufus", seed=306)
    teal = (60, 150, 162)
    wr = lambda f, p, u, v: dark(teal, 0.75) if int(p[1] * 1.3) % 3 == 0 and f not in ("up", "down") else None
    m.box([0, 0, 0], [16, 16, 16], fur(teal, 0.08), painter=chain(eyes_front([4.0, 12.0], 10.0, 1.3, 1.0), wr))
    # 큰 귀
    for x0, x1 in ((-6.5, 0.2), (15.8, 22.5)):
        m.box([x0, 2.0, 5.0], [x1, 15.0, 9.0], fur(dark(teal, 0.9), 0.08), painter=wr)
    # 코 (아래로 휨)
    m.box([5.5, 2.5, -3.0], [10.5, 8.5, 0.5], fur(teal, 0.08), painter=wr)
    m.box([6.0, -4.0, -4.0], [10.0, 3.0, -0.5], fur(teal, 0.08), painter=wr)
    m.box([6.4, -9.0, -5.0], [9.6, -3.5, -1.5], fur(teal, 0.08), painter=wr)
    m.box([6.6, -10.5, -6.2], [9.4, -8.6, -2.4], fur(dark(teal, 0.85), 0.08))
    # 상아
    ivory = Material((245, 240, 220), noise=0.03)
    for x0 in (2.8, 11.4):
        m.box([x0, 1.0, -2.5], [x0 + 1.8, 3.0, 0.5], ivory)
        m.box([x0, -3.0, -4.0], [x0 + 1.8, 1.5, -1.5], ivory)
        m.box([x0 + 0.2, -4.5, -5.6], [x0 + 1.6, -2.5, -3.6], ivory)
    return m


def rami():
    m = Model("rami", seed=307)
    tan = (226, 182, 112)
    hair = fur((150, 76, 36), 0.18)
    m.box([0, 0, 0], [16, 16, 16], fur(tan, 0.08), painter=chain(eyes_side(4.5, 10.0, 1.4, 1.0), fur_streaks(tan, 7)))
    m.box([3.5, 0, -8.5], [12.5, 8.5, 0.5], fur(tan, 0.08), painter=chain(
        lambda f, p, u, v: BLACK if f == "north" and (ellipse(p[0], p[1], 5.6, 5.5, 0.6, 1.0) or ellipse(p[0], p[1], 10.4, 5.5, 0.6, 1.0)) else None,
        lambda f, p, u, v: (190, 140, 80) if p[1] < 3 else None))
    m.box([4.0, -1.6, -7.0], [12.0, 0.4, 0.4], fur((200, 150, 90), 0.08))          # 늘어진 입술
    m.box([-0.8, 11, 0], [16.8, 18, 13], hair)                                       # 정수리 털
    m.box([-1.2, 2, 6], [0.4, 14, 17], hair)
    m.box([15.6, 2, 6], [17.2, 14, 17], hair)
    m.box([3, 17, 6], [5, 20, 8], fur(tan))
    m.box([11, 17, 6], [13, 20, 8], fur(tan))
    return m


def willem():
    m = Model("willem", seed=308)
    brown = (118, 72, 40)
    face = (218, 168, 120)
    m.box([0, 0, 0], [16, 16, 16], fur(brown, 0.14), painter=chain(
        lambda f, p, u, v: face if f == "north" and ellipse(p[0], p[1], 8, 7, 6.6, 6.8) else None,
        fur_streaks(brown, 8, 0.2)))
    m.box([2.5, 1.5, -1.6], [13.5, 13.0, 0.2], Material(face, noise=0.05), painter=chain(
        eyes_front([5.2, 10.8], 9.2, 1.6, 1.4, (40, 20, 10)),
        lambda f, p, u, v: dark(face, 0.75) if f == "north" and ellipse(p[0], p[1], 8, 5.4, 1.8, 0.8) else None,
        lambda f, p, u, v: (150, 80, 70) if f == "north" and abs(p[1] - 3.0) < 0.35 and abs(p[0] - 8) < 3.4 else None))
    m.box([2.8, 10.6, -2.2], [13.2, 12.2, -1.4], Material(dark(face, 0.82), noise=0.05))   # 눈썹뼈
    m.box([5.6, 3.6, -3.2], [10.4, 6.6, -1.4], Material(face, noise=0.05))                  # 입 부분
    for x0, x1 in ((-3.2, 0.2), (15.8, 19.2)):
        m.box([x0, 7, 6], [x1, 11.5, 9], Material(face, noise=0.06))
    return m


def peter():
    m = Model("peter", seed=309)
    wh = (246, 246, 250)
    m.box([0, 0, 0], [16, 16, 16], fur(wh, 0.03), painter=eyes_side(4.8, 10.5, 1.3, 1.1, (40, 140, 220), pupil=BLACK))
    m.box([3.5, 0.5, -8.0], [12.5, 9.0, 0.5], fur(wh, 0.03), painter=lambda f, p, u, v: (180, 180, 190) if f == "north" and (ellipse(p[0], p[1], 5.6, 5.0, 0.8, 1.2) or ellipse(p[0], p[1], 10.4, 5.0, 0.8, 1.2)) else None)
    spiral = lambda f, p, u, v: (205, 205, 215) if (p[1] + p[0] * 0.5 + p[2] * 0.5) % 1.6 < 0.5 else (250, 250, 255)
    m.box([6.7, 15.5, 0.5], [9.3, 21, 3.1], fur(wh), painter=spiral)
    m.box([7.1, 21, 0.9], [8.9, 26, 2.7], fur(wh), painter=spiral)
    m.box([7.5, 26, 1.3], [8.5, 30.5, 2.3], fur(wh), painter=spiral)
    mane = Material((236, 236, 244), noise=0.1)
    m.box([6, 13, 6], [10, 18, 17], mane)
    m.box([6.5, 2, 15.5], [9.5, 15, 18.5], mane)
    m.box([3, 16, 7], [5, 20, 9], fur(wh))
    m.box([11, 16, 7], [13, 20, 9], fur(wh))
    return m


def zack():
    m = Model("zack", seed=310)
    green = (112, 212, 60)
    sp = spots(dark(green, 0.7), 10, 0.6, 0.86)
    m.box([0, 0, 0], [16, 16, 16], fur(green, 0.06), painter=chain(
        lambda f, p, u, v: (236, 220, 120) if f == "north" and 2.0 < p[1] < 6.5 else None,
        lambda f, p, u, v: (60, 110, 30) if f == "north" and abs(p[1] - 4.2) < 0.4 else None, sp))
    m.box([-0.6, 1.5, -0.4], [16.6, 6.8, 13], fur(green, 0.06), painter=chain(
        lambda f, p, u, v: (236, 220, 120) if p[1] < 5.5 else None,
        lambda f, p, u, v: (60, 110, 30) if abs(p[1] - 4.2) < 0.4 and f != "up" else None))
    # 큰 눈
    for x0 in (0.5, 10.0):
        m.box([x0, 13, -1.5], [x0 + 5.5, 19.5, 5], fur(green, 0.06), painter=eyes_front([x0 + 2.75], 16.2, 2.3, 2.6, (250, 230, 60), pupil=BLACK))
    return m


def rick():
    m = Model("rick", seed=311)
    orng = (242, 122, 38)
    m.box([0, 0, 0], [16, 16, 16], fur(orng, 0.1), painter=chain(
        eyes_front([4.2, 11.8], 10.6, 1.5, 0.9, BLACK),
        lambda f, p, u, v: WHITE if f in ("north", "east", "west") and p[1] < 7 and (f != "north" or abs(p[0] - 8) > 2.4) else None,
        fur_streaks(orng, 11)))
    m.box([5.0, 2.5, -6.0], [11.0, 7.6, 0.3], fur(orng, 0.08), painter=lambda f, p, u, v: WHITE if p[1] < 4.5 else None)
    m.box([6.8, 6.0, -6.6], [9.2, 7.8, -5.6], Material(BLACK, noise=0.05))
    m.box([5.4, 2.0, -5.4], [10.6, 2.8, 0.2], Material((230, 110, 140), noise=0.05))
    for x0 in (1.5, 10.5):
        m.box([x0, 16, 6], [x0 + 4.0, 22, 9], fur(orng), painter=lambda f, p, u, v: BLACK if p[1] > 20 else None)
    return m


def brandon():
    m = Model("brandon", seed=312)
    purp = (112, 40, 140)
    m.box([0, 0, 0], [16, 16, 16], fur(purp, 0.1), painter=chain(eyes_front([4.2, 11.8], 10.6, 1.6, 0.9, (250, 210, 60), pupil=BLACK), fur_streaks(purp, 12)))
    m.box([4.0, 5.0, -4.0], [12.0, 9.5, 0.4], fur(dark(purp, 0.85)), painter=lambda f, p, u, v: (40, 10, 50) if p[1] > 8.4 and abs(p[0] - 8) < 1.4 and p[2] < -3.5 else None)
    m.box([4.4, 2.8, -3.6], [11.6, 5.0, 0.3], Material((220, 80, 160), noise=0.06))
    m.box([4.4, 4.4, -4.1], [11.6, 5.4, -3.5], Material(WHITE, noise=0.02), painter=teeth_row(("north",), 5.4, 4.4, 4.4, 11.6, tooth=1.8, gum=(200, 60, 140)))
    m.box([4.4, 2.4, -4.1], [11.6, 3.4, -3.5], Material(WHITE, noise=0.02))
    m.box([2.0, 16, 7], [5.0, 19, 9], fur(purp))
    m.box([11.0, 16, 7], [14.0, 19, 9], fur(purp))
    return m


def earl():
    m = Model("earl", seed=313)
    gray = (72, 70, 74)
    m.box([0, 0, 0], [16, 16, 16], fur(gray, 0.1), painter=chain(eyes_front([4.0, 12.0], 11.0, 0.9, 0.7, BLACK), fur_streaks(gray, 13)))
    whisk = lambda f, p, u, v: (240, 210, 90) if f in ("north", "east", "west", "down") and hnoise(int(p[0] * 2), int(p[1] * 2), int(p[2] * 2), 13) > 0.7 else None
    m.box([2.0, 2.0, -5.0], [14.0, 9.0, 0.5], fur((90, 86, 88), 0.1), painter=chain(whisk, lambda f, p, u, v: (210, 90, 120) if f == "north" and abs(p[0] - 8) < 1.6 and 2 < p[1] < 3.6 else None))
    ivory = Material((248, 244, 228), noise=0.03)
    for x0 in (3.6, 10.6):
        m.box([x0, -6.0, -4.0], [x0 + 1.8, 2.5, -2.0], ivory)
        m.box([x0 + 0.3, -10.0, -4.6], [x0 + 1.5, -6.0, -2.8], ivory)
    return m


def jake():
    m = Model("jake", seed=314)
    green = (88, 196, 70)
    scale_p = lambda f, p, u, v: dark(green, 0.78) if (int(p[0] * 1.8) + int(p[1] * 1.8) + int(p[2] * 1.8)) % 2 == 0 else None
    m.box([0, 0, 0], [16, 16, 16], fur(green, 0.08), painter=chain(eyes_front([3.8, 12.2], 11.0, 1.8, 1.0, (255, 220, 60), pupil=BLACK), scale_p))
    # 후드 (뒤로 넓게 펼쳐짐)
    hood = fur((70, 170, 56), 0.08)
    m.box([-6.5, -1, 9.5], [22.5, 19, 12.5], hood, painter=lambda f, p, u, v: (240, 150, 40) if (p[0] < -4.8 or p[0] > 20.8 or p[1] > 17.2) else scale_p(f, p, u, v))
    m.box([3.5, 4.0, -4.0], [12.5, 8.5, 0.4], fur(green), painter=scale_p)
    m.box([4.0, 2.0, -3.6], [12.0, 4.0, 0.2], Material((150, 40, 170), noise=0.05))
    m.box([5.0, 2.4, -4.0], [6.0, 4.0, -3.4], Material(WHITE, noise=0.02))      # 송곳니
    m.box([10.0, 2.4, -4.0], [11.0, 4.0, -3.4], Material(WHITE, noise=0.02))
    m.box([7.5, 1.0, -7.0], [8.5, 1.8, -3.6], Material((230, 40, 60), noise=0.04))  # 혀
    return m


def richter():
    m = Model("richter", seed=315)
    gray = (56, 56, 62)
    m.box([0, 0, 0], [16, 16, 16], fur(gray, 0.14), painter=chain(eyes_front([4.6, 11.4], 10.4, 1.2, 1.0, BLACK, pupil=(120, 30, 30)), fur_streaks(gray, 15, 0.24)))
    m.box([4.5, 2.5, -6.5], [11.5, 8.0, 0.3], fur(gray, 0.14))
    m.box([6.2, 4.4, -8.4], [9.8, 7.4, -6.4], fur(gray, 0.14))
    m.box([6.8, 5.6, -9.2], [9.2, 7.4, -8.3], Material((240, 140, 160), noise=0.04))
    m.box([7.0, 1.4, -6.0], [9.0, 2.6, -5.0], Material(WHITE, noise=0.02))
    whisk = Material((200, 200, 205), noise=0.02)
    m.box([1.0, 5.6, -6.0], [5.0, 5.8, -5.8], whisk)
    m.box([11.0, 5.6, -6.0], [15.0, 5.8, -5.8], whisk)
    pink = Material((236, 150, 170), noise=0.05)
    for x0 in (-0.5, 11.5):
        m.box([x0, 14.5, 5.5], [x0 + 5.0, 20.0, 7.5], fur(gray), painter=lambda f, p, u, v, x0=x0: (236, 150, 170) if f == "north" and x0 + 1 < p[0] < x0 + 4 and 15.5 < p[1] < 19 else None)
    _ = pink
    return m


def pig_butcher():
    m = Model("pig_butcher", seed=316)
    pale = (242, 228, 190)
    m.box([0, 0, 0], [16, 16, 16], fur(pale, 0.06), painter=chain(
        eyes_front([4.0, 12.0], 10.4, 1.5, 0.8, (60, 30, 20)),
        lambda f, p, u, v: (180, 40, 40) if hnoise(int(p[0] * 3), int(p[1] * 3), int(p[2] * 3), 16) > 0.93 else None))
    pink = (238, 150, 160)
    m.box([4.2, 3.0, -3.0], [11.8, 9.0, 0.4], Material(pink, noise=0.05),
          painter=lambda f, p, u, v: (120, 40, 50) if f == "north" and (ellipse(p[0], p[1], 6.4, 6, 0.8, 1.2) or ellipse(p[0], p[1], 9.6, 6, 0.8, 1.2)) else (dark(pink, 0.82) if f == "north" and int(p[1] * 2) % 3 == 0 else None))
    m.box([1.0, 16, 4], [5.5, 19.5, 8], fur(pale))
    m.box([10.5, 16, 4], [15.0, 19.5, 8], fur(pale))
    m.box([1.0, 14.5, 1.5], [5.5, 16.5, 4.5], fur(pale))   # 접힌 귀
    m.box([10.5, 14.5, 1.5], [15.0, 16.5, 4.5], fur(pale))
    return m


def cory():
    m = Model("cory", seed=317)
    st = stripes((26, 26, 30), 2.6, 1.0)
    m.box([0, 0, 0], [16, 16, 16], fur(WHITE, 0.04), painter=chain(eyes_side(5.0, 10.6, 1.4, 1.0, BLACK), st))
    m.box([3.5, 0.5, -8.5], [12.5, 9.0, 0.5], fur(WHITE, 0.04), painter=chain(lambda f, p, u, v: (26, 26, 30) if p[2] < -5.5 else None, st))
    mane = Material((26, 26, 30), noise=0.1)
    m.box([6.5, 15.5, 2], [9.5, 19.5, 17], mane, painter=lambda f, p, u, v: WHITE if int(p[2]) % 3 == 0 else None)
    m.box([3, 16, 6], [5, 20, 8], fur(WHITE))
    m.box([11, 16, 6], [13, 20, 8], fur(WHITE))
    return m


def mark():
    m = Model("mark", seed=318)
    blk = (34, 33, 36)
    m.box([0, 0, 0], [16, 16, 16], fur(blk, 0.18), painter=chain(eyes_front([4.2, 11.8], 10.6, 1.2, 0.9, (90, 40, 30)), fur_streaks(blk, 18, 0.3)))
    m.box([3.6, 2.0, -5.0], [12.4, 8.6, 0.4], fur((70, 60, 58), 0.12))
    m.box([5.6, 5.8, -5.8], [10.4, 8.4, -4.8], Material((230, 140, 150), noise=0.05))
    m.box([5.0, 1.6, -4.6], [11.0, 2.6, 0.2], Material((200, 70, 90), noise=0.05))
    for x0 in (0.6, 11.4):
        m.box([x0, 15.0, 6], [x0 + 4.0, 19.0, 9], fur(blk, 0.15))
    return m


def tony():
    m = Model("tony", seed=319)
    orng = (244, 172, 40)
    st = stripes((40, 20, 10), 3.2, 1.0, (1, 0.2, 0.15))
    m.box([0, 0, 0], [16, 16, 16], fur(orng, 0.08), painter=chain(
        eyes_front([4.2, 11.8], 10.8, 1.6, 0.9, BLACK),
        lambda f, p, u, v: (252, 240, 200) if f == "north" and p[1] < 8 and abs(p[0] - 8) > 2.6 else None, st))
    m.box([3.6, 5.0, -4.2], [12.4, 9.5, 0.4], fur((252, 240, 200), 0.05), painter=lambda f, p, u, v: (230, 110, 140) if f == "north" and p[1] > 8.2 and abs(p[0] - 8) < 1.4 else None)
    m.box([4.0, 2.4, -3.8], [12.0, 5.0, 0.3], Material((210, 50, 70), noise=0.06))
    m.box([4.0, 4.2, -4.3], [12.0, 5.2, -3.7], Material(WHITE, noise=0.02), painter=teeth_row(("north",), 5.2, 4.2, 4.0, 12.0, tooth=2.0, gum=(200, 50, 70)))
    m.box([4.0, 1.6, -4.0], [12.0, 2.6, 0.3], fur((252, 240, 200)))
    for x0 in (1.0, 11.0):
        m.box([x0, 16, 7], [x0 + 4.0, 19.5, 9], fur(orng), painter=lambda f, p, u, v: BLACK if p[1] > 18 else None)
    return m


def detective():
    m = Model("detective", seed=320)
    felt = Material((78, 60, 46), noise=0.08)
    m.box([-3.5, 13.4, -3.5], [19.5, 14.6, 19.5], felt)
    m.box([1.0, 14.6, 1.0], [15.0, 20.6, 15.0], felt, painter=lambda f, p, u, v: (30, 24, 20) if p[1] < 16.2 else None)
    m.box([4.5, 20.6, 2.0], [11.5, 21.4, 14.0], felt)
    m.box([1.5, 20.0, 4.0], [3.0, 21.0, 12.0], felt)
    m.box([13.0, 20.0, 4.0], [14.5, 21.0, 12.0], felt)
    return m


def biker():
    m = Model("biker", seed=321)
    shell = Material((232, 232, 236), noise=0.03, edge=0.86, spec=(255, 255, 255))
    m.box([-1, -1, -1], [17, 17, 17], shell,
          painter=lambda f, p, u, v: (200, 30, 40) if abs(p[0] - 8) < 1.4 and f in ("up", "north", "south") else None)
    m.box([0.5, 3.5, -1.6], [15.5, 11.5, -0.8], Material((20, 22, 30), noise=0.02, spec=(120, 140, 180)),
          painter=lambda f, p, u, v: (140, 160, 200) if f == "north" and abs((p[0] - p[1]) % 6 - 1) < 0.4 else None)
    m.box([-1.6, 5, 4], [-0.6, 9, 12], Material((60, 60, 66), noise=0.05))
    m.box([16.6, 5, 4], [17.6, 9, 12], Material((60, 60, 66), noise=0.05))
    return m


MASKS = {f.__name__: f for f in [richard, don_juan, graham, dennis, george, rufus, rami, willem, peter, zack, rick,
                                 brandon, earl, jake, richter, pig_butcher, cory, mark, tony, detective, biker]}
