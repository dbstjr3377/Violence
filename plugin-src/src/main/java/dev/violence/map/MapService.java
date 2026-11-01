package dev.violence.map;

import dev.violence.ViolencePlugin;
import dev.violence.arena.GameMap;
import dev.violence.logic.NavGrid;
import dev.violence.mapgen.Generators;
import dev.violence.mapgen.MapGenerator;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;
import java.util.TreeSet;
import java.util.function.Consumer;
import java.util.logging.Level;
import java.util.stream.Stream;
import org.bukkit.Bukkit;
import org.bukkit.GameRules;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.WorldCreator;
import org.bukkit.block.Block;
import org.bukkit.block.data.BlockData;
import org.bukkit.util.BoundingBox;

/**
 * 맵 저장/불러오기와 게임용 월드 생성.
 * plugins/ViolenceCore/maps/<id>/map.yml + blocks.vmap
 * 내장 생성기 맵(아파트, 빌딩, 감옥 등)은 처음 쓸 때 자동으로 생성되어 저장된다.
 */
public final class MapService {
    private final ViolencePlugin plugin;
    private final File mapsDir;
    private int worldCounter;

    public MapService(ViolencePlugin plugin) {
        this.plugin = plugin;
        this.mapsDir = new File(plugin.getDataFolder(), "maps");
        mapsDir.mkdirs();
    }

    public File mapDir(String id) { return new File(mapsDir, id); }

    public boolean hasSaved(String id) {
        return new File(mapDir(id), "map.yml").isFile() && new File(mapDir(id), "blocks.vmap").isFile();
    }

    /** 사용 가능한 맵 id 목록 (저장된 맵 + 내장 생성기) */
    public List<String> mapIds() {
        TreeSet<String> ids = new TreeSet<>();
        File[] dirs = mapsDir.listFiles(File::isDirectory);
        if (dirs != null) for (File d : dirs) if (new File(d, "map.yml").isFile()) ids.add(d.getName());
        for (MapGenerator g : Generators.all()) ids.add(g.id());
        return new ArrayList<>(ids);
    }

    public String displayName(String id) {
        if (hasSaved(id)) return GameMap.load(new File(mapDir(id), "map.yml")).displayName;
        MapGenerator g = Generators.get(id);
        return g != null ? g.displayName() : id;
    }

    public World createWorld(String prefix) {
        String name = prefix + "_" + (System.currentTimeMillis() % 100000) + "_" + (worldCounter++);
        WorldCreator wc = new WorldCreator(name).generator(new VoidGenerator()).generateStructures(false);
        World w = wc.createWorld();
        if (w == null) throw new IllegalStateException("월드 생성 실패: " + name);
        w.setAutoSave(false);
        w.setGameRule(GameRules.ADVANCE_TIME, false);
        w.setGameRule(GameRules.ADVANCE_WEATHER, false);
        w.setGameRule(GameRules.SPAWN_MOBS, false);
        w.setGameRule(GameRules.SPAWN_MONSTERS, false);
        w.setGameRule(GameRules.FALL_DAMAGE, false);
        w.setGameRule(GameRules.NATURAL_HEALTH_REGENERATION, false);
        w.setGameRule(GameRules.IMMEDIATE_RESPAWN, true);
        w.setGameRule(GameRules.SHOW_DEATH_MESSAGES, false);
        w.setGameRule(GameRules.SHOW_ADVANCEMENT_MESSAGES, false);
        w.setGameRule(GameRules.KEEP_INVENTORY, true);
        w.setGameRule(GameRules.LOCATOR_BAR, false);
        w.setGameRule(GameRules.MOB_GRIEFING, false);
        w.setGameRule(GameRules.BLOCK_DROPS, false);
        w.setGameRule(GameRules.RANDOM_TICK_SPEED, 0);
        w.setTime(18000);
        w.setStorm(false);
        return w;
    }

