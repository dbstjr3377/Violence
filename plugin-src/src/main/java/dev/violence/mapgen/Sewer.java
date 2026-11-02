package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.HashSet;
import java.util.Random;
import java.util.Set;

/**
 * 하수구: 미로처럼 얽힌 터널(가운데 물길) + 교차로 공간 + 정비실/펌프실.
 * 1층 구조지만 넓고 시야가 짧다.
 */
public final class Sewer implements MapGenerator {
    private static final int CELL = 15;
    private static final int GRID = 7;

    @Override public String id() { return "sewer"; }
    @Override public String displayName() { return "하수구"; }

    @Override
    public GameMap generate(BlockAccess world, Random rnd) {
        Theme t = Theme.of("minecraft:mossy_stone_bricks", "minecraft:stone_bricks", "minecraft:stone_bricks",
                "minecraft:cracked_stone_bricks", "minecraft:deepslate_bricks", "minecraft:verdant_froglight",
                "minecraft:glass_pane", "minecraft:spruce_slab[type=top]", "minecraft:polished_deepslate",
                "minecraft:iron_block", "minecraft:mud");
        MapBuilder m = new MapBuilder(world, rnd, t);
        int y = 64;
        int origin = -(CELL * GRID) / 2;
        // 전체를 돌로 채운 뒤 터널을 파낸다
        int x1 = origin - 1, z1 = origin - 1, x2 = origin + CELL * GRID, z2 = origin + CELL * GRID;
        m.fill(x1, y, z1, x2, y, z2, t.floor);
        m.fill(x1, y + 5, z1, x2, y + 5, z2, t.ceiling);
        m.fill(x1, y + 1, z1, x2, y + 4, z2, t.wall);
        // 미로 (스패닝 트리 + 추가 고리)
        boolean[][] visited = new boolean[GRID][GRID];
        List<int[]> edges = new ArrayList<>();
        carve(0, 0, visited, edges, rnd);
        for (int i = 0; i < GRID * 2; i++) {
            int cx = rnd.nextInt(GRID - 1), cz = rnd.nextInt(GRID);
            if (rnd.nextBoolean()) edges.add(new int[]{cx, cz, cx + 1, cz});
            else if (cz < GRID - 1) edges.add(new int[]{cx, cz, cx, cz + 1});
        }
        String water = "minecraft:stone_brick_slab[type=bottom,waterlogged=true]";
        for (int[] e : edges) {
            int ax = origin + e[0] * CELL + CELL / 2, az = origin + e[1] * CELL + CELL / 2;
            int bx = origin + e[2] * CELL + CELL / 2, bz = origin + e[3] * CELL + CELL / 2;
            boolean alongX = az == bz;
            int lo = alongX ? Math.min(ax, bx) : Math.min(az, bz), hi = alongX ? Math.max(ax, bx) : Math.max(az, bz);
            for (int c = lo; c <= hi; c++) {
                for (int wv = -2; wv <= 2; wv++) {
                    int x = alongX ? c : ax + wv, z = alongX ? az + wv : c;
                    m.clearBox(x, y + 1, z, x, y + 3, z);
                    if (Math.abs(wv) <= 1) m.clear(x, y + 4, z);
                    if (wv == 0) m.set(x, y, z, water);
                }
            }
            // 터널 천장 조명 (드문드문)
            if (rnd.nextInt(2) == 0) {
                int lc = (lo + hi) / 2;
                int lx = alongX ? lc : ax - 2, lz = alongX ? az - 2 : lc;
                m.set(lx, y + 3, lz, t.light);
            }
        }
        // 교차로 공간
        for (int gx = 0; gx < GRID; gx++) {
            for (int gz = 0; gz < GRID; gz++) {
                int cx = origin + gx * CELL + CELL / 2, cz = origin + gz * CELL + CELL / 2;
                int r = rnd.nextInt(4) == 0 ? 4 : 3;
                for (int x = cx - r; x <= cx + r; x++)
                    for (int z = cz - r; z <= cz + r; z++) m.clearBox(x, y + 1, z, x, y + 3, z);
                m.set(cx, y + 4, cz, t.light);
                m.clear(cx, y + 4, cz + 1);
                if (r == 4) {
                    // 기둥 4개
                    for (int dx : new int[]{-2, 2}) for (int dz : new int[]{-2, 2}) m.fill(cx + dx, y + 1, cz + dz, cx + dx, y + 3, cz + dz, t.wallAccent);
                }
                m.populate(new Rect(cx - r, cz - r, cx + r, cz + r), y, 2, rnd.nextInt(3) == 0 ? 2 : 1);
            }
        }
        // 정비실: 동서 터널 남쪽 벽에 문을 내고 그 뒤 바위 속에 방을 판다
        int roomsMade = 0;
        List<int[]> eastEdges = new ArrayList<>();
        for (int[] e : edges) if (e[1] == e[3] && Math.abs(e[0] - e[2]) == 1) eastEdges.add(e);
        Collections.shuffle(eastEdges, rnd);
        Set<String> used = new HashSet<>();
        for (int[] e : eastEdges) {
            if (roomsMade >= 8) break;
            int gx = Math.min(e[0], e[2]), gz = e[1];
            if (gz >= GRID - 1 || !used.add(gx + ":" + gz)) continue;
            int cx = origin + gx * CELL + CELL / 2, cz = origin + gz * CELL + CELL / 2;
            Rect room = new Rect(cx + 6, cz + 4, cx + 9, cz + 8);
            m.clearBox(room.x1(), y + 1, room.z1(), room.x2(), y + 3, room.z2());
            m.door(cx + 7, y, cz + 3, true);
            m.set(room.cx(), y + 4, room.cz(), t.light);
            Furnish.storage(m, room, y);
            m.table(room.x2(), y, room.z2(), true);
            roomsMade++;
        }
        // 펌프실 (큰 방)
        int pcx = origin + (GRID / 2) * CELL, pcz = origin + (GRID / 2) * CELL;
        Rect pump = new Rect(pcx - 6, pcz - 6, pcx + 6, pcz + 6);
        m.clearBox(pump.x1(), y + 1, pump.z1(), pump.x2(), y + 4, pump.z2());
        for (int x = pcx - 4; x <= pcx + 4; x += 4) {
            m.fill(x, y + 1, pcz - 1, x, y + 3, pcz + 1, "minecraft:iron_block");
            m.set(x, y + 4, pcz, "minecraft:lightning_rod");
        }
        m.lights(pump, y - 1, 4);
        m.populate(pump, y, 4, 3);
        // 바깥 경계 (지붕)
        m.fill(x1, y + 6, z1, x2, y + 6, z2, "minecraft:stone");
        return m.finish(id(), displayName());
    }

    private void carve(int x, int z, boolean[][] visited, List<int[]> edges, Random rnd) {
        visited[x][z] = true;
        List<int[]> dirs = new ArrayList<>(List.of(new int[]{1, 0}, new int[]{-1, 0}, new int[]{0, 1}, new int[]{0, -1}));
        Collections.shuffle(dirs, rnd);
        for (int[] d : dirs) {
            int nx = x + d[0], nz = z + d[1];
            if (nx < 0 || nz < 0 || nx >= GRID || nz >= GRID || visited[nx][nz]) continue;
            edges.add(new int[]{x, z, nx, nz});
            carve(nx, nz, visited, edges, rnd);
        }
    }
}
