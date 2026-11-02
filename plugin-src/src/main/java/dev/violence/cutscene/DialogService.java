package dev.violence.cutscene;

import dev.violence.ViolencePlugin;
import dev.violence.fx.Glyphs;
import dev.violence.game.GameService;
import dev.violence.math.Vec3;
import io.papermc.paper.datacomponent.DataComponentTypes;
import io.papermc.paper.datacomponent.item.Equippable;
import io.papermc.paper.datacomponent.item.TooltipDisplay;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.logging.Level;
import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.TextComponent;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextColor;
import net.kyori.adventure.title.Title;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.SoundCategory;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;

/**
 * 컷씬 다이얼로그 (핫라인 마이애미 2 대화 연출). 게임이 진행 중이 아닐 때 어드민이 시작한다.
 *  - 대사마다 지정한 개체를 비추는 위치로 카메라가 easeOutExpo 로 이동
 *  - 위/아래 검은 띠(카메라 오버레이), 오른쪽에서 자홍색 패널과 초상화(타이틀 글리프)가 들어옴
 *  - 아래 띠에 대사가 한 글자씩 찍힘(액션바), 초상화는 대사를 넘길 때까지 ±15° easeInOutSine 으로 흔들림
 *  - 어드민 왼클릭: 타자 중이면 대사 전체 표시, 다 나왔으면 다음 대사 (마지막이면 종료)
 * 보는 사람은 관전 모드로 카메라를 따라가 핫바 등 HUD 가 가려진다. 어드민은 원래 모드로 남아 왼클릭을 쓴다.
 */
public final class DialogService {
    public static final Key CUT_FONT = Key.key("violence", "cutscene");
    public static final Key[] LINE_FONTS = {Key.key("violence", "dialog1"), Key.key("violence", "dialog2")};
    private static final int MOVE_TICKS = 28;       // 카메라 이동 (easeOutExpo)
    private static final int PANEL_IN = 16;
    private static final int PANEL_OUT = 7;
    private static final double SWAY_HALF = 20;     // 초상화가 한쪽 끝에서 반대쪽까지 가는 틱
    private static final int CLICK_GAP = 4;

    private record Line(UUID target, String portrait, String text) {}
    private record Saved(GameMode mode, Location loc, ItemStack helmet, double speed, double jump, boolean admin) {}

    private final ViolencePlugin plugin;
    private CutsceneAssets assets;
    private DialogLayout layout;

    private boolean active;
    private boolean ending;
    private UUID admin;
    private ItemDisplay cam;
    private final Map<UUID, Saved> viewers = new LinkedHashMap<>();
    private final Deque<Line> queue = new ArrayDeque<>();
    private long tick;
    private long lastClick = -100;
    private long startedAt = -100;
    /** 시작에 실패한 틱: 같은 틱에 이어지는 대사(Skript)는 다른 사람 컷씬에 끼어들지 않게 버림 */
    private long beginFailedAt = -100;
    /** 컷씬용 임시 배우 (cutscene actor 명령으로 생성, 끝나면 제거) */
    private final Map<String, Entity> actors = new LinkedHashMap<>();

    // 현재 대사
    private Line current;
    private List<String> lines = List.of();
    private int total;
    private double revealed;
    private int shownChars = -1;
    private long lineStart;

    // 카메라
    private Location camFrom;
    private Location camTo;
    private long moveStart = -1;

    // 위아래 띠 (0 = 없음 ~ letterboxFrames = 다 들어옴)
    private int bar;
    private int barTarget;

    // 패널 (0 = 제자리, 1 = 화면 밖)
    private double panelFrom = 1;
    private double panelTarget = 1;
    private long panelStart;
    private int panelDur = 1;
    private String portrait;
    private String pendingPortrait;
    private boolean titleShown;

    public DialogService(ViolencePlugin plugin) {
        this.plugin = plugin;
        reloadAssets();
    }

    /** plugins/ViolenceCore/cutscene.json (리소스팩 생성기가 만든 글리프/글자 폭 정보) */
    public void reloadAssets() {
        Path file = plugin.getDataFolder().toPath().resolve("cutscene.json");
        try {
            assets = CutsceneAssets.load(file);
            layout = new DialogLayout(assets);
        } catch (Exception e) {
            assets = null;
            layout = null;
            plugin.getLogger().log(Level.WARNING, "컷씬 정보(cutscene.json)를 읽지 못했습니다 - 컷씬을 쓸 수 없습니다: " + e);
        }
    }

    public boolean active() { return active; }

    public boolean isAdmin(Player p) { return active && p.getUniqueId().equals(admin); }

