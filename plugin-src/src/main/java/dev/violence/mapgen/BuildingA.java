package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;

/**
 * 오피스 빌딩: 3층. 가운데 코어(계단, 화장실) 둘레로 칸막이 사무실과
 * 유리벽 회의실, 임원실이 배치된다.
 */
public final class BuildingA implements MapGenerator {
    @Override public String id() { return "building_a"; }
    @Override public String displayName() { return "오피스 빌딩"; }

    @Override
    public GameMap generate(BlockAccess world, Random rnd) {
        Theme t = Theme.of("minecraft:light_gray_concrete", "minecraft:gray_concrete", "minecraft:gray_wool",
                "minecraft:polished_andesite", "minecraft:smooth_quartz", "minecraft:sea_lantern",
                "minecraft:light_blue_stained_glass", "minecraft:smooth_quartz_slab[type=top]", "minecraft:smooth_quartz",
                "minecraft:polished_blackstone", "minecraft:stone");
        MapBuilder m = new MapBuilder(world, rnd, t);
        Rect outer = new Rect(-32, -26, 32, 26);
        int floors = 3;
        for (int f = 0; f < floors; f++) {
            int y = 64 + f * MapBuilder.H;
            m.shell(outer, y, t.wall, t.floor, t.ceiling);
            // 코어: x -7..7, z -5..5
            Rect core = new Rect(-7, -5, 7, 5);
            m.floor(core, y, t.floorAlt);
            m.wallX(-7, 7, -5, y, t.wallAccent);
            m.wallX(-7, 7, 5, y, t.wallAccent);
            m.wallZ(-7, -5, 5, y, t.wallAccent);
            m.wallZ(7, -5, 5, y, t.wallAccent);
            m.doorway(-1, y, 5, true, 3);
            m.door(-7, y, 0, false);
            m.door(7, y, 0, false);
            m.lights(core, y, 5);
            // 화장실 (코어 안 동쪽)
            m.wallZ(3, 1, 4, y, t.wall);
            m.door(3, y, 2, false);
            Furnish.bathroom(m, new Rect(4, 1, 6, 4), y);
            // 동쪽 블록: 회의실 (유리벽)
            Rect meetE = new Rect(18, -25, 31, -12);
            m.glassWall(18, y, -25, false, 14);
            m.glassWall(18, y, -11, true, 14);
            m.door(18, y, -18, false);
            m.counter(22, -20, 27, -17, y);
            for (int x = 22; x <= 27; x += 2) m.weaponSpot(x + 0.5, y + 2, -18.5);
            m.lights(meetE, y, 4);
            m.populate(meetE, y, 2, 0);
            // 서쪽: 임원실 줄 (BSP)
            Rect execs = new Rect(-31, -25, -20, 25);
            m.wallZ(-19, -25, 25, y, t.wall);
            for (int z = -22; z <= 22; z += 9) m.door(-19, y, z, false);
            List<MapBuilder.Room> rooms = m.subdivide(execs, y, 5, 9, t.wall, 0.6, 0.3);
            for (MapBuilder.Room r : rooms) {
                m.lights(r.rect(), y, 5);
                Furnish.office(m, r.rect(), y);
            }
            // 오픈 오피스: 칸막이 책상 무리
            for (int bx = -15; bx <= 14; bx += 7) {
                for (int bz = -22; bz <= 20; bz += 7) {
                    if (new Rect(-9, -7, 9, 7).contains(bx + 2, bz + 2)) continue;
                    if (meetE.contains(bx, bz) || meetE.contains(bx + 4, bz + 4)) continue;
                    if (overlapsStairs(bx, bz)) continue;
                    cubicle(m, bx, y, bz, rnd);
                }
            }
            m.lights(new Rect(-18, -25, 31, 25), y, 6);
            m.populate(new Rect(-18, -25, 17, 25), y, 8, 4);
            m.exteriorWindows(outer, y, 3, 2);
        }
        // 계단 (코어 안 서쪽 x -6..-5, 층마다 방향 교대)
        var slab = "minecraft:polished_andesite_slab";
        m.stairs(-6, 64, -4, 1, 0, 2, t.floorAlt, slab);
        // 2→3층은 동쪽 바깥 회의실 옆 복도
        m.stairs(15, 64 + MapBuilder.H, 24, 0, -1, 2, t.floorAlt, slab);
        // 1→2층 두 번째 계단 (남동쪽)
        m.stairs(29, 64, 24, 0, -1, 2, t.floorAlt, slab);
        m.floor(outer, 64 + floors * MapBuilder.H, "minecraft:gray_concrete");
        return m.finish(id(), displayName());
    }

    private static boolean overlapsStairs(int bx, int bz) {
        Rect c = new Rect(bx - 1, bz - 1, bx + 4, bz + 4);
        Rect[] stairs = {new Rect(14, 14, 17, 25), new Rect(28, 14, 31, 25)};
        for (Rect s : stairs) {
            if (c.x1() <= s.x2() && c.x2() >= s.x1() && c.z1() <= s.z2() && c.z2() >= s.z1()) return true;
        }
        return false;
    }

    /** 2x2 책상 + 낮은 유리 칸막이 */
    private void cubicle(MapBuilder m, int x, int y, int z, Random rnd) {
        var low = "minecraft:white_stained_glass_pane[east=true,west=true]";
        var lowZ = "minecraft:white_stained_glass_pane[north=true,south=true]";
        for (int i = 0; i < 4; i++) {
            if (m.isAir(x + i, y + 1, z + 1)) m.set(x + i, y + 1, z + 1, low);
        }
        if (m.isAir(x + 1, y + 1, z)) m.set(x + 1, y + 1, z, lowZ);
        if (m.isAir(x + 1, y + 1, z + 2)) m.set(x + 1, y + 1, z + 2, lowZ);
        if (m.isAir(x, y + 1, z)) m.table(x, y, z, rnd.nextInt(3) == 0);
        if (m.isAir(x + 2, y + 1, z)) m.table(x + 2, y, z, rnd.nextInt(4) == 0);
        if (m.isAir(x, y + 1, z + 2)) m.table(x, y, z + 2, rnd.nextInt(4) == 0);
        if (m.isAir(x + 2, y + 1, z + 2)) m.table(x + 2, y, z + 2, rnd.nextInt(3) == 0);
    }
}
