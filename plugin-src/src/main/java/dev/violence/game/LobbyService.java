package dev.violence.game;

import dev.violence.ViolencePlugin;
import java.util.ArrayList;
import java.util.List;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.entity.Player;
import org.bukkit.entity.Pose;

/** 로비 (기본 월드). 게임 밖 플레이어를 관리한다. */
public final class LobbyService {
    private final ViolencePlugin plugin;

    public LobbyService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public World world() { return Bukkit.getWorlds().getFirst(); }

    /** 로비 월드: 밤낮/날씨/몹 고정 */
    public void setupWorld() {
        World w = world();
        w.setGameRule(org.bukkit.GameRules.ADVANCE_TIME, false);
        w.setGameRule(org.bukkit.GameRules.ADVANCE_WEATHER, false);
        w.setGameRule(org.bukkit.GameRules.SPAWN_MOBS, false);
        w.setGameRule(org.bukkit.GameRules.SPAWN_MONSTERS, false);
        w.setGameRule(org.bukkit.GameRules.SHOW_ADVANCEMENT_MESSAGES, false);
        w.setGameRule(org.bukkit.GameRules.FALL_DAMAGE, false);
        w.setGameRule(org.bukkit.GameRules.LOCATOR_BAR, false);
        w.setTime(18000);
        w.setStorm(false);
    }

    public boolean isLobby(World w) { return w.equals(world()); }

    public Location spawn() {
        World w = world();
        Location s = w.getSpawnLocation();
        return s.clone().add(0.5, 0, 0.5);
    }

    /** 게임에 참가할 플레이어 (관전 모드/제외 권한 제외) */
    public List<Player> participants() {
        List<Player> out = new ArrayList<>();
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (p.getGameMode() == GameMode.SPECTATOR) continue;
            if (p.hasPermission("violence.exempt") && !p.isOp()) continue;
            out.add(p);
        }
        return out;
    }

    public void onJoin(Player p) {
        if (plugin.arena() != null && plugin.arena().players.containsKey(p.getUniqueId())) return;
        resetPlayer(p);
        sendToLobby(p);
    }

    public void sendToLobby(Player p) {
        p.teleport(spawn());
        p.setGameMode(GameMode.ADVENTURE);
    }

    /** 이전 게임에서 남은 속성/자세 초기화 */
    public static void resetPlayer(Player p) {
        set(p, Attribute.JUMP_STRENGTH, 0.42);
        set(p, Attribute.BLOCK_INTERACTION_RANGE, 4.5);
        set(p, Attribute.ENTITY_INTERACTION_RANGE, 3.0);
        set(p, Attribute.BLOCK_BREAK_SPEED, 1.0);
        dev.violence.player.PlayerSpeed.set(p, 0.1);
        set(p, Attribute.ATTACK_SPEED, 4.0);
        set(p, Attribute.FALL_DAMAGE_MULTIPLIER, 1.0);
        p.setPose(Pose.STANDING, false);
        p.setInvisible(false);
        p.getInventory().clear();
        p.setFoodLevel(20);
        p.setHealth(p.getAttribute(Attribute.MAX_HEALTH).getValue());
    }

    private static void set(Player p, Attribute a, double v) {
        AttributeInstance i = p.getAttribute(a);
        if (i != null) i.setBaseValue(v);
    }
}
