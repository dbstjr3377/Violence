"""1인칭 사격 순간의 총구 화염 (노란색, 빛남)."""
import math

from voxel import Material

FLASH = Material((255, 220, 80), noise=0.0, edge=1.0, top=1.0)


def star(face, pt, fu, fv, cx, cy, r):
    dx, dy = pt[0] - cx, pt[1] - cy
    d = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    spike = r * (0.55 + 0.45 * abs(math.cos(ang * 3)))
    if d < r * 0.28:
        return (255, 255, 235, 255)
    if d < spike * 0.6:
        return (255, 236, 120, 255)
    if d < spike:
        return (255, 190, 40, 255)
    return (0, 0, 0, 0)


def cone(face, pt, fu, fv, mz, length, r, axis):
    t = (pt[2] - mz) / length
    if t < 0 or t > 1:
        return (0, 0, 0, 0)
    w = r * (1 - t) ** 0.8 * (0.6 + 0.4 * math.sin(t * 9) ** 2)
    off = abs(pt[0] - 8) if axis == "x" else abs(pt[1] - cone.cy)
    if off < w * 0.35:
        return (255, 250, 220, 255)
    if off < w:
        return (255, 200, 50, 255)
    return (0, 0, 0, 0)


def add_flash(m, muzzle, size=3.2):
    x, y, z = muzzle
    length = min(6.5, 31.8 - z)
    cone.cy = y
    # 정면 별 모양
    m.box([x - size, y - size, z + 0.3], [x + size, y + size, z + 0.35], FLASH,
          painter=lambda f, p, u, v: star(f, p, u, v, x, y, size), faces=("north", "south"), light=True)
    # 앞으로 뻗는 불꽃 (세로/가로 판)
    m.box([x - 0.02, y - size * 0.8, z], [x + 0.02, y + size * 0.8, z + length], FLASH,
          painter=lambda f, p, u, v: cone(f, (8 + abs(p[1] - y), p[1], p[2]), u, v, z, length, size * 0.8, "x"), faces=("east", "west"), light=True)
    m.box([x - size * 0.8, y - 0.02, z], [x + size * 0.8, y + 0.02, z + length], FLASH,
          painter=lambda f, p, u, v: cone(f, p, u, v, z, length, size * 0.8, "x"), faces=("up", "down"), light=True)
