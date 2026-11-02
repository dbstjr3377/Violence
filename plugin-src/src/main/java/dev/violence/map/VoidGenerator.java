package dev.violence.map;

import java.util.List;
import java.util.Random;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.generator.BlockPopulator;
import org.bukkit.generator.ChunkGenerator;

/** 아무것도 없는 공허 월드 (맵을 붙여 넣는 용도). */
public final class VoidGenerator extends ChunkGenerator {
    @Override public boolean shouldGenerateNoise() { return false; }
    @Override public boolean shouldGenerateSurface() { return false; }
    @Override public boolean shouldGenerateCaves() { return false; }
    @Override public boolean shouldGenerateDecorations() { return false; }
    @Override public boolean shouldGenerateMobs() { return false; }
    @Override public boolean shouldGenerateStructures() { return false; }
    @Override public List<BlockPopulator> getDefaultPopulators(World world) { return List.of(); }
    @Override public Location getFixedSpawnLocation(World world, Random random) { return new Location(world, 0, 80, 0); }
    @Override public boolean canSpawn(World world, int x, int z) { return true; }
}
