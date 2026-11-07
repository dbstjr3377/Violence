package dev.violence.math;

/**
 * 사람형 히트박스. 몸통(AABB)과 머리(눈 높이 주변 정육면체)로 구성.
 * 쓰러진 상태는 낮고 넓은 상자 하나로 판정 (쓰러진 대상은 어디를 맞아도 치명).
 */
public final class Hitbox {
    public static final double WIDTH = 0.6;
    public static final double HEIGHT = 1.8;
    public static final double EYE = 1.62;
    public static final double HEAD_HALF = 0.27;

    public enum Part { NONE, HEAD, BODY }

    public record Result(Part part, double distance) {
        public static final Result MISS = new Result(Part.NONE, -1);
        public boolean hit() { return part != Part.NONE; }
    }

    private Hitbox() {}

    public static Aabb body(Vec3 feet, double scale) {
        return Aabb.ofCenterBottom(feet, WIDTH * scale, HEIGHT * scale);
    }

    public static Aabb head(Vec3 feet, double scale) {
        return Aabb.ofCenter(feet.add(0, EYE * scale, 0), HEAD_HALF * scale);
    }

    /** 쓰러진(누운) 상태: 높이 0.6, 진행 방향으로 긴 상자 대신 넉넉한 정사각 근사. */
    public static Aabb downed(Vec3 feet, double scale) {
        return Aabb.ofCenterBottom(feet, 1.6 * scale, 0.6 * scale);
    }

    /** 벽에 기대 앉은(기절) 상태: 폭 0.9, 높이 1.15 상자 (어디를 맞아도 치명) */
    public static Aabb sitting(Vec3 feet, double scale) {
        return Aabb.ofCenterBottom(feet, 0.9 * scale, 1.15 * scale);
    }

    public static Result raycastSitting(Vec3 feet, double scale, Vec3 origin, Vec3 dir, double maxDist) {
        double t = sitting(feet, scale).rayIntersect(origin, dir, maxDist);
        return t >= 0 ? new Result(Part.BODY, t) : Result.MISS;
    }

    /** 서있는 대상에 대한 레이 판정. 머리를 먼저 검사한다. */
    public static Result raycastStanding(Vec3 feet, double scale, Vec3 origin, Vec3 dir, double maxDist) {
        double th = head(feet, scale).rayIntersect(origin, dir, maxDist);
        double tb = body(feet, scale).rayIntersect(origin, dir, maxDist);
        if (th >= 0 && (tb < 0 || th <= tb + 0.35)) return new Result(Part.HEAD, th);
        if (tb >= 0) {
            // 몸통 상자에 들어갔지만 그 레이가 머리 높이를 지나간다면 머리로 처리
            Vec3 p = origin.add(dir.mul(tb));
            if (p.y() >= feet.y() + (EYE - HEAD_HALF) * scale) return new Result(Part.HEAD, tb);
            return new Result(Part.BODY, tb);
        }
        return Result.MISS;
    }

    public static Result raycastDowned(Vec3 feet, double scale, Vec3 origin, Vec3 dir, double maxDist) {
        double t = downed(feet, scale).rayIntersect(origin, dir, maxDist);
        return t >= 0 ? new Result(Part.BODY, t) : Result.MISS;
    }
}
