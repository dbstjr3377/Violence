package dev.violence.game;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.arena.GameMap;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.fx.Glyphs;
import dev.violence.logic.KillStreak;
import dev.violence.logic.KillType;
import dev.violence.logic.NavGrid;
import dev.violence.math.Vec3;
import dev.violence.npc.NpcCombatant;
import dev.violence.player.PlayerCombatant;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponType;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.title.Title;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;

/**
 * 한 판의 진행: 준비(맵 생성/배치) → 카운트다운 → 진행 → 종료(결과) → 정리.
 * 종료 조건: 제한 시간 종료 또는 목표 킬 달성.
 */
public final class GameService {
    public enum State { IDLE, PREPARING, COUNTDOWN, RUNNING, ENDING }

    private final ViolencePlugin plugin;
    private final SkriptBridge bridge;
    private final ScoreService scores;
    private State state = State.IDLE;
    private World preparingWorld;
    private long startTick;
    private long endTick;
    private int targetKills;
    private int timeLimit;
    private String mapId;

    public GameService(ViolencePlugin plugin) {
        this.plugin = plugin;
        this.bridge = new SkriptBridge(plugin);
        this.scores = new ScoreService(plugin, bridge);
    }

    public State state() { return state; }
    public ScoreService scores() { return scores; }
    public SkriptBridge bridge() { return bridge; }
    public int targetKills() { return targetKills; }

    public long remainingTicks() {
        if (state != State.RUNNING) return (long) timeLimit * 20;
        return Math.max(0, endTick - plugin.now());
    }

    // ───────── 시작 ─────────

    /**
     * 게임 시작.
     * @param npcCount NPC 수 (-1 이면 총원 50 - 플레이어 수)
     */
    public boolean start(CommandSender sender, String map, int npcCount, int kills, int seconds) {
        if (state != State.IDLE) {
            sender.sendMessage(Component.text("이미 게임이 진행 중입니다.", NamedTextColor.RED));
            return false;
        }
        List<Player> players = new ArrayList<>(plugin.lobby().participants());
        int total = plugin.getConfig().getInt("game.total-entities", 50);
        int minPlayers = plugin.getConfig().getInt("game.min-players", 1);
        if (players.size() < minPlayers) {
            sender.sendMessage(Component.text("참가 플레이어가 부족합니다 (최소 " + minPlayers + "명).", NamedTextColor.RED));
            return false;
        }
        List<String> ids = plugin.maps().mapIds();
        if (map == null || map.isBlank() || map.equalsIgnoreCase("random") || map.equals("랜덤")) {
            map = ids.get(plugin.random().nextInt(ids.size()));
        }
        if (!ids.contains(map)) {
            sender.sendMessage(Component.text("알 수 없는 맵: " + map + "  (" + String.join(", ", ids) + ")", NamedTextColor.RED));
            return false;
        }
        int npcs = npcCount >= 0 ? npcCount : Math.max(0, total - players.size());
        this.targetKills = kills > 0 ? kills : plugin.getConfig().getInt("game.target-kills", 30);
        this.timeLimit = seconds > 0 ? seconds : plugin.getConfig().getInt("game.time-limit-seconds", 600);
        this.mapId = map;
        state = State.PREPARING;
        String display = plugin.maps().displayName(map);
        Bukkit.broadcast(Component.text("[VIOLENCE] ", NamedTextColor.LIGHT_PURPLE)
                .append(Component.text(display + " 맵을 준비합니다... (플레이어 " + players.size() + " + NPC " + npcs + ")", NamedTextColor.WHITE)));
        int finalNpcs = npcs;
        final String finalMap = map;
        try {
            plugin.maps().prepare(map, w -> preparingWorld = w, (world, gm) -> {
                if (world == null || gm == null) {
                    Bukkit.broadcast(Component.text("맵 준비에 실패했습니다.", NamedTextColor.RED));
                    if (world != null) plugin.maps().destroy(world);
                    state = State.IDLE;
                    return;
                }
                try {
                    setupArena(world, gm, players, finalNpcs, finalMap);
                } catch (RuntimeException ex) {
                    plugin.getLogger().log(java.util.logging.Level.SEVERE, "게임 시작 실패", ex);
                    Bukkit.broadcast(Component.text("게임 시작 중 오류가 발생했습니다: " + ex.getMessage(), NamedTextColor.RED));
                    forceCleanup();
                }
            });
        } catch (RuntimeException ex) {
            plugin.getLogger().log(java.util.logging.Level.SEVERE, "맵 준비 실패", ex);
            state = State.IDLE;
            if (preparingWorld != null) plugin.maps().destroy(preparingWorld);
            return false;
        }
        return true;
    }

