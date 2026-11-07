package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.math.Vec3;
import dev.violence.npc.NpcCombatant;
import dev.violence.player.PlayerCombatant;
import io.papermc.paper.datacomponent.DataComponentTypes;
import io.papermc.paper.datacomponent.item.CustomModelData;
import io.papermc.paper.datacomponent.item.ResolvableProfile;
import java.awt.image.BufferedImage;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import net.kyori.adventure.key.Key;
import org.bukkit.Color;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mannequin;
import org.bukkit.entity.Player;
import org.bukkit.entity.Pose;
import org.bukkit.inventory.EntityEquipment;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3d;
import org.joml.Vector3f;

/**
 * 쓰러지거나 죽을 때 넘어지는 동작.
 *
 * 맞은 방향으로 넘어진다: 앞에서 맞으면 뒤로(등으로 누움), 등 뒤에서 맞으면 앞으로(엎드림),
 * 샷건처럼 강한 공격을 앞에서 맞으면 두 팔을 벌리고 뒤로 날아간다 (fall.json, FallPose).
 *
 * 1) 넘어지는 동안: 실제 몸과 장비를 숨기고, 같은 크기·색의 6부위 인형(아이템 디스플레이)이 20fps 키프레임으로 넘어진다.
 * 2) 넘어진 뒤: 인형 대신 같은 스킨·장비의 마네킹(대역)이 같은 자세로 눕는다.
 *    바닐라는 등으로 누운 자세를 플레이어에게 줄 수 없어서(엎드린 자세만 있음), 쓰러져 있는 동안은 대역이 대신 누워 있고
 *    실제 몸은 숨긴 채 위치만 따라간다. 일어서면 대역을 치우고 실제 몸을 보인다.
 *    대역의 자세: 등 = 침대 없이 SLEEPING (바닐라가 발을 축으로 뒤로 눕힘), 엎드림 = SWIMMING (12틱 전환이 끝난 뒤 보임).
 * 3) 죽으면: 대역이 그대로 시체가 된다(CorpseService). 쓰러지지 않고 바로 죽어도 같은 순서로 넘어져 시체가 된다.
 * 처형 중에도 대역이 누워 있다. 아레나가 정리되면 모두 실제 몸으로 돌린다.
 *
 * 색: 플레이어는 스킨 그림에서 얼굴·머리카락·옷·바지·신발 색을 뽑아 쓰고(처음 한 번 내려받음), NPC 는 옷 색을 쓴다.
 * 가면을 쓰고 있으면 인형 머리 대신 가면 모델을 씌운다.
 */
public final class FallService {
    private static final EquipmentSlot[] SLOTS = {EquipmentSlot.HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.HEAD,
            EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};
    /** 기본 색: 피부, 머리카락, 윗옷, 바지, 신발 */
    static final int[] DEFAULT_COLORS = {0xC89A7A, 0x3B2A1E, 0x3C8C96, 0x323278, 0x222222};
    /** 쓰고 있는 가면을 머리에 씌울 때 크기 (머리 칸 아이템 = 0.625 블록) */
    private static final float MASK_SCALE = 0.625f;

    private final ViolencePlugin plugin;
    private final Map<FallPose.Kind, FallPose> poses;
    /** 쓰러져 있는 (살아 있는) 대상 */
    private final Map<UUID, Lying> downed = new HashMap<>();
    /** 넘어지는 중인 시체 */
    private final List<Lying> falling = new ArrayList<>();
    private final Map<UUID, int[]> skins = new ConcurrentHashMap<>();
    private final Map<UUID, Boolean> fetching = new ConcurrentHashMap<>();
    private HttpClient http;

    private static final class Lying {
        final Combatant victim;
        final Arena arena;
        final FallPose pose;
        /** 넘어지기 전 몸이 보던 방향 (도) */
        final float yaw;
        final double scale;
        final Map<FallPose.Part, ItemDisplay> parts = new EnumMap<>(FallPose.Part.class);
        ItemDisplay mask;
        Mannequin body;
        Location feet;
        boolean corpse;
        boolean revealed;
        int tick;

