package dev.violence;

import dev.violence.arena.Arena;
import dev.violence.arena.CorpseService;
import dev.violence.arena.DoorService;
import dev.violence.arena.GlassService;
import dev.violence.arena.GroundWeaponService;
import dev.violence.arena.SpawnService;
import dev.violence.combat.CombatService;
import dev.violence.command.FallbackCommands;
import dev.violence.command.ViolenceCommand;
import dev.violence.fx.CameraService;
import dev.violence.fx.Fx;
import dev.violence.fx.Hud;
import dev.violence.fx.Shake;
import dev.violence.game.GameService;
import dev.violence.game.LobbyService;
import dev.violence.map.MapService;
import dev.violence.mask.MaskService;
import dev.violence.npc.NpcManager;
import dev.violence.pack.PackServer;
import dev.violence.player.PlayerListener;
import dev.violence.weapon.WeaponRegistry;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Random;
import java.util.function.Consumer;
import java.util.logging.Level;
import org.bukkit.command.PluginCommand;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

/**
 * VIOLENCE - 속도감 있는 1/3인칭 데스매치 슈터.
 * 실시간 전투 엔진(히트스캔, 근접, 투척, 처형, 문/유리 물리, NPC AI, 연출)은 이 플러그인이,
 * 게임 규칙(명령어, 점수표, 콤보 공식, 알림)은 Skript 스크립트가 담당한다.
 */
public final class ViolencePlugin extends JavaPlugin {
    private static ViolencePlugin instance;

    private final Random random = new Random();
    private long tick;
    private Arena arena;

    private WeaponRegistry weapons;
    private Fx fx;
    private Shake shake;
    private CameraService camera;
    private dev.violence.fx.PoseSync poses;
    private Hud hud;
    private CombatService combat;
    private GlassService glass;
    private DoorService doors;
    private GroundWeaponService ground;
    private SpawnService spawns;
    private CorpseService corpses;
    private NpcManager npcs;
    private MaskService masks;
    private GameService game;
    private LobbyService lobby;
    private MapService maps;
    private PackServer pack;
    private ViolenceCommand command;

    public static ViolencePlugin get() { return instance; }

    @Override
    public void onEnable() {
        instance = this;
        saveDefaultConfig();
        saveResourceIfMissing("weapons.yml");
        try {
            loadWeapons();
        } catch (Exception e) {
            getLogger().log(Level.SEVERE, "weapons.yml 로딩 실패 - 플러그인을 비활성화합니다", e);
            getServer().getPluginManager().disablePlugin(this);
            return;
        }
        fx = new Fx(this);
        shake = new Shake();
        camera = new CameraService(this);
        poses = new dev.violence.fx.PoseSync(this);
        hud = new Hud(this);
        combat = new CombatService(this);
        glass = new GlassService(this);
        doors = new DoorService(this);
        ground = new GroundWeaponService(this);
        spawns = new SpawnService(this);
        corpses = new CorpseService(this);
        npcs = new NpcManager(this);
        masks = new MaskService(this);
        lobby = new LobbyService(this);
        maps = new MapService(this);
        game = new GameService(this);
        pack = new PackServer(this);
        maps.cleanupLeftovers();
        try {
            lobby.setupWorld();
        } catch (RuntimeException e) {
            getLogger().warning("로비 월드 설정 실패: " + e);
        }
        pack.start();

        getServer().getPluginManager().registerEvents(new PlayerListener(this), this);
        command = new ViolenceCommand(this);
        PluginCommand pc = getCommand("violence");
        if (pc != null) {
            pc.setExecutor(command);
            pc.setTabCompleter(command);
        }
        // 메인 틱 루프
        getServer().getScheduler().runTaskTimer(this, this::onTick, 1L, 1L);
        // Skript 가 스크립트를 다 읽은 뒤 확인
        later(100, () -> FallbackCommands.registerIfNeeded(this));
        getLogger().info("VIOLENCE 활성화 - 무기 " + weapons.all().size() + "종, 맵 " + maps.mapIds().size() + "개");
    }

    @Override
    public void onDisable() {
        // 단계마다 따로 보호: 하나가 실패해도 나머지(포트 해제 등)는 반드시 실행
        try {
            if (game != null) game.shutdown();
        } catch (RuntimeException e) {
            getLogger().log(Level.WARNING, "게임 정리 실패", e);
        }
        try {
            if (command != null) command.editor().close();
        } catch (RuntimeException e) {
            getLogger().log(Level.WARNING, "맵 편집기 정리 실패", e);
        }
        try {
            if (pack != null) pack.stop();
        } catch (RuntimeException e) {
            getLogger().log(Level.WARNING, "리소스팩 서버 정지 실패", e);
        }
        instance = null;
    }

    private void saveResourceIfMissing(String name) {
        if (!new File(getDataFolder(), name).exists()) saveResource(name, false);
    }

    private void loadWeapons() throws IOException {
        File f = new File(getDataFolder(), "weapons.yml");
        try (InputStreamReader r = new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8)) {
            weapons = WeaponRegistry.load(r);
        }
    }

    private void onTick() {
        tick++;
        try {
            game.tick(tick);
        } catch (RuntimeException e) {
            getLogger().log(Level.SEVERE, "게임 틱 처리 중 오류", e);
        }
    }

    // ───────── 스케줄 도우미 ─────────

    public long now() { return tick; }

    public Random random() { return random; }

    public BukkitTask later(int ticks, Runnable r) {
        return getServer().getScheduler().runTaskLater(this, () -> {
            try {
                r.run();
            } catch (RuntimeException e) {
                getLogger().log(Level.WARNING, "예약 작업 오류", e);
            }
        }, Math.max(1, ticks));
    }

    /** 지정한 판(arena)이 아직 진행 중일 때만 실행되는 지연 작업 */
    public BukkitTask laterIn(Arena a, int ticks, Runnable r) {
        return later(ticks, () -> {
            if (a != null && arena == a) r.run();
        });
    }

    public void repeat(int period, Consumer<BukkitTask> body) {
        getServer().getScheduler().runTaskTimer(this, body, 1L, Math.max(1, period));
    }

    // ───────── 서비스 접근 ─────────

    public Arena arena() { return arena; }
    public void setArena(Arena a) { this.arena = a; }
    public WeaponRegistry weapons() { return weapons; }
    public Fx fx() { return fx; }
    public Shake shake() { return shake; }
    public CameraService camera() { return camera; }
    public dev.violence.fx.PoseSync poses() { return poses; }
    public Hud hud() { return hud; }
    public CombatService combat() { return combat; }
    public GlassService glass() { return glass; }
    public DoorService doors() { return doors; }
    public GroundWeaponService ground() { return ground; }
    public SpawnService spawns() { return spawns; }
    public CorpseService corpses() { return corpses; }
    public NpcManager npcs() { return npcs; }
    public MaskService masks() { return masks; }
    public GameService game() { return game; }
    public LobbyService lobby() { return lobby; }
    public MapService maps() { return maps; }
    public PackServer pack() { return pack; }
}
