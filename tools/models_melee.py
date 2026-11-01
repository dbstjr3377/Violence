"""근접/투척 무기 모델. 좌표: 손잡이가 아래(y 0~8), 날/머리가 +Y. 중심 x=8, z=8."""
from voxel import Model, disc, flat, octagon_rod, rot

def rod(m, y0, y1, r, mat, painter=None, x=8, z=8):
    return octagon_rod(m, "y", x, z, r, y0, y1, mat, painter=painter)


def wrap(period=0.8, dark=(20, 20, 22)):
    """손잡이 감은 테이프/끈 무늬"""
    def p(face, pt, fu, fv):
        if face in ("up", "down"):
            return None
        if (pt[1] + (pt[0] + pt[2]) * 0.4) % period < period * 0.3:
            return dark
        return None
    return p


def edge_line(face_set=("north", "south"), color=(240, 244, 250), lo=0.0, hi=0.18):
    """날 끝 쪽 밝은 줄 (연마면)"""
    def p(face, pt, fu, fv):
        if face in face_set and lo <= fu <= hi:
            return color
        return None
    return p


def dagger(m=None, scale=1.0):
    m = m or Model("dagger", seed=101, auto_round=0.16)
    rod(m, 0.6, 6.8, 0.85, "rubber", painter=wrap(0.9))
    m.box([7.1, 0, 7.1], [8.9, 0.7, 8.9], "dark_steel")
    m.box([5.8, 6.8, 7.3], [10.2, 7.6, 8.7], "dark_steel")
    m.box([7.25, 7.6, 7.65], [8.75, 15.0, 8.35], "blade", painter=edge_line(("north", "south"), lo=0.82, hi=1.0))
    m.box([7.9, 8.4, 7.62], [8.1, 13.6, 8.38], "blade_dark")   # 피 홈
    m.box([7.25, 15.0, 7.7], [8.4, 16.4, 8.3], "blade", rot=rot("z", -22.5, [7.25, 15.0, 8]))
    return m


def bat():
    m = Model("bat", seed=102, auto_round=0.16)
    rod(m, 0, 0.8, 1.3, "wood_dark_y")
    rod(m, 0.8, 7.5, 0.75, "tape", painter=wrap(0.7, (30, 30, 34)))
    rod(m, 7.5, 12, 0.85, "wood_y")
    rod(m, 12, 17, 1.1, "wood_y")
    rod(m, 17, 23, 1.4, "wood_light_y")
    rod(m, 23, 28, 1.55, "wood_light_y", painter=lambda f, p, u, v: (40, 24, 14) if f == "north" and 24.5 < p[1] < 26 and abs(p[0] - 8) < 0.8 else None)
    rod(m, 28, 28.6, 1.3, "wood_light_y")
    return m


def pipe():
    m = Model("pipe", seed=103, auto_round=0.16)
    rust = lambda f, p, u, v: (120, 64, 34) if (int(p[1] * 2.3) * 7 + int(p[0] * 3)) % 11 == 0 else None
    rod(m, 0, 27, 0.8, "dark_steel", painter=rust)
    rod(m, 0, 1.6, 1.05, "steel", painter=lambda f, p, u, v: (70, 72, 78) if int(p[1] * 4) % 2 == 0 else None)
    rod(m, 25.4, 27.4, 1.15, "steel")
    m.box([6.6, 26.9, 6.6], [9.4, 27.6, 9.4], "dark_steel")
    return m


def golf_club():
    m = Model("golf_club", seed=104, auto_round=0.16)
    rod(m, 0, 8, 0.75, "grip")
    rod(m, 8, 25.5, 0.38, "chrome")
    m.box([7.4, 24.5, 7.0], [8.6, 26.8, 9.0], "chrome")
    m.box([7.2, 24.2, 3.2], [8.8, 26.6, 9.0], "chrome", rot=rot("x", -22.5, [8, 24.5, 8]),
          painter=lambda f, p, u, v: (60, 62, 68) if f in ("east",) and int(p[1] * 4) % 2 == 0 else None)
    return m


def fire_axe():
    m = Model("fire_axe", seed=105, auto_round=0.16)
    rod(m, 0, 26, 0.75, "red_paint")
    rod(m, 0, 4.5, 0.9, "rubber")
    m.box([7.3, 21, 3.6], [8.7, 26.2, 9.4], "red_paint")                      # 도끼 머리
    m.box([7.45, 20.2, 1.6], [8.55, 27.0, 3.6], "steel", painter=edge_line(("east", "west"), (235, 238, 245), 0.0, 0.3))
    m.box([7.5, 22.6, 9.4], [8.5, 24.6, 13.2], "red_paint")                   # 뒤쪽 뿔
    m.box([7.65, 22.9, 13.2], [8.35, 24.3, 14.4], "steel")
    return m


