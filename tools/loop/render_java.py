#!/usr/bin/env python3
"""Java 아이템 모델(+텍스처) 심사용 렌더러 (루프 3단계 증빙).

사용: python3 tools/loop/render_java.py <model.json> <texture.png> <출력폴더> [--name 이름]
출력: <이름>_side.png(+x에서 본 측면), <이름>_side_b.png(−x 측면), <이름>_34.png(3/4 사선),
      <이름>_top.png(위에서), <이름>_tex.png(텍스처 원본 확대), <이름>_sheet.png(모아보기)
텍셀 하나하나를 사각형으로 그려 텍스처가 실제 게임처럼 보이게 한다. 면 밝기는 게임의 방향 음영을 흉내 낸다.
"""
import argparse, math, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fp_sim  # noqa: E402  (element_rot: 26.3 오일러/한 축 회전)
from voxel import face_point  # noqa: E402

NRM = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
BG = (118, 120, 126)


class _B:
    def __init__(self, a, b):
        self.frm, self.to = a, b


def rot_dir(v, r):
    if not r:
        return v
    o = r["origin"]
    p = fp_sim.element_rot([o[i] + v[i] for i in range(3)], r)
    return [p[i] - o[i] for i in range(3)]


def view(yaw, pitch):
    cy, sy, cp, sp = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    def f(p):
        x, y, z = p[0] - 8, p[1], p[2] - 8
        x, z = x * cy - z * sy, x * sy + z * cy          # y축 회전
        y, z = y * cp - z * sp, y * sp + z * cp          # x축 회전(내려다보기)
        return (x, y, z)
    return f


def light(n):
    # 게임 아이템 방향 음영 근사: 위 1.0, 아래 0.5, 남북 0.8, 동서 0.6 을 법선으로 보간
    return (n[1] ** 2) * (1.0 if n[1] > 0 else 0.5) + (n[2] ** 2) * 0.8 + (n[0] ** 2) * 0.6


