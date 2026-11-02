package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.logic.AStar;
import dev.violence.logic.NavGrid;
import dev.violence.logic.SpawnScorer;
import dev.violence.math.Vec3;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import org.junit.jupiter.api.Test;

class NavTest {

    /** 가짜 월드: 바닥 y=0, 벽은 y=1..3 에 블록, 계단은 반블록/블록 교대 */
    static final class FakeWorld implements NavGrid.BlockQuery {
        final Set<Long> solid = new HashSet<>();
        final Set<Long> slab = new HashSet<>();
        static long k(int x, int y, int z) { return NavGrid.key(x, y, z); }
        void solid(int x, int y, int z) { solid.add(k(x, y, z)); }
        void slab(int x, int y, int z) { slab.add(k(x, y, z)); }
        @Override public double topHeight(int x, int y, int z) {
            if (solid.contains(k(x, y, z))) return 1.0;
            if (slab.contains(k(x, y, z))) return 0.5;
            return Double.NaN;
        }
        @Override public boolean passable(int x, int y, int z) {
            return !solid.contains(k(x, y, z)) && !slab.contains(k(x, y, z));
        }
    }

    private FakeWorld room() {
        FakeWorld w = new FakeWorld();
        for (int x = 0; x < 20; x++) for (int z = 0; z < 20; z++) w.solid(x, 0, z);
        // x=10 에 벽, z=15 에만 통로
        for (int z = 0; z < 20; z++) {
            if (z == 15) continue;
            for (int y = 1; y <= 3; y++) w.solid(10, y, z);
        }
        return w;
    }

    @Test
    void sealedRoomIsSeparateIslandAndFailsFast() {
        FakeWorld w = room();
        // x=10 통로를 막아 오른쪽 방을 섬으로 만들고, 왼쪽에 지붕 위 섬도 추가
        for (int y = 1; y <= 3; y++) w.solid(10, y, 15);
        for (int x = 2; x <= 4; x++) for (int z = 2; z <= 4; z++) w.solid(x, 5, z);
        NavGrid g = NavGrid.build(w, 0, 0, 0, 19, 8, 19);
        NavGrid.Node a = g.nearest(new Vec3(2.5, 1, 8.5));
        NavGrid.Node b = g.nearest(new Vec3(17.5, 1, 2.5));
        NavGrid.Node roof = g.get(3, 5, 3);
        assertNotNull(roof);
        assertFalse(g.connected(a, b), "막힌 방은 다른 덩어리");
        assertFalse(g.connected(a, roof), "지붕 위는 다른 덩어리");
        assertTrue(g.inMain(a) || g.inMain(b));
        assertFalse(g.inMain(roof));
        long t0 = System.nanoTime();
        assertTrue(AStar.find(g, a, b, 100_000).isEmpty(), "갈 수 없는 목표는 빈 경로");
        assertTrue((System.nanoTime() - t0) / 1e6 < 50, "섬 판정으로 바로 끝나야 함");
        for (NavGrid.Node n : g.mainNodes()) assertTrue(g.inMain(n));
    }

    @Test
    void positionHistoryRemembersPosture() {
        dev.violence.combat.PositionHistory h = new dev.violence.combat.PositionHistory(10);
        assertNull(h.downed(0));
        h.record(new Vec3(0, 0, 0), true);
        h.record(new Vec3(1, 0, 0), true);
        h.record(new Vec3(2, 0, 0), false);
        assertEquals(Boolean.FALSE, h.downed(0));
        assertEquals(Boolean.TRUE, h.downed(1));
        assertEquals(Boolean.TRUE, h.downed(99), "기록보다 오래 전이면 가장 오래된 기록");
    }

    @Test
    void pathGoesAroundWall() {
        FakeWorld w = room();
        NavGrid g = NavGrid.build(w, 0, 0, 0, 19, 4, 19);
        NavGrid.Node a = g.nearest(new Vec3(2.5, 1, 2.5));
        NavGrid.Node b = g.nearest(new Vec3(17.5, 1, 2.5));
        assertNotNull(a);
        assertNotNull(b);
        List<Vec3> path = AStar.find(g, a, b, 5000);
        assertFalse(path.isEmpty());
        assertEquals(b.pos(), path.getLast());
        // 반드시 통로(z=15) 근처를 지나야 한다
        assertTrue(path.stream().anyMatch(p -> Math.floor(p.x()) == 10 && Math.floor(p.z()) == 15)
                || path.stream().anyMatch(p -> p.z() > 13));
    }

    @Test
    void stairsWithoutJumping() {
        FakeWorld w = new FakeWorld();
        for (int x = 0; x < 12; x++) for (int z = 0; z < 3; z++) w.solid(x, 0, z);
        // x=4: 반블록(높이 1.5), x=5: 블록(2.0), x=6: 반블록 y=2 (2.5), x>=7: 2층 바닥 y=2 (3.0)
        for (int z = 0; z < 3; z++) {
            w.slab(4, 1, z);
            w.solid(5, 1, z);
            w.slab(6, 2, z);
            for (int x = 7; x < 12; x++) w.solid(x, 2, z);
        }
        NavGrid g = NavGrid.build(w, 0, 0, 0, 11, 6, 2);
        NavGrid.Node a = g.nearest(new Vec3(1.5, 1, 1.5));
        NavGrid.Node b = g.nearest(new Vec3(10.5, 3, 1.5));
        assertEquals(3.0, b.h, 1e-9);
        List<Vec3> path = AStar.find(g, a, b, 5000);
        assertFalse(path.isEmpty());
        assertEquals(3.0, path.getLast().y(), 1e-9);
    }

    @Test
    void fullBlockStepIsNotClimbable() {
        FakeWorld w = new FakeWorld();
        for (int x = 0; x < 8; x++) for (int z = 0; z < 3; z++) w.solid(x, 0, z);
        for (int z = 0; z < 3; z++) for (int x = 4; x < 8; x++) w.solid(x, 1, z);
        NavGrid g = NavGrid.build(w, 0, 0, 0, 7, 5, 2);
        NavGrid.Node a = g.nearest(new Vec3(1.5, 1, 1.5));
        NavGrid.Node b = g.nearest(new Vec3(6.5, 2, 1.5));
        List<Vec3> path = AStar.find(g, a, b, 5000);
        // 목표에 못 감 (점프 불가)
        assertTrue(path.isEmpty() || path.getLast().y() < 1.5);
    }

    @Test
    void spawnPrefersHiddenSpots() {
        Vec3 observer = new Vec3(0, 1.6, 0);
        Vec3 visible = new Vec3(10, 0, 0);
        Vec3 hidden = new Vec3(10, 0, 20);
        // hidden 은 벽 뒤라고 가정
        double sv = SpawnScorer.score(visible, List.of(observer), (o, t) -> t.z() < 5, 8);
        double sh = SpawnScorer.score(hidden, List.of(observer), (o, t) -> t.z() < 5, 8);
        assertTrue(sh > sv);
        Vec3 chosen = SpawnScorer.choose(List.of(visible, hidden), List.of(observer), (o, t) -> t.z() < 5, 20, 8, new Random(3));
        assertEquals(hidden, chosen);
    }
}