def machete():
    m = Model("machete", seed=106, auto_round=0.16)
    m.box([7.25, 0, 7.15], [8.75, 6.6, 8.85], "polymer", painter=lambda f, p, u, v: (150, 150, 155) if f in ("east", "west") and abs(p[1] - 1.8) < 0.3 and abs(p[2] - 8) < 0.3 or (f in ("east", "west") and abs(p[1] - 4.6) < 0.3 and abs(p[2] - 8) < 0.3) else None)
    m.box([7.1, 6.6, 6.9], [8.9, 7.2, 9.1], "dark_steel")
    m.box([7.65, 7.2, 6.6], [8.35, 22.5, 9.9], "blade", painter=edge_line(("east", "west"), (245, 248, 252), 0.0, 0.16))
    m.box([7.65, 21.0, 7.4], [8.35, 25.5, 10.2], "blade", rot=rot("x", -22.5, [8, 22.5, 9.9]))
    return m


def pot():
    m = Model("pot", seed=107, auto_round=0.16)
    rod(m, 0, 9, 0.65, "black")
    m.box([7.5, 7.5, 7.5], [8.5, 10.2, 8.5], "steel")
    disc(m, "y", 8, 13, 8, 5.2, 6.0, "steel")
    disc(m, "y", 8, 16.1, 8, 5.5, 0.4, "chrome")
    disc(m, "y", 8, 15.9, 8, 4.6, 0.2, flat((30, 30, 34)))
    return m


def frying_pan():
    m = Model("frying_pan", seed=108, auto_round=0.16)
    rod(m, 0, 11, 0.7, "black")
    m.box([7.4, 1.0, 7.4], [8.6, 1.8, 8.6], flat((12, 12, 12)))
    m.box([7.5, 10.4, 7.6], [8.5, 12.4, 8.4], "dark_steel")
    disc(m, "z", 8, 18.5, 8.2, 6.2, 1.2, "anodized")
    disc(m, "z", 8, 18.5, 7.55, 5.4, 0.2, flat((22, 22, 24)))
    return m


def crowbar():
    m = Model("crowbar", seed=109, auto_round=0.16)
    m.box([7.4, 0.8, 7.4], [8.6, 21.5, 8.6], "red_paint")
    m.box([7.4, 21.0, 7.4], [8.6, 23.0, 9.6], "red_paint", rot=rot("x", 45, [8, 21.5, 8]))
    m.box([7.4, 21.5, 9.2], [8.6, 22.6, 12.2], "red_paint")
    m.box([7.4, 19.6, 11.2], [8.6, 22.6, 12.4], "red_paint")
    m.box([7.55, 18.6, 11.4], [8.45, 19.6, 12.2], "steel")
    m.box([7.45, 0, 7.45], [8.55, 1.2, 10.2], "red_paint", rot=rot("x", -22.5, [8, 0.8, 8]))
    m.box([7.6, -0.2, 10.0], [8.4, 0.7, 11.0], "steel")
    return m


def katana():
    m = Model("katana", seed=110, auto_round=0.16)
    diamond = lambda f, p, u, v: (210, 30, 40) if f != "up" and f != "down" and (int(p[1] * 2.2) + int((p[0] + p[2]) * 2.2)) % 3 == 0 else None
    m.box([7.25, 0.3, 7.25], [8.75, 7.0, 8.75], "cloth_black", painter=diamond)
    m.box([7.15, 0, 7.15], [8.85, 0.5, 8.85], "gold")
    disc(m, "y", 8, 7.3, 8, 2.3, 0.6, "gold")
    m.box([7.3, 7.6, 7.2], [8.7, 8.6, 8.8], "gold")
    hamon = lambda f, p, u, v: (250, 252, 255) if f in ("north", "south") and fu_wave(p) else None
    m.box([7.72, 8.6, 7.25], [8.28, 30.0, 8.75], "blade", painter=hamon)
    m.box([7.72, 29.0, 7.3], [8.28, 31.6, 8.5], "blade", rot=rot("x", 22.5, [8, 30, 8.75]))
    return m


def fu_wave(p):
    import math
    return (p[2] - 7.25) < 0.45 + 0.12 * math.sin(p[1] * 2.5)


