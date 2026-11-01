package dev.violence.math;

/** 서버 API 에 의존하지 않는 불변 3D 벡터 (순수 로직/테스트용). */
public record Vec3(double x, double y, double z) {
    public static final Vec3 ZERO = new Vec3(0, 0, 0);
    public static final Vec3 UP = new Vec3(0, 1, 0);

    public Vec3 add(Vec3 o) { return new Vec3(x + o.x, y + o.y, z + o.z); }
    public Vec3 add(double ax, double ay, double az) { return new Vec3(x + ax, y + ay, z + az); }
    public Vec3 sub(Vec3 o) { return new Vec3(x - o.x, y - o.y, z - o.z); }
    public Vec3 mul(double s) { return new Vec3(x * s, y * s, z * s); }
    public double dot(Vec3 o) { return x * o.x + y * o.y + z * o.z; }
    public Vec3 cross(Vec3 o) { return new Vec3(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x); }
    public double lengthSq() { return x * x + y * y + z * z; }
    public double length() { return Math.sqrt(lengthSq()); }
    public double distance(Vec3 o) { return sub(o).length(); }
    public double distanceSq(Vec3 o) { return sub(o).lengthSq(); }
    public double horizontalDistance(Vec3 o) { double dx = x - o.x, dz = z - o.z; return Math.sqrt(dx * dx + dz * dz); }

    public Vec3 normalize() {
        double l = length();
        return l < 1e-9 ? ZERO : new Vec3(x / l, y / l, z / l);
    }

    public Vec3 horizontal() { return new Vec3(x, 0, z); }

    /** 마인크래프트 yaw/pitch(도) 로부터 시선 방향 벡터. */
    public static Vec3 fromYawPitch(double yawDeg, double pitchDeg) {
        double yaw = Math.toRadians(yawDeg), pitch = Math.toRadians(pitchDeg);
        double xz = Math.cos(pitch);
        return new Vec3(-xz * Math.sin(yaw), -Math.sin(pitch), xz * Math.cos(yaw));
    }

    /** 방향 벡터의 마인크래프트 yaw (도). */
    public double yaw() { return Math.toDegrees(Math.atan2(-x, z)); }

    /** 방향 벡터의 마인크래프트 pitch (도). */
    public double pitch() {
        double xz = Math.sqrt(x * x + z * z);
        return Math.toDegrees(Math.atan2(-y, xz));
    }

    /** Y 축 기준 회전 (라디안). */
    public Vec3 rotateY(double rad) {
        double c = Math.cos(rad), s = Math.sin(rad);
        return new Vec3(x * c - z * s, y, x * s + z * c);
    }

    public Vec3 lerp(Vec3 o, double t) { return new Vec3(x + (o.x - x) * t, y + (o.y - y) * t, z + (o.z - z) * t); }

    /** 두 단위벡터 사이 각도 (도). */
    public double angleTo(Vec3 o) {
        double d = normalize().dot(o.normalize());
        return Math.toDegrees(Math.acos(Math.max(-1, Math.min(1, d))));
    }
}
