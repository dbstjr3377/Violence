package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;

/**
 * 식당: 넓은 홀(테이블, 부스석, 바 카운터), 주방, 냉동고, 화장실, 사무실,
 * 그리고 계단으로 내려가는 지하 창고/와인 셀러.
 */
public final class Restaurant implements MapGenerator {
    @Override public String id() { return "restaurant"; }
    @Override public String displayName() { return "식당"; }

    @Override
    public GameMap generate(BlockAccess world, Random rnd) {
        Theme t = Theme.of("minecraft:stripped_dark_oak_wood", "minecraft:red_terracotta", "minecraft:polished_granite",
                "minecraft:black_glazed_terracotta", "minecraft:dark_oak_planks", "minecraft:shroomlight",
                "minecraft:orange_stained_glass", "minecraft:dark_oak_slab[type=top]", "minecraft:polished_deepslate",
                "minecraft:gold_block", "minecraft:stone");
        MapBuilder m = new MapBuilder(world, rnd, t);
        int y = 64, yb = 64 - MapBuilder.H;
        Rect outer = new Rect(-34, -26, 34, 26);
        m.shell(outer, y, t.wall, t.floor, t.ceiling);
        m.shell(outer, yb, "minecraft:bricks", "minecraft:deepslate_bricks", t.floor);

        // ── 1층 ──
        // 홀: z 0..25 (남쪽), 주방/뒤쪽: z -25..-1
        m.wallX(-33, 33, -1, y, t.wallAccent);
        m.doorway(-3, y, -1, true, 2);
        m.door(10, y, -1, true);
        m.door(-20, y, -1, true);
        Rect hall = new Rect(-33, 0, 33, 25);
        m.checker(hall, y, "minecraft:polished_granite", "minecraft:black_glazed_terracotta");
        // 테이블 (2x2) + 의자
        for (int x = -28; x <= 16; x += 6) {
            for (int z = 4; z <= 20; z += 6) {
                for (int dx = 0; dx < 2; dx++) for (int dz = 0; dz < 2; dz++) m.table(x + dx, y, z + dz, dx == 0 && dz == 0 && rnd.nextInt(2) == 0);
                m.set(x - 1, y + 1, z, "minecraft:dark_oak_stairs[facing=east]");
                m.set(x + 2, y + 1, z + 1, "minecraft:dark_oak_stairs[facing=west]");
            }
        }
        // 부스석 (동쪽 벽)
        for (int z = 3; z <= 23; z += 4) {
            m.set(32, y + 1, z, "minecraft:red_wool");
            m.set(32, y + 1, z + 1, "minecraft:red_wool");
            m.table(30, y, z, true);
            m.table(30, y, z + 1, false);
            m.set(28, y + 1, z, "minecraft:dark_oak_stairs[facing=east]");
        }
        // 바 카운터 (북쪽 홀)
        m.counter(-30, 2, -10, 2, y);
        for (int x = -30; x <= -10; x += 3) {
            m.set(x, y + 1, 4, "minecraft:dark_oak_fence");
            m.weaponSpot(x + 0.5, y + 2, 2.5);
        }
        m.lights(hall, y, 5);
        m.populate(hall, y, 10, 4);
        // 정면 큰 창
        for (int x = -30; x <= 30; x += 5) m.window(x, y, 26, true, 3, true);
        m.door(0, y, 26, true);

        // 주방
        Rect kitchen = new Rect(-10, -25, 33, -2);
        m.wallZ(-11, -25, -2, y, t.wallAccent);
        m.door(-11, y, -10, false);
        m.floor(kitchen, y, t.floorAlt);
        for (int z = -22; z <= -6; z += 5) {
            m.counter(-6, z, 20, z, y);
            for (int x = -5; x <= 19; x += 4) {
                m.set(x, y + 1, z, (rnd.nextBoolean() ? "minecraft:smoker[facing=north]" : "minecraft:furnace[facing=north]"));
                if (rnd.nextInt(2) == 0) m.weaponSpot(x + 1.5, y + 2, z + 0.5);
            }
        }
        m.lights(kitchen, y, 5);
        m.populate(kitchen, y, 5, 3);
        // 냉동고
        Rect freezer = new Rect(24, -25, 33, -15);
        m.wallX(24, 33, -14, y, "minecraft:packed_ice");
        m.wallZ(23, -25, -14, y, "minecraft:packed_ice");
        m.door(28, y, -14, true);
        m.floor(freezer, y, "minecraft:blue_ice");
        for (int z = -24; z <= -16; z += 2) {
            m.set(33, y + 1, z, "minecraft:snow_block");
            m.set(33, y + 2, z, "minecraft:packed_ice");
        }
        m.lights(freezer, y, 4);
        m.populate(freezer, y, 1, 2);
        // 서쪽 뒤쪽: 화장실/사무실 (BSP)
        List<MapBuilder.Room> back = m.subdivide(new Rect(-33, -25, -12, -2), y, 4, 8, t.wall, 0.7, 0.0);
        for (MapBuilder.Room r : back) {
            m.lights(r.rect(), y, 4);
            if (r.rect().area() < 25) Furnish.bathroom(m, r.rect(), y);
            else Furnish.office(m, r.rect(), y);
        }
        m.exteriorWindows(outer, y, 6, 2);

        // ── 지하 ── (주방에서 계단으로)
        String slab = "minecraft:deepslate_brick_slab";
        // 계단: 지하(yb) → 1층(y). 1층 바닥 z -4..-3, x 0→9
        m.stairs(0, yb, -4, 1, 0, 2, "minecraft:deepslate_bricks", slab);
        Rect cellar = new Rect(-33, -25, 33, 25);
        List<MapBuilder.Room> rooms = m.subdivide(cellar, yb, 6, 14, "minecraft:bricks", 0.5, 0.0);
        for (MapBuilder.Room r : rooms) {
            m.lights(r.rect(), yb, 5);
            Furnish.storage(m, r.rect(), yb);
            // 와인 랙
            for (int x = r.rect().x1(); x <= r.rect().x2(); x += 2) {
                if (Furnish.freeCell(m, x, yb, r.rect().z2())) {
                    m.set(x, yb + 1, r.rect().z2(), "minecraft:chiseled_bookshelf");
                }
            }
        }
        // 지하 계단 주변 공간 확보
        m.clearBox(-2, yb + 1, -6, 11, yb + 3, -1);
        // 분할 벽이 계단을 덮었을 수 있으므로 다시 배치
        m.stairs(0, yb, -4, 1, 0, 2, "minecraft:deepslate_bricks", slab);
        m.floor(outer, y + MapBuilder.H, "minecraft:dark_oak_planks");
        return m.finish(id(), displayName());
    }
}