def baton():
    m = Model("baton", seed=111, auto_round=0.16)
    rod(m, 0, 8, 0.85, "foam")
    m.box([7.2, 0, 7.2], [8.8, 0.5, 8.8], "dark_steel")
    rod(m, 8, 16, 0.55, "black")
    rod(m, 16, 23, 0.42, "dark_steel")
    rod(m, 23, 24, 0.7, "chrome")
    return m


def hammer(name="hammer", short=False):
    m = Model(name, seed=112 + short, auto_round=0.16)
    top = 9.5 if short else 15
    rod(m, 0, top, 0.7 if short else 0.8, "wood_y")
    rod(m, 0, 4 if short else 6, 0.95, "grip")
    m.box([7.0, top - 0.6, 5.0], [9.0, top + 2.2, 10.0], "dark_steel")
    m.box([7.2, top - 0.3, 3.4], [8.8, top + 1.9, 5.0], "steel")            # 치는 면
    m.box([7.35, top + 0.2, 10.0], [8.65, top + 1.8, 13.0], "dark_steel", rot=rot("x", -22.5, [8, top + 1, 10]))
    return m


def briefcase():
    m = Model("briefcase", seed=114, auto_round=0.16)
    m.box([1.5, 1.5, 6.4], [14.5, 12.5, 9.6], "leather")
    m.box([1.4, 1.4, 7.85], [14.6, 12.6, 8.15], "leather_dark")             # 이음매
    for x in (1.3, 14.2):
        m.box([x, 1.2, 6.2], [x + 0.5, 2.2, 9.8], "brass")
        m.box([x, 11.8, 6.2], [x + 0.5, 12.8, 9.8], "brass")
    m.box([4.0, 11.0, 6.2], [5.4, 12.0, 6.4], "brass")
    m.box([10.6, 11.0, 6.2], [12.0, 12.0, 6.4], "brass")
    m.box([6.0, 12.5, 7.4], [6.8, 14.0, 8.6], "leather_dark")
    m.box([9.2, 12.5, 7.4], [10.0, 14.0, 8.6], "leather_dark")
    m.box([6.0, 13.6, 7.4], [10.0, 14.6, 8.6], "leather_dark")
    return m


def pool_cue(short=False):
    m = Model("pool_cue_short" if short else "pool_cue", seed=115 + short, auto_round=0.16)
    rod(m, 0, 0.6, 0.85, "rubber")
    rod(m, 0.6, 9, 0.8, "wood_dark_y", painter=lambda f, p, u, v: (230, 225, 210) if f != "up" and 5 < p[1] < 7 and int(p[1] * 3) % 2 == 0 else None)
    rod(m, 9, 9.6, 0.82, "ivory")
    if short:
        rod(m, 9.6, 12.5, 0.6, "wood_light_y")
        m.box([7.6, 12.5, 7.6], [8.3, 15.0, 8.3], "wood_light_y")
        m.box([8.0, 12.5, 7.75], [8.45, 13.8, 8.4], "wood_light_y")
        m.box([7.55, 12.5, 7.9], [7.95, 14.2, 8.45], "wood_light_y")
    else:
        rod(m, 9.6, 30.5, 0.5, "wood_light_y")
        rod(m, 30.5, 31.2, 0.45, "white")
        rod(m, 31.2, 31.6, 0.42, "blue_chalk")
    return m


def cleaver():
    m = Model("cleaver", seed=117, auto_round=0.16)
    rod(m, 0, 6.2, 0.75, "wood_y", painter=lambda f, p, u, v: (200, 200, 205) if f in ("east", "west") and abs(p[1] - 2) < 0.25 or (f in ("east", "west") and abs(p[1] - 4.5) < 0.25) else None)
    m.box([7.5, 5.8, 7.4], [8.5, 7.0, 8.6], "steel")
    hole = lambda f, p, u, v: (0, 0, 0, 0) if f in ("east", "west") and (p[1] - 14.6) ** 2 + (p[2] - 9.6) ** 2 < 0.35 else None
    m.box([7.68, 6.6, 6.2], [8.32, 16.0, 11.6], "blade", painter=hole)
    m.box([7.68, 6.6, 5.6], [8.32, 16.0, 6.2], "blade_dark")
    return m


# ───────────────────────── 투척 ─────────────────────────

def bottle():
    m = Model("bottle", seed=201, auto_round=0.16)
    rod(m, 0, 8.5, 1.55, "glass_brown")
    m.box([6.3, 2.0, 6.3], [9.7, 6.0, 9.7], "paper", painter=lambda f, p, u, v: (180, 30, 34) if 3.4 < p[1] < 4.6 else None)
    rod(m, 8.5, 10.0, 1.05, "glass_brown")
    rod(m, 10.0, 13.2, 0.55, "glass_brown")
    rod(m, 13.2, 13.9, 0.68, "gold")
    return m


