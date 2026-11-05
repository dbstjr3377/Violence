package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.npc.NpcCombatant;
import dev.violence.player.PlayerCombatant;
import io.papermc.paper.datacomponent.DataComponentTypes;
import io.papermc.paper.datacomponent.item.CustomModelData;
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
import org.bukkit.entity.Player;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3d;
import org.joml.Vector3f;

/**
 * 쓰러질 때 6프레임(20fps) 넘어지는 동작.
 *
 * 바닐라는 엎드린 자세로 바뀔 때 몸이 바닥에 반쯤 묻혔다가 0.55초에 걸쳐 천천히 눕는다.
 * 그동안 실제 몸과 장비를 숨기고, 같은 크기·색의 6부위 인형(아이템 디스플레이)으로 앞으로 고꾸라지는 동작을 보여준다.
 * 인형의 마지막 프레임은 바닐라 엎드린 자세와 같아서, 바닐라 전환이 끝난 뒤(12틱) 실제 몸으로 바꿔도 튀지 않는다.
 * 처형·사망·일어서기 등 상태가 바뀌면 바로 끝내고 실제 몸을 보인다.
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
    private final FallPose pose;
    private final Map<UUID, Fall> active = new HashMap<>();
    private final Map<UUID, int[]> skins = new ConcurrentHashMap<>();
    private final Map<UUID, Boolean> fetching = new ConcurrentHashMap<>();
    private HttpClient http;

    private static final class Fall {
        final Combatant c;
        final Arena arena;
        final Map<FallPose.Part, ItemDisplay> parts = new EnumMap<>(FallPose.Part.class);
        ItemDisplay mask;
        int tick;

        Fall(Combatant c, Arena arena) {
            this.c = c;
            this.arena = arena;
        }
    }

    public FallService(ViolencePlugin plugin) {
        this.plugin = plugin;
        FallPose p;
        try {
            p = FallPose.load();
        } catch (RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "fall.json 읽기 실패 - 넘어지는 동작 없이 바로 눕습니다: " + e);
            p = null;
        }
        this.pose = p;
    }

    /** 넘어지는 중이라 실제 몸을 숨겨야 하는지 */
    public boolean hiding(Combatant c) {
        return active.containsKey(c.id);
    }

    /** 쓰러진 직후 호출 (상태는 이미 DOWNED, 엎드린 자세 전환이 막 시작됨) */
    public void start(Combatant c) {
        Arena a = plugin.arena();
        LivingEntity e = c.entity();
        if (pose == null || a == null || e == null || !e.isValid() || c.state != CombatState.DOWNED || active.containsKey(c.id)) return;
        Fall f = new Fall(c, a);
        try {
            int[] col = colors(c);
            Location at = feet(e);
            for (FallPose.Part part : FallPose.Part.values()) {
                if (part == FallPose.Part.HEAD && c.mask != null) continue;
                f.parts.put(part, a.track(a.world.spawn(at, ItemDisplay.class, d -> setup(d, partItem(part, col)))));
            }
            if (c.mask != null) {
                f.mask = a.track(a.world.spawn(at, ItemDisplay.class, d -> {
                    setup(d, dev.violence.weapon.WeaponItems.mask(c.mask, false));
                    d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.HEAD);
                }));
            }
        } catch (RuntimeException ex) {
            plugin.getLogger().log(Level.WARNING, "넘어지는 인형 생성 실패: " + ex);
            remove(f);
            return;
        }
        active.put(c.id, f);
        place(f, 0, false);
        e.setInvisible(true);
        sendEquipment(a, c, true);
    }

    /** 매 틱: 다음 프레임, 끝나거나 상태가 바뀌면 실제 몸으로 */
    public void tick() {
        if (active.isEmpty()) return;
        for (Fall f : new ArrayList<>(active.values())) {
            f.tick++;
            LivingEntity e = f.c.entity();
            boolean done = f.tick >= pose.holdTicks() || f.c.state != CombatState.DOWNED || e == null || !e.isValid()
                    || plugin.arena() != f.arena || !f.arena.combatants.containsKey(f.c.id);
            if (done) {
                finish(f);
                continue;
            }
            place(f, pose.frameAt(f.tick), true);
        }
    }

    /** 아레나 정리 시: 모두 실제 몸으로 */
    public void clear() {
        for (Fall f : new ArrayList<>(active.values())) finish(f);
        active.clear();
    }

    private void finish(Fall f) {
        active.remove(f.c.id);
        remove(f);
        LivingEntity e = f.c.entity();
        if (e == null || !e.isValid()) return;
        f.c.applyStateVisuals();
        if (plugin.arena() == f.arena && f.arena.combatants.containsKey(f.c.id)) sendEquipment(f.arena, f.c, false);
        else e.setInvisible(false);
    }

    private static void remove(Fall f) {
        for (ItemDisplay d : f.parts.values()) if (d.isValid()) d.remove();
        f.parts.clear();
        if (f.mask != null && f.mask.isValid()) f.mask.remove();
        f.mask = null;
    }

    private static Location feet(LivingEntity e) {
        Location l = e.getLocation();
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

    private void place(Fall f, int frame, boolean animate) {
        LivingEntity e = f.c.entity();
        float yaw = e.getBodyYaw();
        double s = f.c.scale();
        Location at = feet(e);
        for (FallPose.Part part : FallPose.Part.values()) {
            ItemDisplay d = part == FallPose.Part.HEAD && f.mask != null ? f.mask : f.parts.get(part);
            if (d == null || !d.isValid()) continue;
            FallPose.Placement p = pose.place(frame, part, s);
            Vector3d c = FallPose.toWorld(p.center(), yaw);
            Quaternionf r = new Quaternionf(FallPose.toWorld(p.rotation(), yaw));
            float sc = (float) (FallPose.PX * 16 * s) * (d == f.mask ? MASK_SCALE : 1f);
            if (d.getLocation().distanceSquared(at) > 1e-4) d.teleport(at);
            d.setTransformation(new Transformation(new Vector3f((float) c.x, (float) c.y, (float) c.z), r,
                    new Vector3f(sc, sc, sc), new Quaternionf()));
            if (animate) d.setInterpolationDelay(0);
        }
    }

    /** 보는 사람들에게 실제 몸의 장비를 숨김(hide) / 다시 보냄 */
    private void sendEquipment(Arena a, Combatant c, boolean hide) {
        LivingEntity e = c.entity();
        Map<EquipmentSlot, ItemStack> eq = new EnumMap<>(EquipmentSlot.class);
        org.bukkit.inventory.EntityEquipment real = e.getEquipment();
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

    /** 테스트용: 프레임 계산 */
    public FallPose pose() { return pose; }

    static List<FallPose.Part> parts() { return List.of(FallPose.Part.values()); }
}
