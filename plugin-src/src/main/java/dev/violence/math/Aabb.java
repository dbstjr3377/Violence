package dev.violence.math;

/** 축 정렬 경계 상자. 히트박스/레이 판정에 사용. */
public record Aabb(double minX, double minY, double minZ, double maxX, double maxY, double maxZ) {

    public static Aabb ofCenterBottom(Vec3 feet, double width, double height) {
        double h = width / 2;
        return new Aabb(feet.x() - h, feet.y(), feet.z() - h, feet.x() + h, feet.y() + height, feet.z() + h);
    }

    public static Aabb ofCenter(Vec3 c, double half) {
        return new Aabb(c.x() - half, c.y() - half, c.z() - half, c.x() + half, c.y() + half, c.z() + half);
    }

    public static Aabb ofCenter(Vec3 c, double hx, double hy, double hz) {
        return new Aabb(c.x() - hx, c.y() - hy, c.z() - hz, c.x() + hx, c.y() + hy, c.z() + hz);
    }

    public Aabb grow(double g) { return new Aabb(minX - g, minY - g, minZ - g, maxX + g, maxY + g, maxZ + g); }

    public Vec3 center() { return new Vec3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2); }

    public boolean contains(Vec3 p) {
        return p.x() >= minX && p.x() <= maxX && p.y() >= minY && p.y() <= maxY && p.z() >= minZ && p.z() <= maxZ;
    }

    public boolean intersects(Aabb o) {
        return minX < o.maxX && maxX > o.minX && minY < o.maxY && maxY > o.minY && minZ < o.maxZ && maxZ > o.minZ;
    }

    /**
     * 레이와의 교차 거리 (slab method).
     * @param origin 시작점
     * @param dir 단위 방향
     * @param maxDist 최대 거리
     * @return 교차 거리, 없으면 -1
     */
    public double rayIntersect(Vec3 origin, Vec3 dir, double maxDist) {
        double tMin = 0, tMax = maxDist;
        double[] o = {origin.x(), origin.y(), origin.z()};
        double[] d = {dir.x(), dir.y(), dir.z()};
        double[] mn = {minX, minY, minZ};
        double[] mx = {maxX, maxY, maxZ};
        for (int i = 0; i < 3; i++) {
            if (Math.abs(d[i]) < 1e-12) {
                if (o[i] < mn[i] || o[i] > mx[i]) return -1;
            } else {
                double inv = 1.0 / d[i];
                double t1 = (mn[i] - o[i]) * inv, t2 = (mx[i] - o[i]) * inv;
                if (t1 > t2) { double t = t1; t1 = t2; t2 = t; }
                tMin = Math.max(tMin, t1);
                tMax = Math.min(tMax, t2);
                if (tMin > tMax) return -1;
            }
        }
        return tMin;
    }
}