    private void setupArena(World world, GameMap gm, List<Player> players, int npcs, String map) {
        long t0 = System.currentTimeMillis();
        NavGrid nav = plugin.maps().buildNav(world, gm);
        Arena a = new Arena(world, gm, nav);
        plugin.setArena(a);
        plugin.getLogger().info("보행 그리드: " + nav.size() + " 노드 (" + (System.currentTimeMillis() - t0) + "ms)");
        if (gm.spawns.size() < 8) {
            // 리스폰 후보가 부족하면 보행 그리드에서 보충
            List<NavGrid.Node> nodes = new ArrayList<>(nav.nodes());
            Collections.shuffle(nodes, plugin.random());
            for (int i = 0; i < Math.min(80, nodes.size()); i++) gm.spawns.add(nodes.get(i).pos());
        }
        plugin.doors().spawnDoors(a);
        // 플레이어 참가
        for (Player p : players) {
            if (!p.isOnline()) continue;
            addPlayer(a, p);
        }
        plugin.npcs().spawn(a, npcs);
        spawnWeapons(a);
        // 카운트다운
        state = State.COUNTDOWN;
        long now = plugin.now();
        for (Combatant c : a.combatants.values()) {
            c.moveLockUntil = now + 60;
            c.actionLockUntil = now + 60;
            c.applyStateVisuals();
        }
        bridge.call("gamestart", map, a.players.size(), a.npcs.size(), targetKills, timeLimit);
        for (int i = 3; i >= 1; i--) {
            int n = i;
            plugin.later((3 - i) * 20, () -> titleAll(Component.text(String.valueOf(n)).font(Glyphs.HUD_BIG).color(net.kyori.adventure.text.format.TextColor.color(Glyphs.PINK)), Component.empty(), 0, 18, 2));
        }
        plugin.later(60, () -> {
            if (plugin.arena() != a) return;
            state = State.RUNNING;
            startTick = plugin.now();
            endTick = startTick + timeLimit * 20L;
            titleAll(Component.text("KILL").font(Glyphs.HUD_BIG).color(net.kyori.adventure.text.format.TextColor.color(Glyphs.RED)),
                    Component.text(plugin.maps().displayName(map)).font(Glyphs.PROMPT), 0, 20, 10);
            for (Combatant c : a.combatants.values()) c.applyStateVisuals();
        });
    }

    private void addPlayer(Arena a, Player p) {
        PlayerCombatant pc = new PlayerCombatant(p);
        Vec3 spot = plugin.spawns().choose(a, pc);
        Location l = new Location(a.world, spot.x(), spot.y(), spot.z(), plugin.random().nextFloat() * 360, 0);
        p.teleport(l);
        a.add(pc);
        pc.applyRules();
    }

    private void spawnWeapons(Arena a) {
        int entities = a.combatants.size();
        double ratio = plugin.getConfig().getDouble("game.weapon-ratio", 0.5);
        int count = (int) Math.round(entities * ratio);
        List<GameMap.WeaponSpot> spots = new ArrayList<>(a.map.weaponSpots);
        Collections.shuffle(spots, plugin.random());
        int placed = 0;
        for (GameMap.WeaponSpot s : spots) {
            if (placed >= count) break;
            WeaponType t = s.fixedWeapon() != null ? plugin.weapons().get(s.fixedWeapon()) : null;
            if (t == null) t = plugin.weapons().randomSpawnable(plugin.random());
            plugin.ground().spawn(a, new WeaponInstance(t), s.pos(), s.yaw());
            placed++;
        }
        // 지점이 부족하면 보행 그리드 위 무작위
        for (int i = placed; i < count && a.nav.size() > 0; i++) {
            Vec3 p = a.nav.nodes().get(plugin.random().nextInt(a.nav.size())).pos();
            plugin.ground().spawn(a, new WeaponInstance(plugin.weapons().randomSpawnable(plugin.random())), p, plugin.random().nextFloat() * 360);
        }
        plugin.getLogger().info("무기 배치: " + count + "개 (개체 " + entities + ")");
    }

