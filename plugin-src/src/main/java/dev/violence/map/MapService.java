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
    /** 이 값이 바뀌면 진행 중인 붙여넣기 작업이 스스로 멈춘다 */
    private int pasteEpoch;

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
        // 예전 버전에서 낮은 높이로 저장된 맵(클럽, 아파트, 교도소)은 쉐이더 구역 밖이라 새로 생성
        int baseY = dev.violence.fx.ShaderZones.baseY(id);
        boolean stale = false;
        try {
            stale = baseY != dev.violence.fx.ShaderZones.DEFAULT_Y0 && hasSaved(id) && Generators.get(id) != null
                    && GameMap.load(new File(mapDir(id), "map.yml")).minY < baseY - 8;
        } catch (RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "map.yml 확인 실패: " + id, e);
        }
        // 내장 맵 생성기가 바뀌면(블록 팔레트 등) 예전에 저장된 맵도 새로 생성
        if (!stale && hasSaved(id) && Generators.get(id) != null && savedGenVersion(id) < Generators.VERSION) {
            stale = true;
            plugin.getLogger().info(id + " 맵 생성기가 바뀌어(v" + Generators.VERSION + ") 다시 생성합니다");
        }
        if (stale) {
            plugin.getLogger().info(id + " 맵을 쉐이더 구역 높이(y=" + baseY + ")로 다시 생성합니다");
            backup(id);   // 직접 편집한 내용이 있을 수 있으니 지우지 않고 보관
        }
        if (!hasSaved(id) || stale) {
            MapGenerator g = Generators.get(id);
            if (g == null) {
                plugin.getLogger().warning("맵을 찾을 수 없거나 블록 파일(blocks.vmap)이 없습니다: " + id);
                done.accept(w, null);
                return;
            }
            plugin.getLogger().info("내장 맵 생성 중: " + id);
            GameMap m;
            try {
                m = g.generate(new WorldBlockAccess(w), new Random(id.hashCode() * 31L + 7));
            } catch (RuntimeException e) {
                plugin.getLogger().log(Level.SEVERE, "맵 생성 실패: " + id, e);
                done.accept(w, null);
                return;
            }
            try {
                saveMap(w, m);
                Files.writeString(new File(mapDir(id), "generator.version").toPath(), String.valueOf(Generators.VERSION));
            } catch (IOException e) {
                plugin.getLogger().log(Level.WARNING, "맵 저장 실패", e);
            }
            done.accept(w, m);
            return;
        }
        GameMap m;
        BlockStore store;
        try {
            m = GameMap.load(new File(mapDir(id), "map.yml"));
            store = BlockStore.load(new File(mapDir(id), "blocks.vmap"));
        } catch (IOException | RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "맵 불러오기 실패 (파일이 깨졌을 수 있음): " + id, e);
            done.accept(w, null);
            return;
        }
        paste(w, store, () -> done.accept(w, m), () -> done.accept(w, null));
    }

    /** 저장된 내장 맵을 만든 생성기 버전 (파일이 없으면 0 = 예전 버전) */
    private int savedGenVersion(String id) {
        try {
            return Integer.parseInt(Files.readString(new File(mapDir(id), "generator.version").toPath()).trim());
        } catch (IOException | NumberFormatException e) {
            return 0;
        }
    }

    /** 맵 폴더를 maps/<id>.bak-<시각> 으로 복사해 둔다 */
    private void backup(String id) {
        File src = mapDir(id);
        File dst = new File(mapsDir, id + ".bak-" + System.currentTimeMillis());
        try {
            dst.mkdirs();
            File[] files = src.listFiles(File::isFile);
            if (files != null) for (File f : files) Files.copy(f.toPath(), new File(dst, f.getName()).toPath());
            plugin.getLogger().info("기존 맵 보관: " + dst.getName());
        } catch (IOException e) {
            plugin.getLogger().log(Level.WARNING, "맵 보관 실패: " + id, e);
        }
    }

    /** 블록 저장본을 월드에 나눠서 붙여 넣기 (틱당 일정량) */
    public void paste(World w, BlockStore s, Runnable after) {
        paste(w, s, after, () -> { });
    }

    /** 블록 저장본을 월드에 나눠서 붙여 넣기. 오류가 나면 멈추고 failed 를 한 번 부른다 */
    public void paste(World w, BlockStore s, Runnable after, Runnable failed) {
        BlockData[] pal;
        try {
            pal = s.resolvePalette();
        } catch (RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "블록 목록 해석 실패", e);
            failed.run();
            return;
        }
        int perTick = Math.max(1000, plugin.getConfig().getInt("map.paste-blocks-per-tick", 60000));
        int[] cursor = {0};
        int total = s.volume();
        int epoch = pasteEpoch;
        java.util.UUID worldId = w.getUID();
        cancelledPastes.remove(worldId);
        plugin.repeat(1, task -> {
            if (epoch != pasteEpoch || cancelledPastes.contains(worldId) || Bukkit.getWorld(worldId) == null) {
                task.cancel();
                return;
            }
            try {
                int end = Math.min(total, cursor[0] + perTick);
                for (int i = cursor[0]; i < end; i++) {
                    int v = s.data[i];
                    if (v <= 0 || v >= pal.length || pal[v] == null) continue;   // 알 수 없는 블록은 공기로
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
            } catch (RuntimeException e) {
                plugin.getLogger().log(Level.SEVERE, "맵 붙여넣기 실패 - 중단합니다", e);
                task.cancel();
                failed.run();
            }
        });
    }

    /** 이 월드의 붙여넣기만 중단 (맵 편집기 붙여넣기는 그대로) */
    public void cancelPaste(World w) {
        if (w != null) cancelledPastes.add(w.getUID());
    }

    private final java.util.Set<java.util.UUID> cancelledPastes = new java.util.HashSet<>();

    /** 진행 중인 모든 붙여넣기 중단 */
    public void cancelPastes() {
        pasteEpoch++;
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
        if (!Bukkit.unloadWorld(w, false)) {
            plugin.getLogger().warning("월드 언로드 실패 (안에 플레이어가 남아 있음?): " + w.getName() + " - 다음 서버 시작 때 정리합니다");
            return;
        }
        if (plugin.isEnabled()) {
            Bukkit.getScheduler().runTaskLaterAsynchronously(plugin, () -> deleteRecursive(folder), 40L);
        } else {
            // 플러그인 비활성화 중에는 스케줄러를 쓸 수 없으므로 바로 삭제
            deleteRecursive(folder);
        }
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
        // 26.x 에서는 추가 월드가 <월드>/dimensions/<네임스페이스>/<이름> 에 저장된다.
        // 서버 폴더 아래 4단계까지 vgame_/vedit_ 폴더를 찾아 지운다 (현재 로드된 월드 제외)
        java.util.Set<String> loaded = new java.util.HashSet<>();
        for (World w : Bukkit.getWorlds()) loaded.add(w.getName());
        try (Stream<Path> walk = Files.walk(Bukkit.getWorldContainer().toPath(), 4)) {
            List<Path> found = walk.filter(Files::isDirectory).filter(p -> {
                String n = p.getFileName().toString();
                return (n.startsWith("vgame_") || n.startsWith("vedit_")) && !loaded.contains(n);
            }).toList();
            for (Path p : found) {
                deleteRecursive(p);
                plugin.getLogger().info("지난 게임 월드 정리: " + p);
            }
        } catch (IOException | RuntimeException e) {
            // 읽을 수 없는 폴더가 있어도 플러그인 시작은 계속
            plugin.getLogger().warning("잔여 월드 검색 실패: " + e);
        }
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
