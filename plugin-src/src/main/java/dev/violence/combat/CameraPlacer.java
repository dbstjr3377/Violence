package dev.violence.combat;

import dev.violence.math.Vec3;
import java.util.List;

/**
 * 처형 카메라 자리 고르기 (순수 계산). 좁은 방(교도소 감방 등)에서 카메라가 벽 속에 들어가 벽만 보이던 문제를 막는다.
 * 후보를 차례로 보고 바라보는 곳(look)에서 후보까지 시야가 트였으면 그 자리를 쓴다.
 * 모두 막혔으면 바라보는 곳 둘레(16방향 × 높이 3단 × 거리 4단)에서 트인 자리를 찾고,
 * 그래도 없으면 가장 많이 트인 후보 쪽으로 벽 바로 앞(0.35블록 안쪽)까지만 카메라를 둔다.
 * 시야가 트였어도 카메라가 벽·천장에 0.4블록보다 가까우면 화면 가장자리가 벽 속으로 들어가 어두워지므로 쓰지 않는다.
 */
public final class CameraPlacer {
    private CameraPlacer() {}

    /** from 에서 to 쪽으로 블록에 막히기 전까지의 거리 (막히지 않으면 두 점 사이 거리) */
    public interface Ray {
        double clear(Vec3 from, Vec3 to);
    }

    public static final double WALL_MARGIN = 0.35;
    public static final double MIN_DIST = 0.8;
    /** 카메라 자리 둘레(앞뒤·좌우·위아래)로 이만큼은 비어 있어야 함 */
    public static final double CLEARANCE = 0.4;

    private static final Vec3[] AXES = {
            new Vec3(1, 0, 0), new Vec3(-1, 0, 0), new Vec3(0, 1, 0), new Vec3(0, -1, 0), new Vec3(0, 0, 1), new Vec3(0, 0, -1)};

    /** look 에서 c 까지 트였고, c 둘레도 벽에서 CLEARANCE 이상 떨어짐 */
    static boolean open(Vec3 look, Vec3 c, Ray ray) {
        double len = c.sub(look).length();
        if (ray.clear(look, c) < len - 1e-3) return false;
        for (Vec3 ax : AXES) {
            if (ray.clear(c, c.add(ax.mul(CLEARANCE))) < CLEARANCE - 1e-3) return false;
        }
        return true;
    }

    public static Vec3 place(Vec3 look, List<Vec3> candidates, Ray ray) {
        Vec3 best = null;
        double bestFrac = -1;
        double bestClear = 0;
        for (Vec3 c : candidates) {
            double len = c.sub(look).length();
            if (len < 1e-6) continue;
            double clear = ray.clear(look, c);
            if (open(look, c, ray)) return c;
            if (clear >= len - 1e-3) clear = Math.max(0, len - CLEARANCE);   // 트였지만 벽에 붙음
            double frac = clear / len;
            if (frac > bestFrac) {
                bestFrac = frac;
                best = c;
                bestClear = clear;
            }
        }
        if (best == null) return candidates.isEmpty() ? look : candidates.get(0);
        // 좁은 복도·낮은 천장: 바라보는 곳 둘레를 돌며 시야가 트인 자리를 찾음 (첫 후보 방향부터, 멀리서 가까이로)
        Vec3 ring = ring(look, candidates.get(0), ray);
        if (ring != null) return ring;
        Vec3 dir = best.sub(look).normalize();
        return look.add(dir.mul(Math.max(MIN_DIST, bestClear - WALL_MARGIN)));
    }

    /** 둘레 찾기: 거리 2.4 → 1.5, 높이각 35·55·20°, 방위 16방향 (선호 방향에서 가까운 순). 끝까지 트인 첫 자리 */
    static Vec3 ring(Vec3 look, Vec3 preferred, Ray ray) {
        Vec3 pref = preferred.sub(look);
        double baseAz = Math.atan2(pref.z(), pref.x());
        double[] dists = {2.4, 2.0, 1.7, 1.5};
        double[] elevs = {35, 55, 20};
        int[] order = {0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8};
        for (double dist : dists) {
            for (double el : elevs) {
                double e = Math.toRadians(el);
                for (int k : order) {
                    double az = baseAz + k * Math.PI / 8;
                    Vec3 c = look.add(new Vec3(Math.cos(az) * Math.cos(e), Math.sin(e), Math.sin(az) * Math.cos(e)).mul(dist));
                    if (open(look, c, ray)) return c;
                }
            }
        }
        return null;
    }
}
