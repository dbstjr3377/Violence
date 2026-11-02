package dev.violence.map;

import dev.violence.mapgen.BlockAccess;
import java.util.HashMap;
import java.util.Map;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.data.BlockData;

/** 실제 월드에 연결된 BlockAccess (블록 데이터는 캐시). */
public final class WorldBlockAccess implements BlockAccess {
    private final World world;
    private final Map<String, BlockData> cache = new HashMap<>();

    public WorldBlockAccess(World world) {
        this.world = world;
    }

    private BlockData data(String s) {
        return cache.computeIfAbsent(s, k -> {
            try {
                return Bukkit.createBlockData(k);
            } catch (IllegalArgumentException e) {
                return Material.STONE.createBlockData();
            }
        });
    }

    @Override
    public void set(int x, int y, int z, String state) {
        world.getBlockAt(x, y, z).setBlockData(data(state), false);
    }

    @Override
    public String get(int x, int y, int z) {
        Block b = world.getBlockAt(x, y, z);
        if (b.getType().isAir()) return null;
        return b.getBlockData().getAsString();
    }

    @Override
    public boolean isAir(int x, int y, int z) {
        return world.getBlockAt(x, y, z).getType().isAir();
    }
}
