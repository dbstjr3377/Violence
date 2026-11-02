package dev.violence.mapgen;


/** 방 종류별 가구 배치. 벽에 붙여 배치해 통로를 막지 않는다. */
public final class Furnish {
    private Furnish() {}

    private static String b(String s) { return s; }

    /** 방 안쪽 벽을 따라 놓을 수 있는 칸인가 (출입구 바로 앞 제외) */
    static boolean freeCell(MapBuilder m, int x, int y, int z) {
        if (!m.isAir(x, y + 1, z) || !m.isAir(x, y + 2, z) || m.isAir(x, y, z)) return false;
        int[][] d = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] o : d) {
            int nx = x + o[0], nz = z + o[1];
            // 이웃이 "위는 막히고 아래 2칸이 빈" 벽 구멍(문틀)이면 피함
            boolean opening = m.isAir(nx, y + 1, nz) && m.isAir(nx, y + 2, nz) && !m.isAir(nx, y + 3, nz);
            if (opening) return false;
        }
        return true;
    }

    /** 벽을 따라 무작위로 소품 블록 놓기 */
    static void alongWalls(MapBuilder m, Rect r, int y, int count, String... props) {
        for (int i = 0; i < count; i++) {
            int side = m.rnd.nextInt(4);
            int x, z;
            switch (side) {
                case 0 -> { x = r.x1(); z = r.z1() + m.rnd.nextInt(r.depth()); }
                case 1 -> { x = r.x2(); z = r.z1() + m.rnd.nextInt(r.depth()); }
                case 2 -> { z = r.z1(); x = r.x1() + m.rnd.nextInt(r.width()); }
                default -> { z = r.z2(); x = r.x1() + m.rnd.nextInt(r.width()); }
            }
            if (!freeCell(m, x, y, z)) continue;
            m.set(x, y + 1, z, props[m.rnd.nextInt(props.length)]);
        }
    }

    public static void livingRoom(MapBuilder m, Rect r, int y) {
        // 소파 (계단 블록) + 탁자 + TV
        int sx = r.x1() + 1;
        if (r.depth() >= 5 && r.width() >= 5) {
            for (int z = r.z1() + 1; z <= Math.min(r.z2() - 1, r.z1() + 3); z++) {
                if (freeCell(m, r.x1(), y, z)) m.set(r.x1(), y + 1, z, b("minecraft:red_terracotta"));
            }
            int tx = sx + 1, tz = r.z1() + 2;
            if (m.isAir(tx, y + 1, tz)) m.table(tx, y, tz, true);
            if (freeCell(m, r.x2(), y, r.z1() + 2)) {
                m.set(r.x2(), y + 1, r.z1() + 2, b("minecraft:black_concrete"));
                m.set(r.x2(), y + 2, r.z1() + 2, b("minecraft:black_stained_glass"));
            }
        }
        alongWalls(m, r, y, 2, b("minecraft:potted_fern"), b("minecraft:bookshelf"), b("minecraft:barrel[facing=up]"));
        m.populate(r, y, 2, 1);
    }

    public static void bedroom(MapBuilder m, Rect r, int y) {
        int bx = r.x2(), bz = r.z2();
        if (freeCell(m, bx, y, bz) && freeCell(m, bx, y, bz - 1)) {
            m.set(bx, y + 1, bz, b("minecraft:white_wool"));
            m.set(bx, y + 1, bz - 1, b("minecraft:light_blue_wool"));
            m.weaponSpot(bx + 0.5, y + 2, bz - 0.5);
        }
        alongWalls(m, r, y, 2, b("minecraft:spruce_planks"), b("minecraft:chiseled_bookshelf"), b("minecraft:potted_dead_bush"));
        m.populate(r, y, 1, 1);
    }

    public static void kitchen(MapBuilder m, Rect r, int y) {
        for (int x = r.x1(); x <= r.x2(); x++) {
            if (!freeCell(m, x, y, r.z1())) continue;
            int roll = m.rnd.nextInt(6);
            String d = switch (roll) {
                case 0 -> b("minecraft:smoker[facing=south]");
                case 1 -> b("minecraft:cauldron");
                case 2 -> b("minecraft:iron_block");
                default -> m.theme.counter;
            };
            m.set(x, y + 1, r.z1(), d);
            if (roll >= 3 && m.rnd.nextInt(3) == 0) m.weaponSpot(x + 0.5, y + 2, r.z1() + 0.5);
        }
        if (r.width() >= 5 && r.depth() >= 5) m.table(r.cx(), y, r.cz(), true);
        m.populate(r, y, 1, 0);
    }

    public static void bathroom(MapBuilder m, Rect r, int y) {
        alongWalls(m, r, y, 3, b("minecraft:cauldron"), b("minecraft:white_concrete"), b("minecraft:quartz_slab"));
        m.populate(r, y, 1, 1);
    }

    public static void office(MapBuilder m, Rect r, int y) {
        // 책상 줄
        for (int x = r.x1() + 1; x <= r.x2() - 1; x += 3) {
            for (int z = r.z1() + 1; z <= r.z2() - 1; z += 3) {
                if (!m.isAir(x, y + 1, z)) continue;
                m.table(x, y, z, m.rnd.nextInt(3) == 0);
                if (m.isAir(x, y + 1, z + 1)) m.set(x, y + 1, z + 1, b("minecraft:dark_oak_stairs[facing=north]"));
            }
        }
        alongWalls(m, r, y, 2, b("minecraft:bookshelf"), b("minecraft:potted_bamboo"), b("minecraft:barrel[facing=up]"));
        m.populate(r, y, 2, 1);
    }

    public static void storage(MapBuilder m, Rect r, int y) {
        alongWalls(m, r, y, Math.max(3, r.width()), b("minecraft:barrel[facing=up]"), b("minecraft:stripped_oak_log"), b("minecraft:hay_block"), b("minecraft:composter"));
        m.populate(r, y, 1, 2);
    }

    /** 방 크기로 종류를 정해 가구 배치 */
    public static void auto(MapBuilder m, MapBuilder.Room room, boolean residential) {
        Rect r = room.rect();
        int y = room.y();
        int a = r.area();
        if (residential) {
            if (a >= 40) livingRoom(m, r, y);
            else if (a >= 24) {
                if (m.rnd.nextBoolean()) bedroom(m, r, y);
                else kitchen(m, r, y);
            }
            else bathroom(m, r, y);
        } else {
            if (a >= 30) office(m, r, y);
            else storage(m, r, y);
        }
    }
}
