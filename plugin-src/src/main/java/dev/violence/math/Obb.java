package dev.violence.math;

/**
 * Y 축으로만 회전된 경계 상자 (문 판자 판정용).
 * center 는 상자 중심, half 는 로컬 축 기준 반 크기, yawRad 는 로컬 X 축이 월드에서 향하는 회전.
 */
public record Obb(Vec3 center, Vec3 half, double yawRad) {

    private Vec3 toLocal(Vec3 p) {
        return p.sub(center).rotateY(-yawRad);
    }

    /** 레이 교차 거리, 없으면 -1. */
    public double rayIntersect(Vec3 origin, Vec3 dir, double maxDist) {
        Vec3 lo = toLocal(origin);
        Vec3 ld = dir.rotateY(-yawRad);
        Aabb box = new Aabb(-half.x(), -half.y(), -half.z(), half.x(), half.y(), half.z());
        return box.rayIntersect(lo, ld, maxDist);
    }

    /** 원기둥(엔티티) 과의 겹침 근사 판정: 점이 반지름만큼 확장된 상자 안에 있는가. */
    public boolean overlapsPoint(Vec3 p, double radius) {
        Vec3 l = toLocal(p);
        return Math.abs(l.x()) <= half.x() + radius && Math.abs(l.y()) <= half.y() + radius && Math.abs(l.z()) <= half.z() + radius;
    }

    /** 로컬 좌표계의 Z 축(판자의 법선)을 월드 방향으로. */
    public Vec3 normal() {
        return new Vec3(0, 0, 1).rotateY(yawRad);
    }
}
