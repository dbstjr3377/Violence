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
    /** 게임을 열 때마다 증가. 지난 판의 콜백/예약 작업이 새 판을 건드리지 못하게 한다 */
    private int generation;

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
            dev.violence.chat.NoChat.tell(sender, Component.text("이미 게임이 진행 중입니다.", NamedTextColor.RED));
            return false;
        }
        if (plugin.dialog().active()) {
            dev.violence.chat.NoChat.tell(sender, Component.text("컷씬이 진행 중입니다. 컷씬이 끝난 뒤 시작하세요.", NamedTextColor.RED));
            return false;
        }
        List<Player> players = new ArrayList<>(plugin.lobby().participants());
        int total = plugin.getConfig().getInt("game.total-entities", 50);
        int minPlayers = plugin.getConfig().getInt("game.min-players", 1);
        if (players.size() < minPlayers) {
            dev.violence.chat.NoChat.tell(sender, Component.text("참가 플레이어가 부족합니다 (최소 " + minPlayers + "명).", NamedTextColor.RED));
            return false;
        }
        List<String> ids = plugin.maps().mapIds();
        if (map == null || map.isBlank() || map.equalsIgnoreCase("random") || map.equals("랜덤")) {
            map = ids.get(plugin.random().nextInt(ids.size()));
        }
        if (!ids.contains(map)) {
            dev.violence.chat.NoChat.tell(sender, Component.text("알 수 없는 맵: " + map + "  (" + String.join(", ", ids) + ")", NamedTextColor.RED));
            return false;
        }
        if (plugin.command() != null && plugin.command().editor().active()) {
            dev.violence.chat.NoChat.tell(sender, Component.text("맵 편집 중에는 게임을 시작할 수 없습니다. /vio map close 후 시작하세요.", NamedTextColor.RED));
            return false;
        }
        // NPC 수 상한: 테스트용으로 직접 지정해도 서버가 멈추지 않게
        int maxNpcs = plugin.getConfig().getInt("game.max-npcs", 120);
        int npcs = Math.max(0, Math.min(maxNpcs, npcCount >= 0 ? npcCount : total - players.size()));
        this.targetKills = kills > 0 ? Math.min(kills, 10_000) : plugin.getConfig().getInt("game.target-kills", 30);
        this.timeLimit = seconds > 0 ? Math.min(seconds, 24 * 3600) : plugin.getConfig().getInt("game.time-limit-seconds", 600);
        String display;
        try {
            display = plugin.maps().displayName(map);   // 손으로 고친 map.yml 이 깨져 있으면 여기서 실패
        } catch (RuntimeException ex) {
            plugin.getLogger().log(java.util.logging.Level.WARNING, "맵 정보를 읽지 못했습니다: " + map, ex);
            dev.violence.chat.NoChat.tell(sender, Component.text("맵 정보(map.yml)를 읽지 못했습니다: " + map, NamedTextColor.RED));
            return false;
        }
        this.mapId = map;
        state = State.PREPARING;
        dev.violence.chat.NoChat.log(Component.text("[VIOLENCE] ", NamedTextColor.LIGHT_PURPLE)
                .append(Component.text(display + " 맵을 준비합니다... (플레이어 " + players.size() + " + NPC " + npcs + ")", NamedTextColor.WHITE)));
        int finalNpcs = npcs;
        final String finalMap = map;
        final int gen = ++generation;
        try {
            plugin.maps().prepare(map, w -> preparingWorld = w, (world, gm) -> {
                if (gen != generation || state != State.PREPARING || (world != null && world != preparingWorld)) {
                    // 준비 중에 중단됨: 이 결과는 버린다
                    if (world != null && world != preparingWorld) plugin.maps().destroy(world);
                    return;
                }
                if (world == null || gm == null) {
                    dev.violence.chat.NoChat.log(Component.text("맵 준비에 실패했습니다. 서버 로그를 확인하세요.", NamedTextColor.RED));
                    World w = world != null ? world : preparingWorld;
                    if (w != null) {
                        for (Player p : w.getPlayers()) plugin.lobby().sendToLobby(p);
                        plugin.maps().destroy(w);
                    }
                    preparingWorld = null;
                    state = State.IDLE;
                    return;
                }
                try {
                    setupArena(world, gm, players, finalNpcs, finalMap);
                } catch (RuntimeException ex) {
                    plugin.getLogger().log(java.util.logging.Level.SEVERE, "게임 시작 실패", ex);
                    dev.violence.chat.NoChat.log(Component.text("게임 시작 중 오류가 발생했습니다: " + ex.getMessage(), NamedTextColor.RED));
                    forceCleanup();
                }
            });
        } catch (RuntimeException ex) {
            plugin.getLogger().log(java.util.logging.Level.SEVERE, "맵 준비 실패", ex);
            state = State.IDLE;
            if (preparingWorld != null) plugin.maps().destroy(preparingWorld);
            preparingWorld = null;
            return false;
        }
        return true;
    }

    private void setupArena(World world, GameMap gm, List<Player> players, int npcs, String map) {
        long t0 = System.currentTimeMillis();
        NavGrid nav = plugin.maps().buildNav(world, gm);
        if (gm.spawns.isEmpty() && nav.size() == 0) {
            // 리스폰도 보행 칸도 없으면 허공 리스폰 → 낙사 반복이 됨
            throw new IllegalStateException("맵에 리스폰 지점과 걸을 수 있는 칸이 없습니다: " + map);
        }
        // 걸어서 갈 수 없는 리스폰 지점(지붕, 막힌 방)은 빼기
        if (nav.size() > 0 && !gm.spawns.isEmpty()) {
            List<Vec3> reachable = new ArrayList<>();
            for (Vec3 sp : gm.spawns) if (nav.inMain(nav.nearest(sp))) reachable.add(sp);
            if (reachable.size() >= 4) {
                gm.spawns.clear();
                gm.spawns.addAll(reachable);
            }
        }
        // 맵 청크를 계속 불러 둠 (플레이어가 멀리 있어도 NPC 몸이 사라지지 않게)
        for (int cx = (gm.minX >> 4) - 1; cx <= (gm.maxX >> 4) + 1; cx++) {
            for (int cz = (gm.minZ >> 4) - 1; cz <= (gm.maxZ >> 4) + 1; cz++) world.addPluginChunkTicket(cx, cz, plugin);
        }
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
        plugin.clubBeams().start(a);   // 클럽: 쉐이더와 맞춘 공중 빛줄기
        // 플레이어 참가 (맵을 준비하는 동안 들어온 사람도 포함)
        java.util.LinkedHashSet<Player> joining = new java.util.LinkedHashSet<>(players);
        joining.addAll(plugin.lobby().participants());
        for (Player p : joining) {
            if (!p.isOnline() || a.players.containsKey(p.getUniqueId())) continue;
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
            if (plugin.arena() != a || state != State.COUNTDOWN) return;
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
        if ((state == State.RUNNING || state == State.COUNTDOWN) && a.players.isEmpty()
                && plugin.getConfig().getBoolean("game.end-when-empty", true)) {
            // 플레이어가 모두 나가면 NPC 끼리 10분을 채우지 않고 정리
            plugin.getLogger().info("플레이어가 모두 나가 게임을 정리합니다.");
            bridge.call("gamestop");
            forceCleanup();
            return;
        }
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
            plugin.falls().tick();
            plugin.blood().tick();
            // 새로 시야에 들어온 사람에게도 3인칭 손 아이템이 보이도록 주기적으로 다시 보냄
            if (now % 10 == 0) {
                for (PlayerCombatant pc : a.players.values()) syncHeld(pc);
                for (NpcCombatant n : a.npcs) syncNpcPose(n);
            }
            for (Combatant c : a.combatants.values()) resetStance(a, c, now);
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
        // 무기 이름은 띄우지 않음. 총이면 탄수만 우측 하단에 (AmmoHud: 쉐이더가 옮김), 가운데 오른쪽에는 가면·남은 시간·방패
        WeaponType t = pc.weaponType(plugin.weapons().fist());
        StringBuilder midText = new StringBuilder();
        Component mid = Component.empty();
        if (pc.mask != null) {
            String m = "[" + pc.mask.displayName() + "]";
            midText.append(m);
            mid = mid.append(Glyphs.text(m, Glyphs.HUD, Glyphs.PINK));
        }
        if (pc.weapon != null && pc.weapon.expireTick() > 0) {
            long left = Math.max(0, pc.weapon.expireTick() - now);
            String m = "  " + (left / 20 + 1) + "s";
            midText.append(m);
            mid = mid.append(Glyphs.text(m, Glyphs.HUD, Glyphs.CYAN));
        }
        if (pc.bulletShield > 0) {
            String m = "  ◆".repeat(pc.bulletShield);
            midText.append(m);
            mid = mid.append(Glyphs.text(m, Glyphs.HUD, Glyphs.CYAN));
        }
        WeaponInstance off = t.isGun() ? pc.offhand : null;
        boolean reloading = pc.weapon != null && pc.weapon.isReloading(now);
        // [가운데 글의 숨은 짝][탄수][가운데 글][탄수의 숨은 짝] → 탄수의 오른쪽 끝이 늘 화면 가운데 (쉐이더가 오른쪽 아래로 옮김),
        // 가운데 글은 가운데의 오른쪽에 붙음
        Component c = Component.empty()
                .append(dev.violence.fx.AmmoHud.hiddenText(midText.toString()))
                .append(dev.violence.fx.AmmoHud.marked(t, pc.weapon, off, reloading))
                .append(mid)
                .append(dev.violence.fx.AmmoHud.hidden(t, pc.weapon, off));
        return c;
    }

    // ───────── 3인칭 손 아이템 ─────────

    /**
     * 다른 플레이어들에게 pc 가 든 아이템을 3인칭용으로 바꿔 보낸다 (본인 인벤토리는 1인칭용 그대로).
     * 양손 총은 장전된 석궁으로 보여 양팔 조준 자세가 되고, 근접 무기는 휘두르기 동작이 보인다.
     */
    public void syncHeld(PlayerCombatant pc) {
        Arena a = plugin.arena();
        if (a == null) return;
        WeaponType held = pc.weaponType(plugin.weapons().fist());
        // 3인칭 휘두르기 프레임 재생 중에는 손 아이템을 다시 보내지 않음 (프레임이 처음으로 튐)
        if (swingShowing(pc, held)) return;
        // 넘어짐/발차기 인형으로 실제 몸을 숨긴 동안에는 손 아이템도 숨김
        if (plugin.falls().hiding(pc)) return;
        java.util.Map<org.bukkit.inventory.EquipmentSlot, org.bukkit.inventory.ItemStack> eq = new java.util.EnumMap<>(org.bukkit.inventory.EquipmentSlot.class);
        boolean melee = dev.violence.weapon.WeaponItems.swings(held);
        if (!melee) pc.tpStanceLeft = false;
        eq.put(org.bukkit.inventory.EquipmentSlot.HAND, pc.state == CombatState.DEAD ? null
                : melee ? dev.violence.weapon.WeaponItems.worldStance(held, pc.tpStanceLeft) : dev.violence.weapon.WeaponItems.world(held));
        eq.put(org.bukkit.inventory.EquipmentSlot.OFF_HAND, pc.offhand != null && pc.state != CombatState.DEAD ? dev.violence.weapon.WeaponItems.world(pc.offhand.type()) : null);
        boolean using = usingPose(pc, held);
        // 근접 무기: 주 손을 왼손으로 보여 왼손이 손잡이 아래, 오른손이 위 (오른팔로 휘두름)
        boolean leftMain = melee && pc.state == CombatState.ALIVE;
        for (PlayerCombatant viewer : a.players.values()) {
            if (viewer == pc || !viewer.player().isOnline()) continue;
            plugin.poses().sendMainHand(viewer.player(), pc.player(), leftMain);
            viewer.player().sendEquipmentChange(pc.player(), eq);
            plugin.poses().sendUsing(viewer.player(), pc.player(), using);
        }
    }

    /** "사용 중" 자세가 필요한 손 아이템: 권총 한 팔 조준, 근접 무기 두 손 대기 */
    private static boolean usingPose(Combatant c, WeaponType held) {
        if (c.state != CombatState.ALIVE) return false;
        return held.isGun() ? dev.violence.weapon.WeaponItems.oneHanded(held) : dev.violence.weapon.WeaponItems.swings(held);
    }

    private boolean swingShowing(Combatant c, WeaponType held) {
        return c.state == CombatState.ALIVE && held == c.tpSwingType && plugin.now() < c.tpSwingUntil;
    }

    /** NPC 의 권총 한 팔 조준 / 근접 두 손 대기 자세를 모든 플레이어에게 */
    public void syncNpcPose(NpcCombatant n) {
        Arena a = plugin.arena();
        if (a == null) return;
        WeaponType held = n.weaponType(plugin.weapons().fist());
        if (swingShowing(n, held)) return;
        boolean using = usingPose(n, held);
        if (!dev.violence.weapon.WeaponItems.swings(held)) n.tpStanceLeft = false;
        if (!using && !n.poseSent) return;
        n.poseSent = using;
        org.bukkit.Location at = n.entity().getLocation();
        for (PlayerCombatant viewer : a.players.values()) {
            Player vp = viewer.player();
            // 멀리 있어 보이지 않는 NPC 는 건너뜀 (가까워지면 다음 주기에 받음)
            if (!vp.isOnline() || vp.getWorld() != at.getWorld() || vp.getLocation().distanceSquared(at) > 72 * 72) continue;
            // 주 손(근접이면 왼손)은 NPC 실제 값으로 보냄 (NpcCombatant.refreshEquipment). 왼쪽 대기 아이템만 따로
            if (n.tpStanceLeft && using) vp.sendEquipmentChange(n.entity(), org.bukkit.inventory.EquipmentSlot.HAND,
                    dev.violence.weapon.WeaponItems.worldStance(held, true));
            plugin.poses().sendUsing(vp, n.entity(), using);
        }
    }

    /**
     * 3인칭 근접 휘두르기 (보는 사람 모두에게).
     * 무기는 왼손(주 손)에 들고 오른손이 위를 잡는다. 휘두르기는 오른팔(보조 손) 휘두르기로 보내 방향과 상관없이 오른팔이 휘두른다.
     * backhand 이면 왼→오, 아니면 오→왼 휘두르기 아이템으로 바꾸고 "사용 시작"을 다시 보내 프레임을 0 틱부터 재생한다.
     * 끝나면 반대쪽 대기 아이템으로 바꾼다 (휘두르기 끝 자세와 같아서 무기가 튀지 않음).
     */
    public void tpSwing(Combatant c, WeaponType t, boolean backhand, long now) {
        Arena a = plugin.arena();
        if (a == null || !dev.violence.weapon.WeaponItems.swings(t) || c.state != CombatState.ALIVE) return;
        int seq = ++c.tpSwingSeq;
        c.tpStanceLeft = backhand;
        c.tpSwingType = t;
        c.tpSwingUntil = now + dev.violence.weapon.WeaponItems.TP_SWING_TICKS;
        sendHand(a, c, dev.violence.weapon.WeaponItems.worldSwing(t, backhand), true);
        // 오른팔 휘두르기: 플레이어는 보는 사람에게만 보내고(본인 1인칭에 영향 없음), NPC 는 그대로 방송
        if (c instanceof NpcCombatant) c.entity().swingOffHand();
        else {
            for (PlayerCombatant viewer : a.players.values()) {
                if (viewer == c || !viewer.player().isOnline()) continue;
                plugin.poses().sendSwing(viewer.player(), c.entity(), true);
            }
        }
        plugin.laterIn(a, dev.violence.weapon.WeaponItems.TP_SWING_TICKS, () -> {
            if (c.tpSwingSeq != seq) return;
            c.tpSwingType = null;
            if (c.state != CombatState.ALIVE || c.weaponType(plugin.weapons().fist()) != t) return;
            c.tpStanceLeft = !backhand;
            sendHand(a, c, dev.violence.weapon.WeaponItems.worldStance(t, c.tpStanceLeft), false);
        });
    }

    private void sendHand(Arena a, Combatant c, org.bukkit.inventory.ItemStack item, boolean restart) {
        org.bukkit.entity.LivingEntity e = c.entity();
        if (e == null) return;
        java.util.Map<org.bukkit.inventory.EquipmentSlot, org.bukkit.inventory.ItemStack> eq = new java.util.EnumMap<>(org.bukkit.inventory.EquipmentSlot.class);
        eq.put(org.bukkit.inventory.EquipmentSlot.HAND, item);
        for (PlayerCombatant viewer : a.players.values()) {
            if (viewer == c || !viewer.player().isOnline()) continue;
            if (c instanceof PlayerCombatant) plugin.poses().sendMainHand(viewer.player(), e, true);
            viewer.player().sendEquipmentChange(e, eq);
            if (restart) plugin.poses().restartUsing(viewer.player(), e);
            else plugin.poses().sendUsing(viewer.player(), e, true);
        }
    }

    /** 연속 휘두르기가 끊기면(1인칭과 같은 기준) 다시 오른쪽 대기로 */
    private void resetStance(Arena a, Combatant c, long now) {
        if (!c.tpStanceLeft || plugin.now() < c.tpSwingUntil) return;
        WeaponType t = c.weaponType(plugin.weapons().fist());
        if (now - c.lastSwingTick <= t.meleeCooldown() + 12) return;
        c.tpStanceLeft = false;
        if (c.state != CombatState.ALIVE || !dev.violence.weapon.WeaponItems.swings(t)) return;
        sendHand(a, c, dev.violence.weapon.WeaponItems.worldStance(t, false), false);
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
            plugin.hud().killFlash(pc.player());   // 처치 흑백 깜빡임
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
            plugin.masks().clearOffer(vp);
            scores.flushCombo(vp);
            plugin.shake().setBaseline(vp.player(), 0);
        }
    }

    // ───────── 종료 ─────────

    public void end(Combatant winner) {
        Arena a = plugin.arena();
        if (a == null || state == State.ENDING) return;
        state = State.ENDING;
        plugin.combat().cancelAllExecutions();   // 순위 발표 뒤 처형으로 킬이 늘지 않게
        for (PlayerCombatant pc : a.players.values()) scores.flushCombo(pc);
        List<Combatant> ranking = new ArrayList<>(a.combatants.values());
        ranking.sort(Comparator.<Combatant>comparingInt(c -> -c.kills).thenComparingInt(c -> -c.score));
        String wname = winner == null ? "-" : winner.name();
        int wk = winner == null ? 0 : winner.kills;
        titleAll(Component.text("GAME OVER").font(Glyphs.HUD_BIG).color(net.kyori.adventure.text.format.TextColor.color(Glyphs.PINK)),
                Component.text("우승: " + wname + " (" + wk + "킬)").font(Glyphs.PROMPT), 5, 100, 20);
        if (!bridge.call("gameend", wname, wk)) {
            dev.violence.chat.NoChat.log(Component.text("[VIOLENCE] 게임 종료! 우승: " + wname + " (" + wk + "킬)", NamedTextColor.LIGHT_PURPLE));
        }
        int rank = 1;
        for (Combatant c : ranking) {
            if (rank > 10) break;
            dev.violence.chat.NoChat.log(Component.text(String.format(" %2d. %-16s %3d킬  %,d점", rank, c.name(), c.kills, c.score),
                    c.isPlayer() ? NamedTextColor.YELLOW : NamedTextColor.GRAY));
            rank++;
        }
        for (PlayerCombatant pc : a.players.values()) {
            if (pc.isPlayer() && !ranking.subList(0, Math.min(10, ranking.size())).contains(pc)) {
                dev.violence.chat.NoChat.log(String.format("%s 순위: %d위  %d킬  %,d점", pc.name(), ranking.indexOf(pc) + 1, pc.kills, pc.score));
            }
        }
        // 모두 정지
        long now = plugin.now();
        for (Combatant c : a.combatants.values()) {
            c.moveLockUntil = Long.MAX_VALUE / 2;
            c.actionLockUntil = Long.MAX_VALUE / 2;
            c.applyStateVisuals();
        }
        int gen = generation;
        plugin.later(plugin.getConfig().getInt("game.end-delay-seconds", 8) * 20, () -> {
            if (gen == generation && state == State.ENDING && plugin.arena() == a) forceCleanup();
        });
    }

    /** /게임중단: 결과 없이 즉시 종료 */
    public boolean stop(CommandSender sender) {
        if (state == State.IDLE) {
            dev.violence.chat.NoChat.tell(sender, Component.text("진행 중인 게임이 없습니다.", NamedTextColor.RED));
            return false;
        }
        // Skript 가 있으면 game.sk 가 알림을 보내므로 한 번만
        if (!bridge.call("gamestop")) dev.violence.chat.NoChat.log(Component.text("[VIOLENCE] 게임이 중단되었습니다.", NamedTextColor.RED));
        forceCleanup();
        return true;
    }

    /** 정리: 플레이어 로비로, 엔티티/월드 제거 */
    private boolean cleaning;

    /** 정리 중 (플레이어를 로비로 옮기는 월드 이동을 '나감'으로 보지 않기 위해) */
    public boolean isCleaning() { return cleaning; }

    public void forceCleanup() {
        if (cleaning) return;
        cleaning = true;
        generation++;
        Arena a = plugin.arena();
        World w = a != null ? a.world : preparingWorld;
        // 단계마다 따로 보호: 하나가 실패해도 아레나 해제, 월드 제거, 상태 초기화는 반드시 실행
        safe("붙여넣기 중단", () -> plugin.maps().cancelPaste(w));
        safe("카메라 복구", () -> plugin.camera().resetAll());
        try {
            if (a != null) {
                for (PlayerCombatant pc : new ArrayList<>(a.players.values())) {
                    Player p = pc.player();
                    safe("플레이어 정리 " + p.getName(), () -> {
                        plugin.hud().clear(p);
                        plugin.shake().remove(p);
                        plugin.ground().removeHighlights(a, p.getUniqueId());
                        if (p.isOnline()) {
                            pc.restoreDefaults();
                            plugin.lobby().sendToLobby(p);
                        }
                    });
                }
                safe("넘어지는 인형 정리", () -> plugin.falls().clear());
                safe("피 정리", () -> plugin.blood().clear());
                safe("문 정리", () -> plugin.doors().clear(a));
                safe("엔티티 정리", () -> {
                    for (Entity e : new ArrayList<>(a.tracked)) if (e.isValid()) e.remove();
                    a.tracked.clear();
                });
                safe("전투 정리", () -> plugin.combat().clear());
                safe("가면 정리", () -> plugin.masks().clear());
                safe("시체 정리", () -> plugin.corpses().clear());
                safe("연출 정리", () -> plugin.fx().clear());
            }
        } finally {
            plugin.setArena(null);
            if (w != null) {
                // 남은 플레이어(관전자 등)도 내보낸 뒤 월드 제거
                safe("남은 플레이어 이동", () -> {
                    for (Player p : w.getPlayers()) plugin.lobby().sendToLobby(p);
                });
                safe("월드 제거", () -> plugin.maps().destroy(w));
            }
            preparingWorld = null;
            state = State.IDLE;
            cleaning = false;
        }
    }

    private void safe(String what, Runnable r) {
        try {
            r.run();
        } catch (RuntimeException e) {
            plugin.getLogger().log(java.util.logging.Level.WARNING, "정리 중 오류 (" + what + ")", e);
        }
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
        plugin.hud().clear(p);
        plugin.masks().forget(a, p.getUniqueId());
        a.remove(pc);
        pc.restoreDefaults();
        // 빈자리는 NPC 로 채움
        if (state == State.RUNNING) plugin.npcs().spawn(a, 1);
    }

    public void onPlayerJoinMidGame(Player p) {
        Arena a = plugin.arena();
        if (a == null || (state != State.RUNNING && state != State.COUNTDOWN)) return;
        if (!plugin.getConfig().getBoolean("game.allow-late-join", true)) return;
        if (a.players.containsKey(p.getUniqueId()) || !plugin.lobby().participants().contains(p)) return;   // 관전자/제외 대상
        // NPC 하나를 빼고 플레이어를 넣어 총원을 유지
        NpcCombatant n = null;
        for (int i = a.npcs.size() - 1; i >= 0; i--) {
            NpcCombatant c = a.npcs.get(i);
            if (c.state == CombatState.ALIVE && c.execution == null) {
                n = c;
                break;
            }
        }
        if (n == null && !a.npcs.isEmpty()) n = a.npcs.getLast();
        if (n != null) {
            if (n.execution != null) plugin.combat().cancelExecution(n.execution);
            plugin.combat().dropWeapons(n, n.look());
            a.remove(n);
            a.tracked.remove(n.entity());
            n.entity().remove();
        }
        addPlayer(a, p);
        PlayerCombatant pc = a.players.get(p.getUniqueId());
        if (pc != null && state == State.COUNTDOWN) {
            long now = plugin.now();
            pc.moveLockUntil = now + 60;
            pc.actionLockUntil = now + 60;
            pc.applyStateVisuals();
        }
    }

    public void shutdown() {
        if (state != State.IDLE) forceCleanup();
    }
}