def render(model, tex, yaw, pitch, size=1000, ss=2):
    """z-버퍼 래스터화: 픽셀마다 가장 가까운 면을 그림 (면 순서 정렬 오류·겹침 깜빡임 없음)"""
    import numpy as np
    T = np.asarray(tex).astype(np.float32)
    W, H = tex.size
    V = view(yaw, pitch)
    tris = []      # (3 화면점(x,y,z), 3 uv(px), 밝기)
    for e in model["elements"]:
        b = _B(e["from"], e["to"])
        r = e.get("rotation")
        for f, fv in e.get("faces", {}).items():
            n = rot_dir(NRM[f], r)
            vn = V([8 + n[0], n[1], 8 + n[2]])
            if vn[2] > 1e-6:
                continue
            u0, v0, u1, v1 = fv["uv"]
            uvc = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            pts = []
            for fu, fv_ in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = face_point(b, f, fu, fv_)
                p = fp_sim.element_rot(list(p), r) if r else p
                pts.append(V(p))
            uvp = [(u * W / 16, v * H / 16) for u, v in uvc]
            L = light(n)
            tris.append((pts[0], pts[1], pts[2], uvp[0], uvp[1], uvp[2], L))
            tris.append((pts[0], pts[2], pts[3], uvp[0], uvp[2], uvp[3], L))
    allp = np.array([p for t in tris for p in t[:3]])
    mnx, mny = allp[:, 0].min(), allp[:, 1].min(); mxx, mxy = allp[:, 0].max(), allp[:, 1].max()
    sc = (size * ss - 80 * ss) / max(mxx - mnx, mxy - mny)
    Wd = int((mxx - mnx) * sc + 80 * ss); Ht = int((mxy - mny) * sc + 80 * ss)
    img = np.empty((Ht, Wd, 3), np.float32); img[:] = BG
    zb = np.full((Ht, Wd), np.inf, np.float32)
    def scr(p):
        return ((p[0] - mnx) * sc + 40 * ss, (mxy - p[1]) * sc + 40 * ss, p[2])
    eps = -0.6   # 가장자리 포함 여유(픽셀): 인접 면 사이 머리카락 틈 방지
    for a, b_, c, ua, ub, uc, L in tris:
        A, B, C = scr(a), scr(b_), scr(c)
        x0 = max(int(np.floor(min(A[0], B[0], C[0]))) - 1, 0); x1 = min(int(np.ceil(max(A[0], B[0], C[0]))) + 1, Wd - 1)
        y0 = max(int(np.floor(min(A[1], B[1], C[1]))) - 1, 0); y1 = min(int(np.ceil(max(A[1], B[1], C[1]))) + 1, Ht - 1)
        if x1 < x0 or y1 < y0:
            continue
        den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
        if abs(den) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((B[1] - C[1]) * (xs - C[0]) + (C[0] - B[0]) * (ys - C[1])) / den
        w1 = ((C[1] - A[1]) * (xs - C[0]) + (A[0] - C[0]) * (ys - C[1])) / den
        w2 = 1 - w0 - w1
        # 픽셀 단위 여유를 무게 단위로 근사
        lim = eps / max(abs(den) ** 0.5, 1.0)
        m = (w0 >= lim) & (w1 >= lim) & (w2 >= lim)
        if not m.any():
            continue
        z = w0 * A[2] + w1 * B[2] + w2 * C[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        m &= z < sub - 1e-5
        if not m.any():
            continue
        u = w0 * ua[0] + w1 * ub[0] + w2 * uc[0]; v = w0 * ua[1] + w1 * ub[1] + w2 * uc[1]
        umin, umax = min(ua[0], ub[0], uc[0]), max(ua[0], ub[0], uc[0]); vmin, vmax = min(ua[1], ub[1], uc[1]), max(ua[1], ub[1], uc[1])
        ui = np.clip(np.floor(np.clip(u, umin, umax - 1e-4)), 0, W - 1).astype(int)
        vi = np.clip(np.floor(np.clip(v, vmin, vmax - 1e-4)), 0, H - 1).astype(int)
        col = T[vi, ui]
        m &= col[..., 3] > 0
        sub[m] = z[m]
        img[y0:y1 + 1, x0:x1 + 1][m] = np.minimum(col[..., :3][m] * L, 255)
    out = Image.fromarray(img.clip(0, 255).astype(np.uint8))
    return out.resize((Wd // ss, Ht // ss), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model"); ap.add_argument("texture"); ap.add_argument("out")
    ap.add_argument("--name", default="model")
    a = ap.parse_args()
    import json
    with open(a.model, encoding="utf-8") as f:
        model = json.load(f)
    tex = Image.open(a.texture).convert("RGBA")
    os.makedirs(a.out, exist_ok=True)
    views = {"side": (-90, 0), "side_b": (90, 0), "34": (-50, 22), "top": (-90, 70)}
    imgs = {}
    for k, (yw, pt) in views.items():
        imgs[k] = render(model, tex, yw, pt)
        imgs[k].save(os.path.join(a.out, f"{a.name}_{k}.png"))
    t = tex.copy()
    bg = Image.new("RGBA", t.size, (255, 0, 255, 255)); bg.alpha_composite(t)
    k = max(1, 768 // t.width)
    tt = bg.convert("RGB").resize((t.width * k, t.height * k), Image.NEAREST)
    tt.save(os.path.join(a.out, f"{a.name}_tex.png"))
    # 모아보기
    cells = [imgs["side"], imgs["34"], imgs["side_b"], imgs["top"]]
    cw = max(c.width for c in cells); ch = max(c.height for c in cells)
    sheet = Image.new("RGB", (cw * 2, ch * 2), BG)
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % 2) * cw + (cw - c.width) // 2, (i // 2) * ch + (ch - c.height) // 2))
    sheet.save(os.path.join(a.out, f"{a.name}_sheet.png"))
    print("rendered ->", a.out)


if __name__ == "__main__":
    main()
