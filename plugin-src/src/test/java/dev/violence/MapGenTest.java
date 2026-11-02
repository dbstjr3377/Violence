package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.arena.GameMap;
import dev.violence.logic.NavGrid;
import dev.violence.map.BlockStore;
import dev.violence.mapgen.BlockAccess;
import dev.violence.mapgen.Generators;
import dev.violence.mapgen.MapGenerator;
import dev.violence.mapgen.Theme;
import dev.violence.math.Vec3;
import java.io.File;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;

/**
 * 내장 맵 생성기 검증 (서버 없이 메모리 월드에서).
 * - 크기, 무기/리스폰/문 개수
 * - 문 위치가 실제 벽 속 출입구인지
 * - 걸을 수 있는 영역이 하나로 이어지고 모든 층이 계단으로 연결되는지 (점프 불가 규칙)
 */
class MapGenTest {

    static final class MemWorld implements BlockAccess {
        final Map<Long, String> blocks = new HashMap<>();
        static long k(int x, int y, int z) { return NavGrid.key(x, y, z); }
        @Override public void set(int x, int y, int z, String state) {
            if (state.startsWith("minecraft:air")) blocks.remove(k(x, y, z));
            else blocks.put(k(x, y, z), state);
        }
        @Override public String get(int x, int y, int z) { return blocks.get(k(x, y, z)); }
    }

    /** 블록 충돌 높이 근사 (실제 서버에서는 충돌 형태로 계산) */
    static double top(String state) {
        if (state == null) return Double.NaN;
        String n = Theme.name(state);
        if (n.endsWith("_slab")) return state.contains("type=top") || state.contains("type=double") ? 1.0 : 0.5;
        if (n.endsWith("_pane") || n.equals("iron_bars") || n.endsWith("_fence") || n.endsWith("_wall")
                || n.startsWith("potted_") || n.equals("lightning_rod") || n.equals("lantern")) return Double.NaN;
        if (n.endsWith("_carpet")) return 0.0625;
        return 1.0;
    }

    static NavGrid nav(MemWorld w, GameMap m) {
        return NavGrid.build(new NavGrid.BlockQuery() {
            @Override public double topHeight(int x, int y, int z) { return top(w.get(x, y, z)); }
            @Override public boolean passable(int x, int y, int z) { return w.get(x, y, z) == null; }
        }, m.minX, m.minY, m.minZ, m.maxX, m.maxY, m.maxZ);
    }

    static Set<Long> component(NavGrid g, NavGrid.Node start) {
        Set<Long> seen = new HashSet<>();
        ArrayDeque<NavGrid.Node> q = new ArrayDeque<>();
        q.add(start);
        seen.add(start.key);
        while (!q.isEmpty()) {
            NavGrid.Node n = q.poll();
            for (NavGrid.Node o : g.neighbors(n)) if (seen.add(o.key)) q.add(o);
        }
        return seen;
    }

    @TestFactory
    List<DynamicTest> allBuiltInMaps() {
        List<DynamicTest> tests = new ArrayList<>();
        for (MapGenerator gen : Generators.all()) {
            tests.add(DynamicTest.dynamicTest(gen.id(), () -> checkMap(gen)));
        }
        return tests;
    }