    /**
     * 게임용 월드를 만들고 맵을 준비한다. 블록은 여러 틱에 나눠 붙여 넣는다.
     * @param done 완료 시 (월드, 맵 데이터) 콜백, 실패 시 null 월드
     */
    public void prepare(String id, Consumer<World> worldReady, java.util.function.BiConsumer<World, GameMap> done) {
        World w = createWorld("vgame");
        worldReady.accept(w);
        if (!hasSaved(id)) {
            MapGenerator g = Generators.get(id);
            if (g == null) {
                plugin.getLogger().warning("맵을 찾을 수 없습니다: " + id);
                done.accept(null, null);
                return;
            }
            plugin.getLogger().info("내장 맵 생성 중: " + id);
            GameMap m = g.generate(w, new Random(id.hashCode() * 31L + 7));
            try {
                saveMap(w, m);
            } catch (IOException e) {
                plugin.getLogger().log(Level.WARNING, "맵 저장 실패", e);
            }
            done.accept(w, m);
            return;
        }
        GameMap m = GameMap.load(new File(mapDir(id), "map.yml"));
        BlockStore store;
        try {
            store = BlockStore.load(new File(mapDir(id), "blocks.vmap"));
        } catch (IOException e) {
            plugin.getLogger().log(Level.WARNING, "맵 블록 불러오기 실패: " + id, e);
            done.accept(null, null);
            return;
        }
        paste(w, store, () -> done.accept(w, m));
    }

    /** 블록 저장본을 월드에 나눠서 붙여 넣기 (틱당 일정량) */
    public void paste(World w, BlockStore s, Runnable after) {
        BlockData[] pal = s.resolvePalette();
        int perTick = plugin.getConfig().getInt("map.paste-blocks-per-tick", 60000);
        int[] cursor = {0};
        int total = s.volume();
        plugin.repeat(1, task -> {
            int end = Math.min(total, cursor[0] + perTick);
            for (int i = cursor[0]; i < end; i++) {
                int v = s.data[i];
                if (v == 0) continue;
                int x = i % s.sx;
                int z = (i / s.sx) % s.sz;
                int y = i / (s.sx * s.sz);
                w.getBlockAt(s.ox + x, s.oy + y, s.oz + z).setBlockData(pal[v], false);
            }
            cursor[0] = end;
            if (end >= total) {
                task.cancel();
                after.run();
            }
        });
    }

    public void saveMap(World w, GameMap m) throws IOException {
        File dir = mapDir(m.id);
        dir.mkdirs();
        BlockStore store = BlockStore.capture(w, m.minX, m.minY, m.minZ, m.maxX, m.maxY, m.maxZ);
        store.save(new File(dir, "blocks.vmap"));
        m.save(new File(dir, "map.yml"));
    }

    /** 게임 월드 제거 (플레이어는 미리 내보내야 함) */
    public void destroy(World w) {
        if (w == null) return;
        Path folder = w.getWorldPath();
        Bukkit.unloadWorld(w, false);
        Bukkit.getScheduler().runTaskLaterAsynchronously(plugin, () -> deleteRecursive(folder), 40L);
    }

    private void deleteRecursive(Path p) {
        if (p == null || !Files.exists(p)) return;
        try (Stream<Path> walk = Files.walk(p)) {
            walk.sorted(Comparator.reverseOrder()).forEach(f -> {
                try {
                    Files.deleteIfExists(f);
                } catch (IOException ignored) {
                    // 잠긴 파일은 다음 기회에
                }
            });
        } catch (IOException e) {
            plugin.getLogger().fine("월드 폴더 삭제 실패: " + p);
        }
    }

    /** 서버 시작 시 지난 게임 월드 잔여물 정리 */
    public void cleanupLeftovers() {
        File container = Bukkit.getWorldContainer();
        File[] files = container.listFiles((d, n) -> n.startsWith("vgame_") || n.startsWith("vedit_"));
        if (files != null) for (File f : files) deleteRecursive(f.toPath());
    }

    /** NPC 보행 그리드 생성 (월드 블록 충돌 형태 기반) */
    public NavGrid buildNav(World w, GameMap m) {
        NavGrid.BlockQuery q = new NavGrid.BlockQuery() {
            @Override
            public double topHeight(int x, int y, int z) {
                Block b = w.getBlockAt(x, y, z);
                Material t = b.getType();
                if (t.isAir() || b.isPassable()) return Double.NaN;
                double top = 0;
                for (BoundingBox bb : b.getCollisionShape().getBoundingBoxes()) top = Math.max(top, bb.getMaxY());
                if (top <= 0 || top > 1.0001) return Double.NaN;
                return top;
            }

            @Override
            public boolean passable(int x, int y, int z) {
                Block b = w.getBlockAt(x, y, z);
                return b.isPassable() && b.getType() != Material.BARRIER;
            }
        };
        return NavGrid.build(q, m.minX, m.minY, m.minZ, m.maxX, m.maxY, m.maxZ);
    }
}
