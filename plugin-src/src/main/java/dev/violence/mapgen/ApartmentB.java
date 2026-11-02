package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;

/**
 * 아파트 B동: 2층 ㄷ자 건물이 가운데 안뜰을 둘러싼 구조.
 * 안뜰(분수, 벤치, 나무)과 각 동의 복도가 1층 출입구로 이어진다.
 */
public final class ApartmentB implements MapGenerator {
    @Override public String id() { return "apartment_b"; }
    @Override public String displayName() { return "아파트 B동"; }

    @Override
    public GameMap generate(BlockAccess world, Random rnd) {
        Theme t = Theme.of("minecraft:bricks", "minecraft:terracotta", "minecraft:spruce_planks",
                "minecraft:mud_bricks", "minecraft:smooth_sandstone", "minecraft:lantern[hanging=true]",
                "minecraft:glass_pane", "minecraft:dark_oak_slab[type=top]", "minecraft:polished_granite",
                "minecraft:stripped_spruce_wood", "minecraft:grass_block");
        MapBuilder m = new MapBuilder(world, rnd, t);
        int y0 = dev.violence.fx.ShaderZones.baseY(id());   // 쉐이더 구역 높이
        // 안뜰 바닥 (지붕 없음)
        Rect yard = new Rect(-21, -13, 21, 33);
        m.floor(yard, y0, "minecraft:grass_block");
        for (int x = -2; x <= 2; x++) m.fill(x, y0, -12, x, y0, 33, "minecraft:stone_bricks");
        for (int z = 8; z <= 12; z++) m.fill(-20, y0, z, 20, y0, z, "minecraft:stone_bricks");
        // 분수
        m.fill(-3, y0 + 1, 7, 3, y0 + 1, 13, "minecraft:stone_brick_slab");
        m.fill(-2, y0 + 1, 8, 2, y0 + 1, 12, "minecraft:stone_brick_slab[type=bottom,waterlogged=true]");
        m.set(0, y0 + 1, 10, "minecraft:chiseled_stone_bricks");
        m.set(0, y0 + 2, 10, "minecraft:stone_brick_wall");
        // 나무와 벤치
        int[][] trees = {{-15, -6}, {15, -6}, {-15, 26}, {15, 26}, {-15, 10}, {15, 10}};
        for (int[] tr : trees) {
            for (int h = 1; h <= 4; h++) m.set(tr[0], y0 + h, tr[1], "minecraft:oak_log");
            for (int dx = -2; dx <= 2; dx++)
                for (int dz = -2; dz <= 2; dz++)
                    for (int h = 4; h <= 6; h++)
                        if (Math.abs(dx) + Math.abs(dz) + (h - 4) <= 3 && !(dx == 0 && dz == 0 && h < 5))
                            m.set(tr[0] + dx, y0 + h, tr[1] + dz, "minecraft:oak_leaves[persistent=true]");
        }
        for (int i = 0; i < 6; i++) {
            int bx = -12 + i * 5;
            m.set(bx, y0 + 1, 0, "minecraft:spruce_stairs[facing=north]");
            m.set(bx, y0 + 1, 20, "minecraft:spruce_stairs[facing=south]");
            m.weaponSpot(bx + 0.5, y0 + 1, 1.5);
        }
        // 남쪽 담장 (넘어갈 수 없음)
        for (int x = -22; x <= 22; x++) {
            m.set(x, y0, 34, t.wall);
            m.set(x, y0 + 1, 34, t.wall);
            m.set(x, y0 + 2, 34, "minecraft:iron_bars[east=true,west=true]");
        }
        m.populate(yard, y0, 10, 4);
        // 가로등
        for (int z = -8; z <= 30; z += 12) {
            for (int x : new int[]{-6, 6}) {
                m.set(x, y0 + 1, z, "minecraft:dark_oak_fence");
                m.set(x, y0 + 2, z, "minecraft:dark_oak_fence");
                m.set(x, y0 + 3, z, "minecraft:ochre_froglight");
            }
        }

        // 세 동 (북, 서, 동) × 2층
        Rect north = new Rect(-36, -30, 36, -14);
        Rect westW = new Rect(-36, -13, -22, 34);
        Rect eastW = new Rect(22, -13, 36, 34);
        for (int f = 0; f < 2; f++) {
            int y = y0 + f * MapBuilder.H;
            // 북동: 복도는 안뜰 쪽 (z -17..-15), 세대는 바깥쪽
            m.shell(north, y, t.wall, t.floor, t.ceiling);
            Rect nc = new Rect(-35, -17, 35, -15);
            m.floor(nc, y, t.floorAlt);
            m.wallX(-35, 35, -18, y, t.wallAccent);
            m.lights(nc, y, 6);
            wing(m, t, new Rect(-35, -29, 35, -19), y, true, -18, rnd);
            // 서동
            m.shell(westW, y, t.wall, t.floor, t.ceiling);
            Rect wc = new Rect(-25, -12, -23, 33);
            m.floor(wc, y, t.floorAlt);
            m.wallZ(-26, -12, 22, y, t.wallAccent);
            m.lights(wc, y, 6);
            wing(m, t, new Rect(-35, -12, -27, 21), y, false, -26, rnd);
            m.wallX(-35, -27, 22, y, t.wall);
            m.populate(new Rect(-35, 23, -27, 30), y, 2, 1);
            // 동동
            m.shell(eastW, y, t.wall, t.floor, t.ceiling);
            Rect ec = new Rect(23, -12, 25, 33);
            m.floor(ec, y, t.floorAlt);
            m.wallZ(26, -12, 22, y, t.wallAccent);
            m.lights(ec, y, 6);
            wing(m, t, new Rect(27, -12, 35, 21), y, false, 26, rnd);
            m.wallX(27, 35, 22, y, t.wall);
            m.populate(new Rect(27, 23, 35, 30), y, 2, 1);
            // 동끼리 연결 (북동-서동, 북동-동동)
            m.doorway(-25, y, -14, true, 3);
            m.doorway(23, y, -14, true, 3);
            m.clearBox(-25, y + 1, -13, -23, y + 2, -13);
            m.clearBox(23, y + 1, -13, 25, y + 2, -13);
            // 안뜰 쪽 창
            for (int x = -18; x <= 18; x += 4) m.window(x, y, -14, true, 2, true);
            for (int z = -10; z <= 30; z += 4) {
                m.window(-22, y, z, false, 2, true);
                m.window(22, y, z, false, 2, true);
            }
            m.populate(nc, y, 3, 2);
            m.populate(wc, y, 3, 2);
            m.populate(ec, y, 3, 2);
        }
        // 1층 안뜰 출입구
        m.door(-22, y0, 4, false);
        m.door(-22, y0, 24, false);
        m.door(22, y0, 4, false);
        m.door(22, y0, 24, false);
        m.door(-8, y0, -14, true);
        m.door(8, y0, -14, true);
        // 계단 (서동/동동 복도 끝)
        var slab = "minecraft:mud_brick_slab";
        m.stairs(-34, y0, 31, 1, 0, 2, t.floorAlt, slab);
        m.stairs(34, y0, 31, -1, 0, 2, t.floorAlt, slab);
        m.floor(north, y0 + 2 * MapBuilder.H, "minecraft:dark_oak_planks");
        m.floor(westW, y0 + 2 * MapBuilder.H, "minecraft:dark_oak_planks");
        m.floor(eastW, y0 + 2 * MapBuilder.H, "minecraft:dark_oak_planks");
        return m.finish(id(), displayName());
    }

