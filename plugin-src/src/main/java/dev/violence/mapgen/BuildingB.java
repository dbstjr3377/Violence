package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;
import org.bukkit.World;

/**
 * 고층 빌딩 로비: 2층 높이의 아트리움 로비(안내 데스크, 기둥, 화분)와
 * 2층 메자닌(유리 난간), 둘레의 사무실/보안실/창고.
 */
public final class BuildingB implements MapGenerator {
    @Override public String id() { return "building_b"; }
    @Override public String displayName() { return "고층 빌딩 로비"; }

    @Override
    public GameMap generate(World world, Random rnd) {
        Theme t = Theme.of("minecraft:quartz_block", "minecraft:black_concrete", "minecraft:polished_diorite",
                "minecraft:black_glazed_terracotta", "minecraft:smooth_quartz", "minecraft:sea_lantern",
                "minecraft:gray_stained_glass", "minecraft:polished_blackstone_slab[type=top]", "minecraft:polished_blackstone",
                "minecraft:gold_block", "minecraft:stone");
        MapBuilder m = new MapBuilder(world, rnd, t);
        Rect outer = new Rect(-34, -28, 34, 28);
        int y0 = 64, y1 = 64 + MapBuilder.H;
        m.shell(outer, y0, t.wall, t.floor, t.ceiling);
        m.shell(outer, y1, t.wall, t.floor, t.ceiling);
        // 아트리움: x -15..15, z -11..11 (2층 바닥 없음)
        Rect atrium = new Rect(-15, -11, 15, 11);
        m.checker(atrium, y0, t.floor, Theme.b("minecraft:polished_andesite"));
        m.clearBox(-15, y1, -11, 15, y1, 11);
        // 유리 난간 (2층)
        for (int x = -15; x <= 15; x++) {
            m.set(x, y1 + 1, -12, Theme.b("minecraft:gray_stained_glass_pane[east=true,west=true]"));
            m.set(x, y1 + 1, 12, Theme.b("minecraft:gray_stained_glass_pane[east=true,west=true]"));
        }
        for (int z = -11; z <= 11; z++) {
            m.set(-16, y1 + 1, z, Theme.b("minecraft:gray_stained_glass_pane[north=true,south=true]"));
            m.set(16, y1 + 1, z, Theme.b("minecraft:gray_stained_glass_pane[north=true,south=true]"));
        }
        // 기둥
        for (int x : new int[]{-12, 12}) for (int z : new int[]{-8, 8}) {
            m.fill(x, y0 + 1, z, x + 1, y1 + MapBuilder.H - 1, z + 1, Theme.b("minecraft:quartz_pillar"));
        }
        // 안내 데스크
        m.counter(-4, -2, 4, -2, y0);
        m.counter(-4, 2, 4, 2, y0);
        m.counter(-4, -1, -4, 1, y0);
        for (int x = -3; x <= 3; x += 2) m.weaponSpot(x + 0.5, y0 + 2, -1.5);
        // 화분 / 소파
        for (int x = -10; x <= 10; x += 5) {
            m.set(x, y0 + 1, -10, Theme.b("minecraft:potted_bamboo"));
            m.set(x, y0 + 1, 10, Theme.b("minecraft:potted_bamboo"));
        }
        for (int z = -6; z <= 6; z += 3) {
            m.set(-14, y0 + 1, z, Theme.b("minecraft:black_wool"));
            m.set(14, y0 + 1, z, Theme.b("minecraft:black_wool"));
        }
        m.populate(atrium, y0, 8, 5);
        // 아트리움 천장 조명 (2층 위)
        for (int x = -12; x <= 12; x += 6) for (int z = -9; z <= 9; z += 6) m.set(x, y1 + MapBuilder.H, z, t.light);
        // 정면 유리 커튼월 (남쪽)
        for (int x = -12; x <= 12; x++) for (int yy = y0 + 2; yy < y1 + MapBuilder.H; yy++) {
            if (yy == y1) continue;
            m.set(x, yy, 28, Theme.b("minecraft:gray_stained_glass_pane[east=true,west=true]"));
        }
        // 둘레 구역: 아트리움 벽
        for (int[] yy : new int[][]{{y0}, {y1}}) {
            int y = yy[0];
            m.wallX(-33, 33, -13, y, t.wallAccent);
            m.wallZ(-17, -12, 27, y, t.wallAccent);
            m.wallZ(17, -12, 27, y, t.wallAccent);
            if (y == y0) {
                m.clearBox(-15, y + 1, -13, 15, y + 4, -13); // 로비→북쪽 복도 크게 개방
                m.wallX(-15, 15, -13, y, t.glass);
                m.doorway(-2, y, -13, true, 5);
            } else {
                m.doorway(-2, y, -13, true, 5);
            }
            m.door(-17, y, 0, false);
            m.door(17, y, 0, false);
            m.door(-17, y, 20, false);
            m.door(17, y, 20, false);
            // 북쪽 사무실 줄
            List<MapBuilder.Room> north = m.subdivide(new Rect(-33, -27, 33, -17), y, 5, 10, t.wall, 0.6, 0.35);
            m.wallX(-33, 33, -16, y, t.wall);
            Rect nc = new Rect(-33, -15, 33, -14);
            m.floor(nc, y, t.floorAlt);
            for (int x = -30; x <= 30; x += 8) m.connect(x, y, -16, true, 0.7);
            for (MapBuilder.Room r : north) {
                m.lights(r.rect(), y, 5);
                Furnish.office(m, r.rect(), y);
            }
            m.lights(nc, y, 6);
            // 서/동 사무실 줄
            for (int side : new int[]{-1, 1}) {
                Rect strip = side < 0 ? new Rect(-33, -12, -18, 27) : new Rect(18, -12, 33, 27);
                List<MapBuilder.Room> rooms = m.subdivide(strip, y, 5, 9, t.wall, 0.6, 0.3);
                for (MapBuilder.Room r : rooms) {
                    m.lights(r.rect(), y, 5);
                    Furnish.auto(m, r, false);
                }
            }
            m.exteriorWindows(outer, y, 4, 2);
        }
        // 2층 메자닌 바닥 (아트리움 남쪽 띠)
        Rect mezz = new Rect(-16, 12, 16, 27);
        m.floor(mezz, y0, t.floor);
        m.populate(mezz, y0, 3, 2);
        m.populate(mezz, y1, 3, 2);
        m.lights(mezz, y0, 6);
        m.lights(mezz, y1, 6);
        // 그랜드 계단: 로비 → 2층 메자닌 (아트리움 양쪽)
        var slab = Theme.b("minecraft:quartz_slab");
        m.stairs(-14, y0, 22, 1, 0, 3, Theme.b("minecraft:smooth_quartz"), slab);
        m.stairs(14, y0, 15, -1, 0, 3, Theme.b("minecraft:smooth_quartz"), slab);
        m.floor(outer, y1 + MapBuilder.H, Theme.b("minecraft:black_concrete"));
        return m.finish(id(), displayName());
    }
}
