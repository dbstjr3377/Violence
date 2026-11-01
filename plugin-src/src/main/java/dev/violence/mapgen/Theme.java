package dev.violence.mapgen;

import org.bukkit.Bukkit;
import org.bukkit.block.data.BlockData;

/** 맵 분위기별 블록 팔레트. */
public final class Theme {
    public BlockData wall, wallAccent, floor, floorAlt, ceiling, light, glass, table, counter, trim, outside;

    public static BlockData b(String s) { return Bukkit.createBlockData(s); }

    public static Theme of(String wall, String accent, String floor, String floorAlt, String ceiling, String light,
                           String glass, String table, String counter, String trim, String outside) {
        Theme t = new Theme();
        t.wall = b(wall);
        t.wallAccent = b(accent);
        t.floor = b(floor);
        t.floorAlt = b(floorAlt);
        t.ceiling = b(ceiling);
        t.light = b(light);
        t.glass = b(glass);
        t.table = b(table);
        t.counter = b(counter);
        t.trim = b(trim);
        t.outside = b(outside);
        return t;
    }
}