    public boolean isViewer(Player p) { return active && viewers.containsKey(p.getUniqueId()); }

    public ItemDisplay camera() { return cam; }

    private static void msg(CommandSender s, String text, NamedTextColor c) {
        s.sendMessage(Component.text("[컷씬] " + text, c));
    }

    // ───────────────────────── 시작 / 대사 / 넘기기 / 종료 ─────────────────────────

    /** 콘솔(Skript)에서 실행돼도 어드민이 이유를 볼 수 있게 */
    private static void msgBoth(CommandSender sender, Player adminPlayer, String text, NamedTextColor c) {
        msg(sender, text, c);
        if (adminPlayer != null && adminPlayer != sender) msg(adminPlayer, text, c);
    }

    public boolean begin(CommandSender sender, Player adminPlayer) {
        boolean ok = beginInner(sender, adminPlayer);
        if (!ok) beginFailedAt = plugin.now();
        return ok;
    }

    private boolean beginInner(CommandSender sender, Player adminPlayer) {
        if (layout == null) {
            msgBoth(sender, adminPlayer, "cutscene.json 이 없어 컷씬을 시작할 수 없습니다. 리소스팩을 다시 만들어 주세요.", NamedTextColor.RED);
            return false;
        }
        if (active) {
            msgBoth(sender, adminPlayer, "이미 컷씬이 진행 중입니다.", NamedTextColor.RED);
            return false;
        }
        if (plugin.game().state() != GameService.State.IDLE) {
            msgBoth(sender, adminPlayer, "게임 중에는 컷씬을 시작할 수 없습니다. 게임이 끝난 뒤(로비) 실행하세요.", NamedTextColor.RED);
            return false;
        }
        if (adminPlayer == null || !adminPlayer.isOnline()) {
            msg(sender, "컷씬을 진행할 어드민(플레이어)을 찾을 수 없습니다.", NamedTextColor.RED);
            return false;
        }
        if (!plugin.lobby().isLobby(adminPlayer.getWorld())) {
            msg(adminPlayer, "컷씬은 로비에서만 시작할 수 있습니다.", NamedTextColor.RED);
            return false;
        }
        active = true;
        ending = false;
        admin = adminPlayer.getUniqueId();
        startedAt = plugin.now();
        queue.clear();
        current = null;
        tick = 0;
        lastClick = -100;          // 지난 컷씬의 시각이 남아 클릭이 막히지 않게
        moveStart = -1;
        camFrom = camTo = null;
        bar = 0;
        barTarget = assets.letterboxFrames;
        panelFrom = panelTarget = 1;
        portrait = pendingPortrait = null;
        titleShown = false;
        Location start = adminPlayer.getEyeLocation();
        cam = plugin.camera().spawnCamera(start, 2);
        cam.setTeleportDuration(2);
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (p.getWorld().equals(start.getWorld())) addViewer(p);
        }
        msg(adminPlayer, "컷씬 시작 - 왼클릭으로 대사를 넘깁니다.", NamedTextColor.LIGHT_PURPLE);
        return true;
    }

    /** 대사 추가. 지금 보이는 대사가 없으면 바로 시작한다. */
    public boolean say(CommandSender sender, Entity target, String portraitId, String text) {
        if (beginFailedAt == plugin.now() && startedAt != plugin.now()) return false;
        if (text == null || text.isBlank()) text = "...";
        if (!active || ending) {
            msg(sender, "진행 중인 컷씬이 없습니다. 먼저 컷씬을 시작하세요.", NamedTextColor.RED);
            return false;
        }
        queue.addLast(new Line(target == null ? null : target.getUniqueId(), portraitId, text));
        if (current == null) advance();
        return true;
    }

    /** 어드민 왼클릭 */
    public void click() {
        if (!active || ending || tick - lastClick < CLICK_GAP) return;
        lastClick = tick;
        if (current != null && revealed < total) {
            revealed = total;
            return;
        }
        if (queue.isEmpty()) end();
        else advance();
    }

    public void end() {
        if (!active || ending) return;
        ending = true;
        current = null;
        queue.clear();
        barTarget = 0;
        slidePanel(1, PANEL_OUT);
        pendingPortrait = null;
        for (Player p : players()) p.sendActionBar(Component.empty());
    }

    /** 즉시 정리 (플러그인 종료, 오류) */
    public void abort() {
        if (!active) return;
        finish();
    }

    private void advance() {
        current = queue.pollFirst();
        if (current == null) return;
        lines = layout.wrap(current.text(), DialogLayout.MAX_LINE, LINE_FONTS.length);
        total = DialogLayout.length(lines);
        revealed = 0;
        shownChars = -1;
        lineStart = tick;
        // 카메라: 지정한 개체를 비추는 자리로
        Entity target = current.target() == null ? null : Bukkit.getEntity(current.target());
        if (target != null && cam != null && target.getWorld().equals(cam.getWorld())) {
            camFrom = cam.getLocation();
            Saved sv = viewers.get(target.getUniqueId());
            if (sv != null && !sv.admin()) {
                // 관전 중인 플레이어는 몸이 카메라에 붙어 있으므로 원래 서 있던 자리를 비춤
                Location eye = sv.loc().clone().add(0, 1.62, 0);
                camTo = shotForEye(eye);
            } else {
                camTo = shotFor(target);
            }
            moveStart = tick;
        }
        // 초상화가 바뀌면 패널이 잠깐 나갔다가 새 초상화로 들어옴
        String next = current.portrait();
        if (portrait == null || panelTarget >= 1) {
            portrait = next;
            pendingPortrait = null;    // 나가던 중 넘긴 경우: 남은 교체 예약 때문에 타자가 멈추지 않게
            slidePanel(0, PANEL_IN);
        } else if (!portrait.equalsIgnoreCase(next)) {
            pendingPortrait = next;
            slidePanel(1, PANEL_OUT);
        }
        for (Player p : players()) p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_ATTACK_SWEEP, SoundCategory.MASTER, 0.5f, 1.4f);
    }

    /** 개체의 얼굴을 비스듬히 앞에서 비추고, 오른쪽 패널을 피해 화면 왼쪽에 오도록 */
    static Location shotFor(Entity target) {
        Location eye = target instanceof LivingEntity le ? le.getEyeLocation() : target.getLocation().add(0, target.getHeight() * 0.85, 0);
        return shotForEye(eye);
    }

    static Location shotForEye(Location eye) {
        double yaw = Math.toRadians(eye.getYaw());
        Vec3 fwd = new Vec3(-Math.sin(yaw), 0, Math.cos(yaw));
        Vec3 right = fwd.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 e = new Vec3(eye.getX(), eye.getY(), eye.getZ());
        Vec3 c = e.add(fwd.mul(2.4)).add(right.mul(-0.55)).add(0, 0.25, 0);
        Vec3 toEye = e.sub(c).normalize();
        Vec3 camRight = toEye.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 look = e.add(camRight.mul(0.85)).sub(c).normalize();
        Location l = new Location(eye.getWorld(), c.x(), c.y(), c.z());
        l.setYaw((float) look.yaw());
        l.setPitch((float) look.pitch());
        return l;
    }

    private void slidePanel(double target, int ticks) {
        panelFrom = panelPos();
        panelTarget = target;
        panelStart = tick;
        panelDur = ticks;
    }

    private double panelPos() {
        double t = (tick - panelStart) / (double) panelDur;
        return Easing.lerp(panelFrom, panelTarget, Easing.outExpo(t));
    }

    private boolean panelSettled() {
        return tick - panelStart >= panelDur;
    }

    /**
     * 컷씬용 임시 배우 (NPC 와 같은 사람 모양). 어드민이 서 있는 곳 기준 앞쪽 forward, 오른쪽 side 블록에 세우고
     * facing 도(어드민 시선 기준)를 바라본다. mask 가 가면 이름이면 가면을 씌운다. 컷씬이 끝나면 사라진다.
     */
    public boolean actor(CommandSender sender, String id, String mask, double forward, double side, double facing) {
        if (!active || ending) {
            msg(sender, "진행 중인 컷씬이 없습니다.", NamedTextColor.RED);
            return false;
        }
        Player a = admin == null ? null : Bukkit.getPlayer(admin);
        Saved sv = admin == null ? null : viewers.get(admin);
        Location base = sv != null ? sv.loc() : (a != null ? a.getLocation() : null);
        if (base == null) return false;
        double yaw = Math.toRadians(base.getYaw());
        Vec3 fwd = new Vec3(-Math.sin(yaw), 0, Math.cos(yaw));
        Vec3 right = fwd.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 p = new Vec3(base.getX(), base.getY(), base.getZ()).add(fwd.mul(forward)).add(right.mul(side));
        Location l = new Location(base.getWorld(), p.x(), p.y(), p.z(), (float) (base.getYaw() + facing), 0);
        Entity old = actors.remove(id);
        if (old != null && old.isValid()) old.remove();
        org.bukkit.entity.Mannequin m = base.getWorld().spawn(l, org.bukkit.entity.Mannequin.class, b -> {
            b.setPersistent(false);
            b.setImmovable(true);
            b.setDescription(null);
            b.setSilent(true);
            b.setCustomNameVisible(false);
            b.addScoreboardTag("violence_actor");
        });
        dev.violence.mask.Mask mk = null;
        try {
            if (mask != null && !mask.equalsIgnoreCase("none")) mk = dev.violence.mask.Mask.valueOf(mask.toUpperCase(java.util.Locale.ROOT));
        } catch (IllegalArgumentException ignored) {
            msg(sender, "알 수 없는 가면: " + mask + " (가면 없이 세움)", NamedTextColor.YELLOW);
        }
        if (mk != null) m.getEquipment().setHelmet(dev.violence.weapon.WeaponItems.mask(mk, false));
        actors.put(id, m);
        return true;
    }

    public Entity actorEntity(String id) {
        Entity e = actors.get(id);
        return e != null && e.isValid() ? e : null;
    }

    // ───────────────────────── 보는 사람 ─────────────────────────

    public void addViewer(Player p) {
        if (!active || viewers.containsKey(p.getUniqueId())) return;
        boolean isAdmin = p.getUniqueId().equals(admin);
        viewers.put(p.getUniqueId(), new Saved(p.getGameMode(), p.getLocation(), p.getInventory().getHelmet(),
                attr(p, Attribute.MOVEMENT_SPEED, 0.1), attr(p, Attribute.JUMP_STRENGTH, 0.42), isAdmin));
        boolean spectate = !isAdmin && plugin.getConfig().getBoolean("cutscene.spectate-viewers", true);
        if (spectate) {
            p.setGameMode(GameMode.SPECTATOR);
            p.setSpectatorTarget(cam);
        } else {
            plugin.camera().view(p, cam);
            setAttr(p, Attribute.MOVEMENT_SPEED, 0);
            setAttr(p, Attribute.JUMP_STRENGTH, 0);
        }
        applyBar(p);
    }

    /** 나가는 플레이어는 원래 상태로 */
    public void removeViewer(Player p) {
        Saved s = viewers.remove(p.getUniqueId());
        if (s != null) restore(p, s);
    }

    private void restore(Player p, Saved s) {
        if (p.getGameMode() == GameMode.SPECTATOR) p.setSpectatorTarget(null);
        if (plugin.camera().isViewing(p)) plugin.camera().reset(p);
        p.setGameMode(s.mode());
        Location back = s.loc() != null && s.loc().isWorldLoaded() ? s.loc() : plugin.lobby().spawn();
        p.teleport(back);
        p.getInventory().setHelmet(s.helmet());
        setAttr(p, Attribute.MOVEMENT_SPEED, s.speed());
        setAttr(p, Attribute.JUMP_STRENGTH, s.jump());
        p.clearTitle();
        p.sendActionBar(Component.empty());
    }

    private List<Player> players() {
        List<Player> out = new ArrayList<>();
        for (UUID id : viewers.keySet()) {
            Player p = Bukkit.getPlayer(id);
            if (p != null && p.isOnline()) out.add(p);
        }
        return out;
    }

    private static double attr(Player p, Attribute a, double def) {
        AttributeInstance i = p.getAttribute(a);
        return i == null ? def : i.getBaseValue();
    }

    private static void setAttr(Player p, Attribute a, double v) {
        AttributeInstance i = p.getAttribute(a);
        if (i != null) i.setBaseValue(v);
    }

    // ───────────────────────── 매 틱 ─────────────────────────

    public void tick() {
        if (!active) return;
        tick++;
        if (cam == null || !cam.isValid()) {
            finish();
            return;
        }
        // 카메라 이동
        if (moveStart >= 0 && camFrom != null && camTo != null) {
            double t = (tick - moveStart) / (double) MOVE_TICKS;
            double e = Easing.outExpo(t);
            Location l = new Location(camTo.getWorld(),
                    Easing.lerp(camFrom.getX(), camTo.getX(), e), Easing.lerp(camFrom.getY(), camTo.getY(), e), Easing.lerp(camFrom.getZ(), camTo.getZ(), e),
                    (float) Easing.lerpAngle(camFrom.getYaw(), camTo.getYaw(), e), (float) Easing.lerp(camFrom.getPitch(), camTo.getPitch(), e));
            cam.teleport(l);
            if (t >= 1) moveStart = -1;
        }
        // 위아래 띠
        if (bar != barTarget) {
            bar += bar < barTarget ? 1 : -1;
            for (Player p : players()) applyBar(p);
        }
        // 초상화 교체: 패널이 다 나가면 새 초상화로 다시 들어옴
        if (pendingPortrait != null && panelTarget >= 1 && panelSettled()) {
            portrait = pendingPortrait;
            pendingPortrait = null;
            slidePanel(0, PANEL_IN);
        }
        // 타자 효과: 패널이 거의 들어온 뒤 시작
        boolean typing = current != null && pendingPortrait == null && panelTarget <= 0 && tick - panelStart >= PANEL_IN / 3;
        if (typing && revealed < total) {
            double before = revealed;
            revealed = Math.min(total, revealed + plugin.getConfig().getDouble("cutscene.chars-per-tick", 1.0));
            if ((int) revealed / 2 != (int) before / 2) {
                for (Player p : players()) p.playSound(p.getLocation(), Sound.BLOCK_NOTE_BLOCK_HAT, SoundCategory.MASTER, 0.25f, 1.7f + (float) (Math.random() * 0.2));
            }
        }
        render();
        // 관전자가 카메라에서 떨어지면 다시 붙임
        if (tick % 10 == 0) {
            for (Player p : players()) {
                if (p.getGameMode() == GameMode.SPECTATOR && p.getSpectatorTarget() != cam) p.setSpectatorTarget(cam);
            }
        }
        if (ending && bar == 0 && panelSettled()) finish();
    }

    private void render() {
        double panel = panelPos();
        List<Player> ps = players();
        // 패널 + 초상화 (타이틀)
        if (panel < 0.999 || !panelSettled()) {
            char frame = 0;
            if (portrait != null) {
                int base = assets.portraitBase(portrait);
                if (base >= 0) frame = assets.portraitFrame(base, Easing.sway(tick - lineStart, SWAY_HALF, assets.portraitSway));
            }
            Component title = toComponent(layout.panel(panel, frame));
            Title t = Title.title(title, Component.empty(), Title.Times.times(Duration.ZERO, Duration.ofSeconds(2), Duration.ZERO));
            for (Player p : ps) p.showTitle(t);
            titleShown = true;
        } else if (titleShown) {
            for (Player p : ps) p.clearTitle();
            titleShown = false;
        }
        // 대사 (액션바, 2초마다 다시 보내 사라지지 않게)
        if (current != null) {
            int chars = (int) revealed;
            if (chars != shownChars || tick % 20 == 0) {
                shownChars = chars;
                Component bar = toComponent(layout.dialog(lines, chars));
                for (Player p : ps) p.sendActionBar(bar);
            }
        }
    }

    private void applyBar(Player p) {
        p.getInventory().setHelmet(bar <= 0 ? null : letterbox(bar));
    }

    private static ItemStack letterbox(int frame) {
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence", "misc/blank"));
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        it.setData(DataComponentTypes.EQUIPPABLE, Equippable.equippable(EquipmentSlot.HEAD).swappable(false).dispensable(false)
                .cameraOverlay(Key.key("violence", "misc/letterbox_" + frame)).build());
        return it;
    }

    private Component toComponent(List<DialogLayout.Piece> pieces) {
        TextComponent.Builder b = Component.text();
        for (DialogLayout.Piece piece : pieces) {
            switch (piece) {
                case DialogLayout.Space s -> b.append(Glyphs.space(s.px()));
                case DialogLayout.Glyph g -> b.append(Component.text(String.valueOf(g.c())).font(CUT_FONT).color(TextColor.color(0xFFFFFF)));
                case DialogLayout.Text t -> b.append(Component.text(assets.tracked(t.text())).font(LINE_FONTS[Math.min(t.line(), LINE_FONTS.length - 1)])
                        .color(TextColor.color(0xFFFFFF)));
            }
        }
        return b.build();
    }

    private void finish() {
        // 목록을 먼저 비워야 관전 해제가 리스너에 막히지 않음
        List<Map.Entry<UUID, Saved>> all = new ArrayList<>(viewers.entrySet());
        viewers.clear();
        for (Map.Entry<UUID, Saved> e : all) {
            Player p = Bukkit.getPlayer(e.getKey());
            if (p == null || !p.isOnline()) continue;
            try {
                restore(p, e.getValue());
            } catch (RuntimeException ex) {
                plugin.getLogger().log(Level.WARNING, "컷씬 복구 실패: " + p.getName(), ex);
                try {
                    p.setGameMode(GameMode.ADVENTURE);
                    plugin.lobby().sendToLobby(p);
                } catch (RuntimeException ignored) {
                    // 최후 수단도 실패하면 재접속 때 로비 초기화가 처리
                }
            }
        }
        for (Entity actor : actors.values()) if (actor.isValid()) actor.remove();
        actors.clear();
        if (cam != null && cam.isValid()) cam.remove();
        cam = null;
        active = false;
        ending = false;
        current = null;
        queue.clear();
        admin = null;
    }
}
