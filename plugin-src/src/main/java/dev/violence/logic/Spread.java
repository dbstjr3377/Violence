package dev.violence.logic;

import dev.violence.math.Vec3;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** 탄 퍼짐 계산 (샷건 산탄, 명중률 오차). */
public final class Spread {
    private Spread() {}

    /**
     * 기준 방향 주변으로 원뿔 안에 무작위 방향을 만든다.
     * @param halfAngleDeg 원뿔 반각(도)
     */
    public static Vec3 jitter(Vec3 dir, double halfAngleDeg, Random rnd) {
        if (halfAngleDeg <= 0) return dir.normalize();
        Vec3 d = dir.normalize();
        Vec3 helper = Math.abs(d.y()) > 0.95 ? new Vec3(1, 0, 0) : Vec3.UP;
        Vec3 right = d.cross(helper).normalize();
        Vec3 up = right.cross(d).normalize();
        // 원판 위 균등 분포
        double r = Math.tan(Math.toRadians(halfAngleDeg)) * Math.sqrt(rnd.nextDouble());
        double a = rnd.nextDouble() * Math.PI * 2;
        return d.add(right.mul(Math.cos(a) * r)).add(up.mul(Math.sin(a) * r)).normalize();
    }

    public static List<Vec3> pellets(Vec3 dir, int count, double halfAngleDeg, Random rnd) {
        List<Vec3> out = new ArrayList<>(count);
        for (int i = 0; i < count; i++) out.add(jitter(dir, halfAngleDeg, rnd));
        return out;
    }
}