    private void checkMap(MapGenerator gen) {
        MemWorld w = new MemWorld();
        long t0 = System.currentTimeMillis();
        GameMap m = gen.generate(w, new Random(gen.id().hashCode() * 31L + 7));
        long genMs = System.currentTimeMillis() - t0;
        int sx = m.maxX - m.minX + 1, sz = m.maxZ - m.minZ + 1, sy = m.maxY - m.minY + 1;
        // 1) 크기: 50명이 불편하지 않도록 충분히 넓게
        assertTrue(Math.max(sx, sz) >= 60 && Math.min(sx, sz) >= 35, gen.id() + " 크기 " + sx + "x" + sz);
        // 2) 배치 요소
        assertTrue(m.weaponSpots.size() >= 30, gen.id() + " 무기 지점 " + m.weaponSpots.size());
        assertTrue(m.spawns.size() >= 20, gen.id() + " 리스폰 지점 " + m.spawns.size());
        // 3) 문: 2칸 높이 출입구 + 양옆이 벽
        int badDoors = 0;
        for (GameMap.DoorSpec d : m.doors) {
            boolean open = w.isAir(d.x(), d.y(), d.z()) && w.isAir(d.x(), d.y() + 1, d.z());
            boolean sides = d.alongX()
                    ? (!w.isAir(d.x() - 1, d.y(), d.z()) || !w.isAir(d.x() + 1, d.y(), d.z()))
                    : (!w.isAir(d.x(), d.y(), d.z() - 1) || !w.isAir(d.x(), d.y(), d.z() + 1));
            if (!open || !sides) badDoors++;
        }
        assertTrue(m.doors.size() >= 6, gen.id() + " 문 " + m.doors.size());
        assertTrue(badDoors <= m.doors.size() / 10, gen.id() + " 잘못된 문 " + badDoors + "/" + m.doors.size());
        // 4) 보행 그리드 연결성
        NavGrid g = nav(w, m);
        assertTrue(g.size() > 1000, gen.id() + " 보행 노드 " + g.size());
        // 가장 큰 연결 영역 찾기 (리스폰 지점에서 시작)
        Set<Long> main = null;
        for (Vec3 s : m.spawns) {
            NavGrid.Node n = g.nearest(s);
            if (n == null) continue;
            Set<Long> c = component(g, n);
            if (main == null || c.size() > main.size()) main = c;
            if (main.size() > g.size() / 2) break;
        }
        assertNotNull(main);
        int spawnOk = 0;
        for (Vec3 s : m.spawns) {
            NavGrid.Node n = g.nearest(s);
            if (n != null && main.contains(n.key)) spawnOk++;
        }
        int weaponOk = 0;
        for (GameMap.WeaponSpot s : m.weaponSpots) {
            // 탁자 위 무기는 바로 옆 바닥에서 집을 수 있으면 됨
            boolean ok = false;
            for (int dx = -2; dx <= 2 && !ok; dx++) for (int dz = -2; dz <= 2 && !ok; dz++) {
                NavGrid.Node n = g.nodeAt((int) Math.floor(s.pos().x()) + dx, (int) Math.floor(s.pos().z()) + dz, s.pos().y(), 1.6);
                if (n != null && main.contains(n.key)) ok = true;
            }
            if (ok) weaponOk++;
        }
        // 층별 연결: 주 영역에 포함된 서 있는 높이(층)
        TreeSet<Integer> floorsReached = new TreeSet<>();
        TreeSet<Integer> floorsAll = new TreeSet<>();
        Map<Long, NavGrid.Node> byKey = new HashMap<>();
        for (NavGrid.Node n : g.nodes()) byKey.put(n.key, n);
        int roofY = m.maxY - 2;
        for (NavGrid.Node n : g.nodes()) {
            int fl = (int) Math.floor(n.h);
            if (fl >= roofY - 1) continue; // 지붕 위 제외
            floorsAll.add(fl);
        }
        for (long k : main) {
            NavGrid.Node n = byKey.get(k);
            floorsReached.add((int) Math.floor(n.h));
        }
        // 주요 층(노드가 300개 이상인 높이)은 모두 연결되어야 함
        Map<Integer, Integer> perFloor = new HashMap<>();
        for (NavGrid.Node n : g.nodes()) {
            int fl = (int) Math.floor(n.h);
            if (fl >= roofY - 1) continue;
            perFloor.merge(fl, 1, Integer::sum);
        }
        int nonRoof = perFloor.values().stream().mapToInt(Integer::intValue).sum();
        // 가구 윗면 등을 제외한 실제 층: 전체의 8% 이상을 차지하는 높이
        List<Integer> majorFloors = perFloor.entrySet().stream().filter(e -> e.getValue() >= Math.max(300, nonRoof * 0.08)).map(Map.Entry::getKey).sorted().toList();
        assertTrue(nonRoof >= 4000, gen.id() + " 걸을 수 있는 면적 " + nonRoof);
        for (int fl : majorFloors) assertTrue(floorsReached.contains(fl), gen.id() + " 층 " + fl + " 이 연결되지 않음. 도달 층: " + floorsReached);
        double spawnRatio = spawnOk / (double) m.spawns.size();
        double weaponRatio = weaponOk / (double) m.weaponSpots.size();
        System.out.printf("[%s] %dx%dx%d 생성 %dms, 노드 %d, 주영역 %d, 층 %s, 무기 %d(도달 %.0f%%), 리스폰 %d(도달 %.0f%%), 문 %d (불량 %d)%n",
                gen.id(), sx, sz, sy, genMs, g.size(), main.size(), majorFloors, m.weaponSpots.size(), weaponRatio * 100,
                m.spawns.size(), spawnRatio * 100, m.doors.size(), badDoors);
        assertTrue(spawnRatio >= 0.9, gen.id() + " 도달 가능한 리스폰 비율 " + spawnRatio);
        assertTrue(weaponRatio >= 0.9, gen.id() + " 도달 가능한 무기 비율 " + weaponRatio);
        // 5) NPC 길찾기: 40블록 이내 무작위 리스폰 지점 쌍 사이 경로 (NPC 와 같은 탐색 한도)
        Random r = new Random(9);
        int tries = 0, found = 0;
        long pathNs = 0;
        List<Vec3> sp = m.spawns;
        while (tries < 60) {
            Vec3 a = sp.get(r.nextInt(sp.size())), b = sp.get(r.nextInt(sp.size()));
            if (a.distance(b) > 40 || a.distance(b) < 6) continue;
            NavGrid.Node na = g.nearest(a), nb = g.nearest(b);
            if (na == null || nb == null || !main.contains(na.key) || !main.contains(nb.key)) continue;
            tries++;
            long t1 = System.nanoTime();
            List<Vec3> path = dev.violence.logic.AStar.find(g, na, nb, 4000);
            pathNs += System.nanoTime() - t1;
            if (!path.isEmpty() && path.getLast().distance(nb.pos()) < 0.01) found++;
        }
        System.out.printf("[%s] 길찾기 성공 %d/%d, 평균 %.2fms%n", gen.id(), found, tries, pathNs / 1e6 / Math.max(1, tries));
        assertTrue(found >= tries * 0.85, gen.id() + " 길찾기 성공률 " + found + "/" + tries);
    }

    @Test
    void blockStoreRoundTrip() throws Exception {
        List<String> pal = List.of("minecraft:air", "minecraft:stone", "minecraft:oak_slab[type=top,waterlogged=false]");
        int sx = 7, sy = 5, sz = 9;
        int[] data = new int[sx * sy * sz];
        Random r = new Random(1);
        for (int i = 0; i < data.length; i++) data[i] = r.nextInt(10) < 6 ? 0 : 1 + r.nextInt(2);
        BlockStore s = new BlockStore(-3, 60, 4, sx, sy, sz, pal, data);
        File f = Files.createTempFile("vmap", ".vmap").toFile();
        s.save(f);
        BlockStore l = BlockStore.load(f);
        assertEquals(s.ox, l.ox);
        assertEquals(s.oy, l.oy);
        assertEquals(s.sz, l.sz);
        assertEquals(pal, l.palette);
        assertArrayEquals(data, l.data);
        f.delete();
    }
}
