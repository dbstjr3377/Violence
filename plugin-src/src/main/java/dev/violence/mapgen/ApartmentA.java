package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.List;
import java.util.Random;

/**
 * 아파트 A동: 3층 복도식 아파트.
 * 가운데 복도 양옆으로 세대(각 2~4개 방)가 늘어서 있고, 양 끝 계단실로 층이 이어진다.
 */
public final class ApartmentA implements MapGenerator {
    @Override public String id() { return "apartment_a"; }
    @Override public String displayName() { return "아파트 A동"; }

    @Override
    public GameMap generate(BlockAccess world, Random rnd) {
        Theme t = Theme.of("minecraft:white_concrete", "minecraft:light_gray_concrete", "minecraft:oak_planks",
                "minecraft:gray_concrete", "minecraft:smooth_stone", "minecraft:lantern[hanging=true]",
                "minecraft:glass_pane", "minecraft:spruce_slab[type=top]", "minecraft:polished_andesite",
                "minecraft:stripped_dark_oak_wood", "minecraft:gray_concrete");
        MapBuilder m = new MapBuilder(world, rnd, t);
        int floors = 3;
        int base = dev.violence.fx.ShaderZones.baseY(id());   // 쉐이더 구역 높이
        Rect outer = new Rect(-47, -17, 47, 17);
        for (int f = 0; f < floors; f++) {
            int y = base + f * MapBuilder.H;
            m.shell(outer, y, t.wall, t.floor, t.ceiling);
            // 계단실 (서/동 끝)
            Rect west = new Rect(-46, -16, -35, 16);
            Rect east = new Rect(35, -16, 46, 16);
            m.floor(west, y, t.floorAlt);
            m.floor(east, y, t.floorAlt);
            m.wallZ(-34, -16, -4, y, t.wallAccent);
            m.wallZ(-34, 4, 16, y, t.wallAccent);
            m.wallZ(34, -16, -4, y, t.wallAccent);
            m.wallZ(34, 4, 16, y, t.wallAccent);
            m.lights(west, y, 6);
            m.lights(east, y, 6);
            // 복도
            Rect corridor = new Rect(-33, -2, 33, 2);
            m.floor(corridor, y, t.floorAlt);
            m.wallX(-33, 33, -3, y, t.wallAccent);
            m.wallX(-33, 33, 3, y, t.wallAccent);
            m.lights(corridor, y, 6);
            // 세대 (북/남 각 6세대)
            int[] walls = {-22, -11, 0, 11, 22};
            for (int side = 0; side < 2; side++) {
                int z1 = side == 0 ? -16 : 4, z2 = side == 0 ? -4 : 16;
                int corridorWallZ = side == 0 ? -3 : 3;
                for (int wx : walls) m.wallZ(wx, z1, z2, y, t.wall);
                int prev = -33;
                for (int u = 0; u <= walls.length; u++) {
                    int ux1 = prev, ux2 = u < walls.length ? walls[u] - 1 : 33;
                    if (u < walls.length) prev = walls[u] + 1;
                    Rect unit = new Rect(ux1, z1, ux2, z2);
                    int dx = ux1 + 2 + rnd.nextInt(Math.max(1, unit.width() - 4));
                    m.door(dx, y, corridorWallZ, true);
                    List<MapBuilder.Room> rooms = m.subdivide(unit, y, 4, 7, t.wall, 0.55, 0.0);
                    for (MapBuilder.Room r : rooms) {
                        m.lights(r.rect(), y, 5);
                        Furnish.auto(m, r, true);
                    }
                }
            }
            m.exteriorWindows(outer, y, 5, 2);
            m.populate(corridor, y, 3, 3);
            m.populate(west, y, 3, 2);
            m.populate(east, y, 3, 2);
            Furnish.storage(m, new Rect(-46, -16, -42, -12), y);
        }
        // 층간 계단: 각 계단실에 1→2층, 2→3층
        var solid = t.floorAlt;
        var slab = "minecraft:smooth_stone_slab";
        m.stairs(-45, base, -14, 0, 1, 2, solid, slab);
        m.stairs(-45, base + MapBuilder.H, 14, 0, -1, 2, solid, slab);
        m.stairs(44, base, 14, 0, -1, 2, solid, slab);
        m.stairs(44, base + MapBuilder.H, -14, 0, 1, 2, solid, slab);
        m.floor(outer, base + floors * MapBuilder.H, "minecraft:gray_concrete");
        return m.finish(id(), displayName());
    }
}