def throwing_knife():
    m = Model("throwing_knife", seed=202, auto_round=0.16)
    holes = lambda f, p, u, v: (0, 0, 0, 0) if f in ("north", "south") and (abs(p[1] - 1.6) < 0.35 or abs(p[1] - 3.6) < 0.35) and abs(p[0] - 8) < 0.3 else None
    m.box([7.3, 0, 7.75], [8.7, 5.5, 8.25], "black", painter=holes)
    m.box([7.25, 5.5, 7.78], [8.75, 12.0, 8.22], "blade", painter=edge_line(("north", "south"), lo=0.8, hi=1.0))
    m.box([7.3, 11.6, 7.8], [8.45, 13.2, 8.2], "blade", rot=rot("z", -22.5, [7.3, 12, 8]))
    return m


def dart():
    m = Model("dart", seed=203, auto_round=0.16)
    rod(m, 0, 4, 0.18, "chrome")
    rod(m, 4, 8.5, 0.55, "brass", painter=lambda f, p, u, v: (120, 90, 30) if int(p[1] * 4) % 2 == 0 else None)
    rod(m, 8.5, 10.5, 0.25, "black")
    m.box([7.92, 9.5, 5.6], [8.08, 13.8, 10.4], "red_paint")
    m.box([5.6, 9.5, 7.92], [10.4, 13.8, 8.08], flat((240, 240, 240)))
    return m


def brick():
    m = Model("brick", seed=204, auto_round=0.16)
    holes = lambda f, p, u, v: (70, 26, 18) if f in ("up", "down") and any((p[0] - hx) ** 2 + (p[2] - 8) ** 2 < 0.45 for hx in (5.6, 8, 10.4)) else None
    m.box([4.2, 4.5, 6.0], [11.8, 8.3, 10.0], "brick", painter=holes)
    return m


def scissors():
    m = Model("scissors", seed=205, auto_round=0.16)
    m.box([7.55, 6.5, 7.4], [8.35, 16.0, 7.95], "chrome", painter=edge_line(("north",), lo=0.0, hi=0.25))
    m.box([7.65, 6.5, 7.95], [8.45, 15.0, 8.5], "steel")
    m.box([7.7, 6.2, 7.3], [8.3, 6.8, 8.6], "dark_steel")
    ring = lambda f, p, u, v: (0, 0, 0, 0) if f in ("north", "south") and (p[0] - cx_of(p)) ** 2 + (p[1] - 3.6) ** 2 < 1.0 else None
    m.box([5.0, 1.4, 7.4], [8.0, 6.4, 7.95], "red_paint", painter=lambda f, p, u, v: (0, 0, 0, 0) if f in ("north", "south") and (p[0] - 6.4) ** 2 + (p[1] - 3.8) ** 2 < 1.1 else None)
    m.box([8.0, 1.4, 7.95], [11.0, 6.4, 8.5], "red_paint", painter=lambda f, p, u, v: (0, 0, 0, 0) if f in ("north", "south") and (p[0] - 9.6) ** 2 + (p[1] - 3.8) ** 2 < 1.1 else None)
    _ = ring
    return m


def cx_of(p):
    return 6.4 if p[0] < 8 else 9.6


MELEE = {
    "dagger": lambda: dagger(), "bat": bat, "pipe": pipe, "golf_club": golf_club, "fire_axe": fire_axe,
    "machete": machete, "pot": pot, "frying_pan": frying_pan, "crowbar": crowbar, "katana": katana,
    "baton": baton, "hammer": lambda: hammer(), "briefcase": briefcase, "pool_cue": lambda: pool_cue(False),
    "pool_cue_short": lambda: pool_cue(True), "cleaver": cleaver,
}
THROWABLES = {
    "small_hammer": lambda: hammer("small_hammer", True), "bottle": bottle, "throwing_knife": throwing_knife,
    "dart": dart, "brick": brick, "scissors": scissors,
}
# 오른손으로 쥐는 위치 (손잡이 중앙)
GRIP = {k: (8, 3.5, 8) for k in list(MELEE) + list(THROWABLES)}
GRIP.update({"briefcase": (8, 13.6, 8), "pot": (8, 4, 8), "frying_pan": (8, 5, 8), "bottle": (8, 9.5, 8),
             "brick": (8, 6.4, 8), "scissors": (8, 3.8, 8), "dart": (8, 6.5, 8), "throwing_knife": (8, 2.6, 8),
             "small_hammer": (8, 3.0, 8), "cleaver": (8, 3.0, 8)})