        Lying(Combatant victim, Arena arena, FallPose pose, float yaw) {
            this.victim = victim;
            this.arena = arena;
            this.pose = pose;
            this.yaw = yaw;
            this.scale = victim.scale();
        }
    }

    public FallService(ViolencePlugin plugin) {
        this.plugin = plugin;
        Map<FallPose.Kind, FallPose> p;
        try {
            p = FallPose.loadAll();
        } catch (RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "fall.json 읽기 실패 - 넘어지는 동작 없이 바로 눕습니다: " + e);
            p = null;
        }
        this.poses = p;
    }

    /** 쓰러져 있어서 실제 몸을 숨기고 대역(인형/마네킹)을 보여주는 중인지 */
    public boolean hiding(Combatant c) {
        return downed.containsKey(c.id);
    }

    // ───────── 시작 ─────────

    /** 쓰러진 직후 호출 (상태는 이미 DOWNED). push = 밀려나는 방향, strong = 샷건 등 강한 공격 */
    public void knockdown(Combatant c, Vec3 push, boolean strong) {
        Arena a = plugin.arena();
        LivingEntity e = c.entity();
        if (poses == null || a == null || e == null || !e.isValid() || c.state != CombatState.DOWNED || downed.containsKey(c.id)) return;
        Lying l = create(a, c, push, strong, e.getLocation());
        if (l == null) return;
        downed.put(c.id, l);
        e.setInvisible(true);
        sendEquipment(a, c, true);
    }

    /**
     * 죽은 자리의 시체 (CorpseService 가 수명 관리). 쓰러져 누워 있던 대역이 있으면 그대로 시체가 되고,
     * 없으면 넘어지는 동작부터 보여준다. 만들 수 없으면 null.
     */
    public Mannequin corpse(Arena a, Combatant v, Vec3 push, boolean strong) {
        Lying l = downed.remove(v.id);
        if (l != null) {
            l.corpse = true;
            falling.add(l);
            // 실제 몸은 죽어서 숨겨진 상태 → 다음 틱에 실제 장비(죽으며 비워짐)를 다시 보냄
            plugin.laterIn(a, 1, () -> {
                if (a.combatants.containsKey(v.id)) sendEquipment(a, v, false);
            });
            return l.body;
        }
        if (poses == null || v.entity() == null) return null;
        Location at = v.entity().getLocation();
        l = create(a, v, push, strong, at);
        if (l == null) return null;
        l.corpse = true;
        falling.add(l);
        return l.body;
    }

    private Lying create(Arena a, Combatant c, Vec3 push, boolean strong, Location at) {
        Vec3 face = c.look().horizontal();
        Vec3 p = push == null ? Vec3.ZERO : push.horizontal();
        FallPose.Kind kind = FallPose.kindFor(p.x(), p.z(), face.x(), face.z(), strong);
        // 넘어지는 방향을 밀려나는 방향에 맞춤 (앞으로 = 밀리는 쪽을 봄, 뒤로 = 밀려오는 쪽을 봄)
        float yaw;
        if (p.lengthSq() < 1e-6) yaw = (float) (face.lengthSq() < 1e-6 ? at.getYaw() : face.yaw());
        else yaw = (float) (kind == FallPose.Kind.FORWARD ? p.yaw() : p.mul(-1).yaw());
        Lying l = new Lying(c, a, poses.get(kind), yaw);
        l.feet = feet(at);
        try {
            int[] col = colors(c);
            for (FallPose.Part part : FallPose.Part.values()) {
                if (part == FallPose.Part.HEAD && c.mask != null) continue;
                l.parts.put(part, a.track(a.world.spawn(l.feet, ItemDisplay.class, d -> setup(d, partItem(part, col)))));
            }
            if (c.mask != null) {
                l.mask = a.track(a.world.spawn(l.feet, ItemDisplay.class, d -> {
                    setup(d, dev.violence.weapon.WeaponItems.mask(c.mask, false));
                    d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.HEAD);
                }));
            }
            l.body = spawnDouble(a, c, l);
        } catch (RuntimeException ex) {
            plugin.getLogger().log(Level.WARNING, "넘어지는 인형 생성 실패: " + ex);
            removePuppet(l);
            if (l.body != null && l.body.isValid()) l.body.remove();
            return null;
        }
        place(l, 0, false);
        return l;
    }

    /** 넘어진 뒤 누워 있을 대역 (처음엔 숨김: 엎드린 자세 전환을 숨긴 채 끝냄) */
    private Mannequin spawnDouble(Arena a, Combatant c, Lying l) {
        Location loc = doubleLocation(l);
        return a.track(a.world.spawn(loc, Mannequin.class, m -> {
            m.setPersistent(false);
            m.setImmovable(true);
            m.setDescription(null);
            m.setInvulnerable(true);
            m.setSilent(true);
            m.setGravity(false);
            m.setCollidable(false);
            m.setInvisible(true);
            if (c instanceof NpcCombatant n) m.setProfile(n.profile());
            else if (c.entity() instanceof Player p) m.setProfile(ResolvableProfile.resolvableProfile(p.getPlayerProfile()));
            if (c.heavy) {
                var s = m.getAttribute(org.bukkit.attribute.Attribute.SCALE);
                if (s != null) s.setBaseValue(c.scale());
            }
            m.setBodyYaw(loc.getYaw());
            try {
                m.setPose(l.pose.faceUp() ? Pose.SLEEPING : Pose.SWIMMING, true);
            } catch (IllegalArgumentException ex) {
                Poses.lying(m);
            }
        }));
    }

    private static Location doubleLocation(Lying l) {
        Location loc = l.feet.clone();
        if (l.pose.faceUp()) {
            loc.add(0, l.pose.lift() * l.scale, 0);
            loc.setYaw(FallPose.sleepingYaw(l.yaw));
        } else {
            loc.setYaw(l.yaw);
        }
        loc.setPitch(0);
        return loc;
    }

    // ───────── 매 틱 ─────────

    public void tick() {
        if (!downed.isEmpty()) {
            for (Lying l : new ArrayList<>(downed.values())) {
                LivingEntity e = l.victim.entity();
                boolean gone = e == null || !e.isValid() || plugin.arena() != l.arena || !l.arena.combatants.containsKey(l.victim.id);
                if (gone || !l.victim.state.isDownedLike()) {
                    // 일어섬 (죽었으면 corpse() 가 먼저 데려감)
                    downed.remove(l.victim.id);
                    end(l, !gone);
                    continue;
                }
                // 기어가면 따라감 (방향은 그대로)
                Location now = feet(e.getLocation());
                if (now.distanceSquared(l.feet) > 1e-4) {
                    l.feet = now;
                    if (l.body != null && l.body.isValid()) l.body.teleport(doubleLocation(l));
                }
                advance(l);
                if (l.revealed && l.tick % 10 == 0) sendEquipment(l.arena, l.victim, true);
            }
        }
        if (!falling.isEmpty()) {
            for (Lying l : new ArrayList<>(falling)) {
                if (l.body == null || !l.body.isValid() || plugin.arena() != l.arena) {
                    removePuppet(l);
                    falling.remove(l);
                    continue;
                }
                advance(l);
                if (l.tick > l.pose.holdTicks()) falling.remove(l);
            }
        }
    }

    /** 다음 프레임 → 끝나기 한 틱 전에 대역을 보이고, 끝나면 인형을 치움 (한 틱 겹쳐서 빈 틱이 없게) */
    private void advance(Lying l) {
        l.tick++;
        int hold = l.pose.holdTicks();
        if (l.tick < hold) place(l, l.pose.frameAt(l.tick), true);
        if (!l.revealed && l.tick >= hold - 1) reveal(l);
        if (l.tick == hold) removePuppet(l);
    }

    private void reveal(Lying l) {
        l.revealed = true;
        Mannequin m = l.body;
        if (m == null || !m.isValid()) return;
        EntityEquipment eq = m.getEquipment();
        Combatant c = l.victim;
        if (c instanceof NpcCombatant n) n.copyOutfitTo(eq);
        else if (c.entity() instanceof Player p) {
            // 시체가 되었으면 가면은 벗겨진 상태 (죽을 때 가면이 사라짐)
            eq.setHelmet(l.corpse ? null : p.getInventory().getHelmet());
            eq.setChestplate(p.getInventory().getChestplate());
            eq.setLeggings(p.getInventory().getLeggings());
        }
        m.setInvisible(false);
    }

    private void end(Lying l, boolean restore) {
        removePuppet(l);
        if (l.body != null && l.body.isValid()) {
            l.arena.tracked.remove(l.body);
            l.body.remove();
        }
        LivingEntity e = l.victim.entity();
        if (!restore || e == null || !e.isValid()) return;
        l.victim.applyStateVisuals();
        sendEquipment(l.arena, l.victim, false);
    }

    /** 아레나 정리 시: 모두 실제 몸으로 */
    public void clear() {
        for (Lying l : new ArrayList<>(downed.values())) end(l, true);
        for (Lying l : falling) removePuppet(l);
        downed.clear();
        falling.clear();
    }

    private static void removePuppet(Lying l) {
        for (ItemDisplay d : l.parts.values()) if (d.isValid()) d.remove();
        l.parts.clear();
        if (l.mask != null && l.mask.isValid()) l.mask.remove();
        l.mask = null;
    }

    private static Location feet(Location src) {
        Location l = src.clone();
        l.setYaw(0);
        l.setPitch(0);
        return l;
    }

    private static void setup(ItemDisplay d, ItemStack item) {
        d.setPersistent(false);
        d.setItemStack(item);
        d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
        d.setInterpolationDuration(1);
        d.setTeleportDuration(1);
        d.setShadowRadius(0);
        d.setViewRange(1.5f);
    }

    private void place(Lying l, int frame, boolean animate) {
        for (FallPose.Part part : FallPose.Part.values()) {
            ItemDisplay d = part == FallPose.Part.HEAD && l.mask != null ? l.mask : l.parts.get(part);
            if (d == null || !d.isValid()) continue;
            FallPose.Placement p = l.pose.place(frame, part, l.scale);
            Vector3d c = FallPose.toWorld(p.center(), l.yaw);
            Quaternionf r = new Quaternionf(FallPose.toWorld(p.rotation(), l.yaw));
            float sc = (float) (FallPose.PX * 16 * l.scale) * (d == l.mask ? MASK_SCALE : 1f);
            if (d.getLocation().distanceSquared(l.feet) > 1e-4) d.teleport(l.feet);
            d.setTransformation(new Transformation(new Vector3f((float) c.x, (float) c.y, (float) c.z), r,
                    new Vector3f(sc, sc, sc), new Quaternionf()));
            if (animate) d.setInterpolationDelay(0);
        }
    }

    /** 보는 사람들에게 실제 몸의 장비를 숨김(hide) / 다시 보냄 */
    private void sendEquipment(Arena a, Combatant c, boolean hide) {
        LivingEntity e = c.entity();
        if (e == null) return;
        Map<EquipmentSlot, ItemStack> eq = new EnumMap<>(EquipmentSlot.class);
        EntityEquipment real = e.getEquipment();
        for (EquipmentSlot slot : SLOTS) {
            ItemStack it = hide || real == null ? null : real.getItem(slot);
            eq.put(slot, it == null ? new ItemStack(Material.AIR) : it);
        }
        for (PlayerCombatant viewer : a.players.values()) {
            if (viewer == c || !viewer.player().isOnline()) continue;
            viewer.player().sendEquipmentChange(e, eq);
        }
        // 손 아이템은 3인칭용으로 바꿔 보내는 것이 따로 있음
        if (!hide && c instanceof PlayerCombatant pc) plugin.game().syncHeld(pc);
        if (!hide && c instanceof NpcCombatant n) plugin.game().syncNpcPose(n);
    }

    // ───────── 인형 아이템 / 색 ─────────

    private static ItemStack partItem(FallPose.Part part, int[] col) {
        String model;
        int c0;
        int c1;
        switch (part) {
            case HEAD -> { model = "head"; c0 = col[0]; c1 = col[1]; }
            case BODY -> { model = "body"; c0 = col[2]; c1 = col[2]; }
            case ARM_R, ARM_L -> { model = "arm"; c0 = col[2]; c1 = col[0]; }
            default -> { model = "leg"; c0 = col[3]; c1 = col[4]; }
        }
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence", "puppet/" + model));
        it.setData(DataComponentTypes.CUSTOM_MODEL_DATA, CustomModelData.customModelData()
                .addColor(Color.fromRGB(c0 & 0xFFFFFF)).addColor(Color.fromRGB(c1 & 0xFFFFFF)).build());
        return it;
    }

    private int[] colors(Combatant c) {
        if (c instanceof NpcCombatant n) {
            int o = n.outfitColor();
            return new int[] {DEFAULT_COLORS[0], DEFAULT_COLORS[1], o, darker(o), 0x222222};
        }
        if (c instanceof PlayerCombatant pc) {
            prefetch(pc.player());
            int[] s = skins.get(pc.player().getUniqueId());
            if (s != null) return s;
        }
        return DEFAULT_COLORS.clone();
    }

    static int darker(int rgb) {
        int r = (rgb >> 16 & 0xFF) * 6 / 10, g = (rgb >> 8 & 0xFF) * 6 / 10, b = (rgb & 0xFF) * 6 / 10;
        return (r << 16) | (g << 8) | b;
    }

    /** 플레이어 스킨에서 인형 색을 뽑아 둔다 (비동기, 실패하면 기본 색) */
    public void prefetch(Player p) {
        UUID id = p.getUniqueId();
        if (skins.containsKey(id) || fetching.putIfAbsent(id, Boolean.TRUE) != null) return;
        java.net.URL url;
        try {
            url = p.getPlayerProfile().getTextures().getSkin();
        } catch (RuntimeException e) {
            url = null;
        }
        if (url == null) {
            skins.put(id, DEFAULT_COLORS.clone());
            fetching.remove(id);
            return;
        }
        final String target = url.toString();
        plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
            try {
                if (http == null) http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
                HttpResponse<byte[]> res = http.send(HttpRequest.newBuilder(URI.create(target)).timeout(Duration.ofSeconds(8)).build(),
                        HttpResponse.BodyHandlers.ofByteArray());
                BufferedImage img = res.statusCode() == 200 ? javax.imageio.ImageIO.read(new java.io.ByteArrayInputStream(res.body())) : null;
                skins.put(id, img == null ? DEFAULT_COLORS.clone() : skinColors(img));
            } catch (Exception e) {
                skins.put(id, DEFAULT_COLORS.clone());
            } finally {
                fetching.remove(id);
            }
        });
    }

    /** 64×64(또는 64×32) 스킨 그림 → 피부, 머리카락, 윗옷, 바지, 신발 색 */
    static int[] skinColors(BufferedImage img) {
        int u = Math.max(1, img.getWidth() / 64);
        return new int[] {
            average(img, 8, 12, 16, 16, u, DEFAULT_COLORS[0]),   // 얼굴 아래쪽 (눈 아래)
            average(img, 8, 0, 16, 8, u, DEFAULT_COLORS[1]),     // 머리 위
            average(img, 20, 20, 28, 32, u, DEFAULT_COLORS[2]),  // 몸통 앞
            average(img, 4, 20, 8, 28, u, DEFAULT_COLORS[3]),    // 다리 앞 위쪽
            average(img, 4, 30, 8, 32, u, DEFAULT_COLORS[4]),    // 다리 앞 끝 (신발)
        };
    }

    private static int average(BufferedImage img, int x0, int y0, int x1, int y1, int u, int fallback) {
        long r = 0, g = 0, b = 0, n = 0;
        for (int y = y0 * u; y < Math.min(img.getHeight(), y1 * u); y++) {
            for (int x = x0 * u; x < Math.min(img.getWidth(), x1 * u); x++) {
                int argb = img.getRGB(x, y);
                if ((argb >>> 24) < 128) continue;
                r += argb >> 16 & 0xFF;
                g += argb >> 8 & 0xFF;
                b += argb & 0xFF;
                n++;
            }
        }
        if (n == 0) return fallback;
        return (int) (r / n) << 16 | (int) (g / n) << 8 | (int) (b / n);
    }
}