    private void titleAll(Component title, Component sub, int in, int stay, int out) {
        Arena a = plugin.arena();
        if (a == null) return;
        Title t = Title.title(title, sub, Title.Times.times(Duration.ofMillis(in * 50L), Duration.ofMillis(stay * 50L), Duration.ofMillis(out * 50L)));
        for (PlayerCombatant pc : a.players.values()) pc.player().showTitle(t);
    }

    // ───────── 진행 ─────────

    public void tick(long now) {
        Arena a = plugin.arena();
        if (a == null) return;
        if (state == State.RUNNING || state == State.COUNTDOWN) {
            if (state == State.RUNNING) {
                for (PlayerCombatant pc : new ArrayList<>(a.players.values())) {
                    if (!pc.player().isOnline()) continue;
                    boolean pressed = pc.input.consumePressed();
                    boolean held = pc.input.held(now);
                    if (pc.state == CombatState.ALIVE) plugin.combat().trigger(pc, now, pressed, held);
                    pc.tickCrawl();
                    if (pc.player().getFoodLevel() != 6) pc.player().setFoodLevel(6);
                    if (pc.state == CombatState.ALIVE && pc.player().getInventory().getHeldItemSlot() != 0) pc.player().getInventory().setHeldItemSlot(0);
                }
                plugin.combat().tick(now);
                plugin.npcs().tick(a, now);
                scores.tick(now);
                plugin.masks().tick(a, now);
            }
            plugin.doors().tick(a, now);
            plugin.ground().tick(a, now);
            updateHud(a, now);
            List<Player> online = new ArrayList<>();
            for (PlayerCombatant pc : a.players.values()) online.add(pc.player());
            plugin.shake().tick(online);
            if (state == State.RUNNING) checkEnd(a, now);
        }
    }

    private void checkEnd(Arena a, long now) {
        if (now >= endTick) {
            end(leader(a));
            return;
        }
        Combatant top = leader(a);
        if (top != null && top.kills >= targetKills) end(top);
    }

    private Combatant leader(Arena a) {
        return a.combatants.values().stream()
                .max(Comparator.<Combatant>comparingInt(c -> c.kills).thenComparingInt(c -> c.score))
                .orElse(null);
    }

    private void updateHud(Arena a, long now) {
        Combatant top = leader(a);
        long rem = state == State.RUNNING ? remainingTicks() / 20 : timeLimit;
        String time = String.format("%02d:%02d", rem / 60, rem % 60);
        for (PlayerCombatant pc : a.players.values()) {
            Player p = pc.player();
            plugin.hud().tick(p, now);
            // 연속 5킬: 심장 박동
            if (pc.streak.value() >= 5 && pc.isAlive() && now % 24 == 0) p.playSound(p.getLocation(), "violence:ui.heartbeat", 0.7f, 1f);
            if (now % 2 == 0) plugin.hud().combo(p, pc.combo.count(), pc.combo.remaining(now, scores.comboWindow(pc)));
            if (now % 5 != 0) continue;
            Component status = Component.empty()
                    .append(Glyphs.text(time, Glyphs.HUD, rem <= 30 ? Glyphs.RED : Glyphs.WHITE))
                    .append(Glyphs.text("   목표 " + targetKills + "킬   ", Glyphs.HUD, Glyphs.GRAY))
                    .append(Glyphs.text("1위 " + (top == null ? "-" : top.name() + " " + top.kills), Glyphs.HUD, Glyphs.YELLOW))
                    .append(Glyphs.text("   " + Glyphs.SKULL + " " + pc.kills + "   " + Glyphs.STAR + " " + String.format("%,d", pc.score), Glyphs.HUD, Glyphs.CYAN));
            plugin.hud().status(p, status);
            plugin.hud().action(p, actionBar(pc, now), now);
        }
    }

