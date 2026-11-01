package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;
import org.bukkit.World;
import org.bukkit.block.data.BlockData;

/**
 * 교도소: 2층 높이 감방동(양쪽 감방 + 2층 통로)을 중심으로
 * 북쪽 식당/주방, 남쪽 경비실/샤워실/면회실이 이어진다.
 */
public final class Prison implements MapGenerator {
    @Override public String id() { return "prison"; }
    @Override public String displayName() { return "교도소"; }

    @Override
    public GameMap generate(World world, Random rnd) {
        Theme t = Theme.of("minecraft:stone_bricks", "minecraft:cracked_stone_bricks", "minecraft:smooth_stone",
                "minecraft:polished_andesite", "minecraft:stone_bricks", "minecraft:redstone_lamp[lit=true]",
                "minecraft:glass_pane", "minecraft:iron_trapdoor[half=top,open=false]", "minecraft:polished_andesite",
                "minecraft:iron_block", "minecraft:gravel");
        MapBuilder m = new MapBuilder(world, rnd, t);
        int y0 = 64, y1 = 64 + MapBuilder.H;
        Rect outer = new Rect(-38, -34, 38, 34);
        m.shell(outer, y0, t.wall, t.floor, t.ceiling);
        m.shell(outer, y1, t.wall, t.floor, t.ceiling);
        BlockData barsX = Theme.b("minecraft:iron_bars[east=true,west=true]");
        // 감방동: x -32..32, z -15..15. 가운데 홀 z -7..7 (2층 높이)
        Rect hall = new Rect(-32, -7, 32, 7);
        m.floor(hall, y0, t.floorAlt);
        m.clearBox(-32, y1, -5, 32, y1, 5);
        m.wallX(-37, 37, -16, y0, t.wall);
        m.wallX(-37, 37, 16, y0, t.wall);
        m.wallX(-37, 37, -16, y1, t.wall);
        m.wallX(-37, 37, 16, y1, t.wall);
        for (int y : new int[]{y0, y1}) {
            for (int side : new int[]{-1, 1}) {
                int front = side * 8; // 감방 앞면 z=±8
                int back = side * 15;
                for (int cx = -32; cx <= 28; cx += 5) {
                    // 감방 칸막이
                    m.wallZ(cx - 1, Math.min(front, back), Math.max(front, back), y, t.wall);
                    // 앞면 쇠창살 + 문
                    for (int x = cx; x <= cx + 3; x++) for (int yy = y + 1; yy < y + MapBuilder.H; yy++) m.set(x, yy, front, barsX);
                    m.door(cx + 1 + rnd.nextInt(2), y, front, true);
                    // 침대 + 변기
                    int bz = front + side * 6;
                    m.set(cx, y + 1, bz, Theme.b("minecraft:white_wool"));
                    m.set(cx, y + 1, bz - side, Theme.b("minecraft:white_wool"));
                    m.set(cx + 3, y + 1, bz, Theme.b("minecraft:cauldron"));
                    m.set(cx + 1, y + MapBuilder.H, front + side * 3, t.light);
                    if (rnd.nextInt(2) == 0) m.weaponSpot(cx + 0.5, y + 2, bz + 0.5);
                    if (rnd.nextInt(2) == 0) m.spawn(cx + 2.5, y + 1, front + side * 4 + 0.5);
                }
                m.wallZ(32, Math.min(front, back), Math.max(front, back), y, t.wall);
            }
        }
        // 2층 통로 (감방 앞 z=±6..±7) + 쇠창살 난간
        for (int side : new int[]{-1, 1}) {
            for (int x = -32; x <= 32; x++) {
                m.set(x, y1, side * 6, t.floorAlt);
                m.set(x, y1, side * 7, t.floorAlt);
                m.set(x, y1 + 1, side * 5, barsX);
            }
        }
        // 홀 조명
        for (int x = -30; x <= 30; x += 6) m.set(x, y1 + MapBuilder.H, 0, t.light);
        m.populate(hall, y0, 10, 5);
        // 홀 양 끝 계단 (1층 → 2층 통로)
        BlockData slab = Theme.b("minecraft:smooth_stone_slab");
        m.stairs(-31, y0, -7, 1, 0, 2, t.floorAlt, slab);
        m.stairs(31, y0, 6, -1, 0, 2, t.floorAlt, slab);
        // 감방동 출입문 (북/남 구역으로)
        m.door(-20, y0, -16, true);
        m.door(20, y0, -16, true);
        m.door(-20, y0, 16, true);
        m.door(20, y0, 16, true);
        m.door(0, y0, -16, true);
        m.door(0, y0, 16, true);
        m.door(-20, y1, -16, true);
        m.door(20, y1, 16, true);

        // 북쪽: 식당 (1층), 2층은 창고/의무실
        Rect canteen = new Rect(-37, -33, 10, -17);
        m.wallZ(11, -33, -17, y0, t.wall);
        m.door(11, y0, -25, false);
        for (int x = -33; x <= 6; x += 6) {
            for (int z = -30; z <= -20; z += 5) {
                for (int i = 0; i < 4; i++) m.table(x + i, y0, z, i == 1 && rnd.nextInt(2) == 0);
                for (int i = 0; i < 4; i++) {
                    m.set(x + i, y0 + 1, z - 1, Theme.b("minecraft:spruce_slab"));
                    m.set(x + i, y0 + 1, z + 1, Theme.b("minecraft:spruce_slab"));
                }
            }
        }
        m.lights(canteen, y0, 6);
        m.populate(canteen, y0, 6, 3);
        Rect kitchen = new Rect(12, -33, 37, -17);
        Furnish.kitchen(m, kitchen, y0);
        m.counter(14, -24, 30, -24, y0);
        for (int x = 15; x <= 29; x += 4) m.weaponSpot(x + 0.5, y0 + 2, -23.5);
        m.lights(kitchen, y0, 6);
        List<MapBuilder.Room> up = m.subdivide(new Rect(-37, -33, 37, -17), y1, 5, 10, t.wall, 0.6, 0.0);
        for (MapBuilder.Room r : up) {
            m.lights(r.rect(), y1, 5);
            Furnish.storage(m, r.rect(), y1);
        }
        // 남쪽: 경비실/샤워실/면회실 (1층), 2층 사무실
        List<MapBuilder.Room> south = m.subdivide(new Rect(-37, 17, 37, 33), y0, 5, 11, t.wall, 0.65, 0.15);
        for (MapBuilder.Room r : south) {
            m.lights(r.rect(), y0, 5);
            if (r.rect().area() > 60) {
                // 면회실: 가운데 유리 칸막이
                m.window(r.rect().x1(), y0, r.rect().cz(), true, r.rect().width(), true);
                m.populate(r.rect(), y0, 2, 2);
            } else Furnish.auto(m, r, false);
        }
        List<MapBuilder.Room> south2 = m.subdivide(new Rect(-37, 17, 37, 33), y1, 5, 11, t.wall, 0.65, 0.2);
        for (MapBuilder.Room r : south2) {
            m.lights(r.rect(), y1, 5);
            Furnish.office(m, r.rect(), y1);
        }
        // 북/남 2층 계단
        m.stairs(-36, y0, -19, 0, -1, 2, t.floorAlt, slab);
        m.stairs(35, y0, 19, 0, 1, 2, t.floorAlt, slab);
        m.exteriorWindows(outer, y0, 6, 1);
        m.exteriorWindows(outer, y1, 6, 1);
        m.floor(outer, y1 + MapBuilder.H, Theme.b("minecraft:stone"));
        return m.finish(id(), displayName());
    }
}