    /** 한 동의 세대 줄: 복도 벽(corridorWall)을 따라 세대를 나누고 현관문을 낸다 */
    private void wing(MapBuilder m, Theme t, Rect area, int y, boolean alongX, int corridorWall, Random rnd) {
        int len = alongX ? area.width() : area.depth();
        int units = Math.max(2, len / 11);
        int step = len / units;
        for (int u = 0; u < units; u++) {
            int a = (alongX ? area.x1() : area.z1()) + u * step;
            int b = u == units - 1 ? (alongX ? area.x2() : area.z2()) : a + step - 2;
            if (u < units - 1) {
                if (alongX) m.wallZ(b + 1, area.z1(), area.z2(), y, t.wall);
                else m.wallX(area.x1(), area.x2(), b + 1, y, t.wall);
            }
            Rect unit = alongX ? new Rect(a, area.z1(), b, area.z2()) : new Rect(area.x1(), a, area.x2(), b);
            int d = a + 2 + rnd.nextInt(Math.max(1, (b - a) - 3));
            if (alongX) m.door(d, y, corridorWall, true);
            else m.door(corridorWall, y, d, false);
            List<MapBuilder.Room> rooms = m.subdivide(unit, y, 4, 7, t.wall, 0.5, 0.0);
            for (MapBuilder.Room r : rooms) {
                m.lights(r.rect(), y, 5);
                Furnish.auto(m, r, true);
            }
        }
        // 바깥쪽 창
        if (alongX) for (int x = area.x1() + 2; x < area.x2() - 2; x += 5) m.window(x, y, area.z1() - 1, true, 2, true);
        else {
            int outerX = area.x1() < 0 ? area.x1() - 1 : area.x2() + 1;
            for (int z = area.z1() + 2; z < area.z2() - 2; z += 5) m.window(outerX, y, z, false, 2, true);
        }
    }
}