    private Component actionBar(PlayerCombatant pc, long now) {
        switch (pc.state) {
            case DEAD -> {
                return Glyphs.text("사망", Glyphs.HUD, Glyphs.RED);
            }
            case DOWNED -> {
                long left = Math.max(0, pc.downedUntil - now);
                return Glyphs.text("쓰러짐 " + String.format("%.1f", left / 20.0) + "초", Glyphs.HUD, Glyphs.YELLOW);
            }
            case BEING_EXECUTED -> {
                return Glyphs.text("처형당하는 중", Glyphs.HUD, Glyphs.RED);
            }
            case EXECUTING -> {
                var e = pc.execution;
                if (e != null && e.style == dev.violence.weapon.ExecutionStyle.HITS) {
                    return Glyphs.text("왼클릭: 공격 (" + e.hitsLeft + ")   우클릭: 내리기", Glyphs.HUD, Glyphs.WHITE);
                }
                return Glyphs.text("처형 중", Glyphs.HUD, Glyphs.PINK);
            }
            default -> {
            }
        }
        WeaponType t = pc.weaponType(plugin.weapons().fist());
        Component c = Component.empty();
        if (pc.mask != null) c = c.append(Glyphs.text("[" + pc.mask.displayName() + "] ", Glyphs.HUD, Glyphs.PINK));
        c = c.append(Glyphs.text(t.displayName(), Glyphs.HUD, Glyphs.WHITE));
        if (t.isGun() && pc.weapon != null) {
            int ammo = pc.weapon.ammo() + (pc.offhand != null ? pc.offhand.ammo() : 0);
            int col = ammo == 0 ? Glyphs.RED : (ammo <= t.ammo() / 4 ? Glyphs.YELLOW : Glyphs.WHITE);
            c = c.append(Glyphs.text("  " + Glyphs.BULLET + " " + ammo, Glyphs.HUD, col));
            if (pc.weapon.isReloading(now)) c = c.append(Glyphs.text("  재장전", Glyphs.HUD, Glyphs.YELLOW));
        }
        if (pc.weapon != null && pc.weapon.expireTick() > 0) {
            long left = Math.max(0, pc.weapon.expireTick() - now);
            c = c.append(Glyphs.text("  " + (left / 20 + 1) + "s", Glyphs.HUD, Glyphs.CYAN));
        }
        if (pc.bulletShield > 0) c = c.append(Glyphs.text("  ◆".repeat(pc.bulletShield), Glyphs.HUD, Glyphs.CYAN));
        return c;
    }

    // ───────── 처치 ─────────

    public void onKill(Combatant killer, Combatant victim, KillType type, boolean headshot, Vec3 at) {
        killer.kills++;
        KillStreak.Milestone ms = killer.streak.add();
        if (victim instanceof PlayerCombatant vp) {
            scores.flushCombo(vp);
            plugin.masks().clearOffer(vp);
            plugin.shake().setBaseline(vp.player(), 0);
        }
        if (killer instanceof PlayerCombatant pc) {
            scores.onPlayerKill(pc, type, headshot, at, victim.name());
            pc.refreshEquipment();
            // 연속킬 화면 효과
            int s = pc.streak.value();
            plugin.shake().setBaseline(pc.player(), s >= 5 ? 0.32 : (s >= 3 ? 0.18 : 0));
            if (ms == KillStreak.Milestone.THREE || ms == KillStreak.Milestone.FIVE) {
                plugin.masks().offer(pc);
                bridge.call("streak", pc.name(), s);
            }
        }
        if (state == State.RUNNING && killer.kills >= targetKills) end(killer);
    }

    public void onSuicide(Combatant victim) {
        if (victim instanceof PlayerCombatant vp) {
            scores.flushCombo(vp);
            plugin.shake().setBaseline(vp.player(), 0);
        }
    }

    // ───────── 종료 ─────────

    public void end(Combatant winner) {
        Arena a = plugin.arena();
        if (a == null || state == State.ENDING) return;
        state = State.ENDING;
        for (PlayerCombatant pc : a.players.values()) scores.flushCombo(pc);
        List<Combatant> ranking = new ArrayList<>(a.combatants.values());
        ranking.sort(Comparator.<Combatant>comparingInt(c -> -c.kills).thenComparingInt(c -> -c.score));
        String wname = winner == null ? "-" : winner.name();
        int wk = winner == null ? 0 : winner.kills;
        titleAll(Component.text("GAME OVER").font(Glyphs.HUD_BIG).color(net.kyori.adventure.text.format.TextColor.color(Glyphs.PINK)),
                Component.text("우승: " + wname + " (" + wk + "킬)").font(Glyphs.PROMPT), 5, 100, 20);
        if (!bridge.call("gameend", wname, wk)) {
            Bukkit.broadcast(Component.text("[VIOLENCE] 게임 종료! 우승: " + wname + " (" + wk + "킬)", NamedTextColor.LIGHT_PURPLE));
        }
        int rank = 1;
        for (Combatant c : ranking) {
            if (rank > 10) break;
            Bukkit.broadcast(Component.text(String.format(" %2d. %-16s %3d킬  %,d점", rank, c.name(), c.kills, c.score),
                    c.isPlayer() ? NamedTextColor.YELLOW : NamedTextColor.GRAY));
            rank++;
        }
        for (PlayerCombatant pc : a.players.values()) {
            if (pc.isPlayer() && !ranking.subList(0, Math.min(10, ranking.size())).contains(pc)) {
                pc.player().sendMessage(Component.text(String.format(" 내 순위: %d위  %d킬  %,d점", ranking.indexOf(pc) + 1, pc.kills, pc.score), NamedTextColor.YELLOW));
            }
        }
        // 모두 정지
        long now = plugin.now();
        for (Combatant c : a.combatants.values()) {
            c.moveLockUntil = Long.MAX_VALUE / 2;
            c.actionLockUntil = Long.MAX_VALUE / 2;
            c.applyStateVisuals();
        }
        plugin.later(plugin.getConfig().getInt("game.end-delay-seconds", 8) * 20, this::forceCleanup);
    }

