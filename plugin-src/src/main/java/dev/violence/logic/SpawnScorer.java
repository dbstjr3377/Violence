package dev.violence.logic;

import dev.violence.math.Vec3;
import java.util.Collection;
import java.util.List;
import java.util.Random;
import java.util.function.BiPredicate;

/**
 * 리스폰 위치 선정: 다른 개체들에게 최대한 보이지 않고, 적당히 떨어진 곳.
 */
public final class SpawnScorer {
    private SpawnScorer() {}

    /**
     * @param candidates 후보 발 위치들
     * @param observers 살아있는 개체들의 눈 위치
     * @param lineOfSight (눈 위치, 후보 머리 위치) → 시야가 뚫려 있는가
     * @param maxLosChecks 성능 제한: 후보 하나당 시야 검사할 최대 관찰자 수 (가까운 순)
     */
    public static Vec3 choose(List<Vec3> candidates, Collection<Vec3> observers,
                              BiPredicate<Vec3, Vec3> lineOfSight, int sampleCount, int maxLosChecks, Random rnd) {
        if (candidates.isEmpty()) return null;
        Vec3 best = null;
        double bestScore = -Double.MAX_VALUE;
        int samples = Math.min(sampleCount, candidates.size());
        for (int i = 0; i < samples; i++) {
            Vec3 c = candidates.get(rnd.nextInt(candidates.size()));
            double score = score(c, observers, lineOfSight, maxLosChecks) + rnd.nextDouble() * 5;
            if (score > bestScore) {
                bestScore = score;
                best = c;
            }
        }
        return best;
    }

    public static double score(Vec3 c, Collection<Vec3> observers, BiPredicate<Vec3, Vec3> los, int maxLosChecks) {
        Vec3 head = c.add(0, 1.6, 0);
        double minDist = 60;
        int visible = 0;
        int checked = 0;
        // 가까운 관찰자부터 검사
        List<Vec3> sorted = observers.stream().sorted((a, b) -> Double.compare(a.distanceSq(head), b.distanceSq(head))).toList();
        for (Vec3 o : sorted) {
            double d = o.distance(head);
            minDist = Math.min(minDist, d);
            if (d > 48 || checked >= maxLosChecks) continue;
            checked++;
            if (los.test(o, head)) visible++;
        }
        double s = 0;
        if (visible == 0) s += 1000;
        s -= visible * 150;
        // 너무 가까우면 큰 감점, 12~40 블록이 이상적
        if (minDist < 6) s -= 600;
        s += Math.min(minDist, 40) * 4;
        return s;
    }
}