    /** /게임중단: 결과 없이 즉시 종료 */
    public boolean stop(CommandSender sender) {
        if (state == State.IDLE) {
            sender.sendMessage(Component.text("진행 중인 게임이 없습니다.", NamedTextColor.RED));
            return false;
        }
        Bukkit.broadcast(Component.text("[VIOLENCE] 게임이 중단되었습니다.", NamedTextColor.RED));
        bridge.call("gamestop");
        forceCleanup();
        return true;
    }

    /** 정리: 플레이어 로비로, 엔티티/월드 제거 */
    public void forceCleanup() {
        Arena a = plugin.arena();
        plugin.camera().resetAll();
        if (a != null) {
            for (PlayerCombatant pc : new ArrayList<>(a.players.values())) {
                Player p = pc.player();
                plugin.hud().clear(p);
                plugin.shake().remove(p);
                plugin.ground().removeHighlights(a, p.getUniqueId());
                if (p.isOnline()) {
                    pc.restoreDefaults();
                    plugin.lobby().sendToLobby(p);
                }
            }
            plugin.doors().clear(a);
            for (Entity e : new ArrayList<>(a.tracked)) if (e.isValid()) e.remove();
            a.tracked.clear();
            plugin.combat().clear();
            plugin.masks().clear();
            plugin.corpses().clear();
            plugin.fx().clear();
            World w = a.world;
            plugin.setArena(null);
            // 남은 플레이어(관전자 등)도 내보낸 뒤 월드 제거
            for (Player p : w.getPlayers()) plugin.lobby().sendToLobby(p);
            plugin.maps().destroy(w);
        } else if (preparingWorld != null) {
            for (Player p : preparingWorld.getPlayers()) plugin.lobby().sendToLobby(p);
            plugin.maps().destroy(preparingWorld);
        }
        preparingWorld = null;
        state = State.IDLE;
    }

    // ───────── 입장/퇴장 ─────────

    public void onPlayerQuit(Player p) {
        Arena a = plugin.arena();
        if (a == null) return;
        PlayerCombatant pc = a.players.get(p.getUniqueId());
        if (pc == null) return;
        if (pc.execution != null) plugin.combat().cancelExecution(pc.execution);
        plugin.combat().dropWeapons(pc, pc.look());
        plugin.ground().removeHighlights(a, p.getUniqueId());
        plugin.camera().reset(p);
        a.remove(pc);
        pc.restoreDefaults();
        // 빈자리는 NPC 로 채움
        if (state == State.RUNNING) plugin.npcs().spawn(a, 1);
    }

    public void onPlayerJoinMidGame(Player p) {
        Arena a = plugin.arena();
        if (a == null || (state != State.RUNNING && state != State.COUNTDOWN)) return;
        if (!plugin.getConfig().getBoolean("game.allow-late-join", true)) return;
        // NPC 하나를 빼고 플레이어를 넣어 총원을 유지
        if (!a.npcs.isEmpty()) {
            NpcCombatant n = a.npcs.getLast();
            plugin.combat().dropWeapons(n, n.look());
            a.remove(n);
            a.tracked.remove(n.entity());
            n.entity().remove();
        }
        addPlayer(a, p);
        plugin.pack().send(p);
    }

    public void shutdown() {
        if (state != State.IDLE) forceCleanup();
    }
}
