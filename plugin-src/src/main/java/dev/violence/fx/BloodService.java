package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.math.Vec3;
import io.papermc.paper.datacomponent.DataComponentTypes;
import io.papermc.paper.datacomponent.item.CustomModelData;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.Iterator;
import java.util.List;
import java.util.Random;
import net.kyori.adventure.key.Key;
import org.bukkit.Color;
import org.bukkit.FluidCollisionMode;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.World;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.inventory.ItemStack;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 피 연출.
 *
 * 핏방울은 공격 방향으로 튀어 중력을 받으며 날아가고(날아가는 동안은 붉은 입자),
 * 바닥이나 벽에 닿으면 그 면에 붙는 혈흔(아이템 디스플레이)이 된다.
 * 혈흔은 면의 방향에 맞춰 눕거나 서고, 비스듬히 부딪힐수록 날아가던 쪽으로 길게 늘어진다(꼬리).
 * 5초 뒤 6단계 투명도 모델로 바꿔 가며 서서히 사라진다 (리소스팩 "fx/blood_splat_N", custom_model_data 0 = 투명도 단계).
 * 처형당한 시체는 머리에서 바닥으로 피가 천천히 흘러 퍼진다 (fx/blood_flow).
 */
public final class BloodService {
    public static final int SHAPES = 4;
    public static final int FADE_STEPS = 6;
    private static final Color DROP = Color.fromRGB(150, 8, 14);
    private static final double GRAVITY = 0.045;
    private static final int SPLAT_LIFE = 100;     // 5초
    private static final int FADE_STEP_TICKS = 4;

    private final ViolencePlugin plugin;
    private final Random rnd = new Random();
    private final List<Drop> drops = new ArrayList<>();
    private final Deque<Decal> decals = new ArrayDeque<>();
    private int maxDecals = 180;

    private static final class Drop {
        final Arena arena;
        Vec3 pos;
        Vec3 vel;
        final float size;
        int age;

        Drop(Arena arena, Vec3 pos, Vec3 vel, float size) {
            this.arena = arena;
            this.pos = pos;
            this.vel = vel;
            this.size = size;
        }
    }

    private static final class Decal {
        final Arena arena;
        final ItemDisplay display;
        final String model;
        final long fadeAt;
        int step;

        Decal(Arena arena, ItemDisplay display, String model, long fadeAt) {
            this.arena = arena;
            this.display = display;
            this.model = model;
            this.fadeAt = fadeAt;
        }
    }

    public BloodService(ViolencePlugin plugin) {
        this.plugin = plugin;
        this.maxDecals = plugin.getConfig().getInt("fx.max-decals", 180);
    }

    /**
     * 피 튀김. 공격 방향(dir)으로 핏방울이 날아가 바닥과 벽에 혈흔을 남긴다.
     * @param intensity 1(약) ~ 4(처형/헤드샷)
     */
    public void spray(Arena a, Vec3 point, Vec3 dir, int intensity) {
        Vec3 bias = dir.lengthSq() < 1e-6 ? Vec3.UP : dir.normalize();
        int n = 5 + intensity * 4;
        for (int i = 0; i < n; i++) {
            Vec3 r = new Vec3(rnd.nextGaussian(), rnd.nextGaussian() * 0.6, rnd.nextGaussian()).normalize();
            Vec3 d = bias.mul(1.4 + intensity * 0.2).add(r).add(0, 0.25, 0).normalize();
            double speed = 0.18 + rnd.nextDouble() * (0.18 + intensity * 0.06);
            float size = 0.22f + rnd.nextFloat() * (0.22f + intensity * 0.07f);
            drops.add(new Drop(a, point.add(r.mul(0.05)), d.mul(speed), size));
        }
    }

    /** 시체 밑 피 웅덩이 (시체가 사라질 즈음 사라짐) */
    public void pool(Arena a, Vec3 feet, float size) {
        Vec3 floor = floorBelow(a, feet.add(0, 0.5, 0), 3);
        if (floor == null) return;
        ItemDisplay d = decal(a, floor, Vec3.UP, null, "violence:fx/blood_pool", size, size, 18 * 20);
        if (d == null) return;
        // 처음엔 작게 → 2초에 걸쳐 퍼짐
        Transformation t = d.getTransformation();
        d.setTransformation(new Transformation(t.getTranslation(), t.getLeftRotation(), new Vector3f(size * 0.3f, 1, size * 0.3f), t.getRightRotation()));
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(40);
            d.setTransformation(t);
        });
    }

    /** 처형당한 시체: 머리에서 바닥으로 피가 천천히 흘러 퍼짐 (dir = 발 → 머리, 흘러가는 쪽) */
    public void headFlow(Arena a, Vec3 head, Vec3 dir) {
        Vec3 floor = floorBelow(a, head.add(0, 0.3, 0), 2.5);
        if (floor == null) return;
        Vec3 f = dir.horizontal().lengthSq() < 1e-6 ? new Vec3(1, 0, 0) : dir.horizontal().normalize();
        // 머리에서 시작해 머리 너머로 흐름: 판의 +x 가 흐르는 방향, 시작점이 머리 밑
        ItemDisplay d = decal(a, floor, Vec3.UP, f, "violence:fx/blood_flow", 0.18f, 0.12f, 16 * 20);
        if (d == null) return;
        Quaternionf q = d.getTransformation().getLeftRotation();
        Vector3f along = q.transform(new Vector3f(1, 0, 0));
        plugin.later(2, () -> {
            if (!d.isValid()) return;
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(70);
            float len = 1.5f;
            d.setTransformation(new Transformation(new Vector3f(along).mul(len * 0.42f), q, new Vector3f(len, 1, 0.62f), new Quaternionf()));
        });
    }

    public void tick() {
        if (!drops.isEmpty()) {
            for (Iterator<Drop> it = drops.iterator(); it.hasNext(); ) {
                Drop d = it.next();
                if (plugin.arena() != d.arena || ++d.age > 50) {
                    it.remove();
                    continue;
                }
                World w = d.arena.world;
                double len = d.vel.length();
                if (len > 1e-4) {
                    RayTraceResult r = w.rayTraceBlocks(Fx.loc(w, d.pos), new Vector(d.vel.x(), d.vel.y(), d.vel.z()), len,
                            FluidCollisionMode.NEVER, true);
                    if (r != null && r.getHitBlockFace() != null) {
                        Vector hp = r.getHitPosition();
                        Vector fn = r.getHitBlockFace().getDirection();
                        splat(d.arena, new Vec3(hp.getX(), hp.getY(), hp.getZ()), new Vec3(fn.getX(), fn.getY(), fn.getZ()), d.vel, d.size);
                        it.remove();
                        continue;
                    }
                }
                // 날아가는 핏방울 (선을 따라 입자 2개)
                Vec3 next = d.pos.add(d.vel);
                w.spawnParticle(Particle.DUST, Fx.loc(w, d.pos), 1, 0, 0, 0, 0, new Particle.DustOptions(DROP, 0.9f + d.size));
                w.spawnParticle(Particle.DUST, Fx.loc(w, d.pos.add(d.vel.mul(0.5))), 1, 0, 0, 0, 0, new Particle.DustOptions(DROP, 0.7f + d.size));
                d.pos = next;
                d.vel = d.vel.mul(0.98).add(0, -GRAVITY, 0);
            }
        }
        if (!decals.isEmpty()) {
            long now = plugin.now();
            for (Iterator<Decal> it = decals.iterator(); it.hasNext(); ) {
                Decal c = it.next();
                if (!c.display.isValid() || plugin.arena() != c.arena) {
                    it.remove();
                    continue;
                }
                if (now < c.fadeAt || (now - c.fadeAt) % FADE_STEP_TICKS != 0) continue;
                c.step++;
                if (c.step >= FADE_STEPS) {
                    c.arena.tracked.remove(c.display);
                    c.display.remove();
                    it.remove();
                } else {
                    c.display.setItemStack(item(c.model, c.step));
                }
            }
        }
    }

    /** 표면에 닿은 핏방울 → 혈흔. 비스듬히 닿을수록 날아가던 쪽으로 길게 늘어짐 */
    private void splat(Arena a, Vec3 point, Vec3 normal, Vec3 vel, float size) {
        Vec3 n = normal.normalize();
        Vec3 tang = vel.sub(n.mul(vel.dot(n)));
        double speed = Math.max(1e-4, vel.length());
        double glance = Math.min(1.0, tang.length() / speed);
        float stretch = (float) (1.0 + glance * glance * 2.4);
        String model = "violence:fx/blood_splat_" + rnd.nextInt(SHAPES);
        Vec3 along = tang.lengthSq() < 1e-6 ? null : tang.normalize();
        ItemDisplay d = decal(a, point, n, along, model, size * stretch, size, SPLAT_LIFE);
        if (d == null || along == null) return;
        // 부딪힌 점이 혈흔의 머리(뭉친 쪽)에 오도록 진행 방향으로 조금 밀어 놓음
        Transformation t = d.getTransformation();
        Vector3f shift = new Vector3f((float) along.x(), (float) along.y(), (float) along.z()).mul(size * stretch * 0.28f);
        d.setTransformation(new Transformation(shift, t.getLeftRotation(), t.getScale(), t.getRightRotation()));
    }

    /**
     * 면에 붙는 판 (+y 가 법선). along 이 있으면 판의 +x 를 그쪽으로(늘어나는 방향), 없으면 아무 방향.
     * life 틱 뒤 투명도 단계를 올리며 사라진다.
     */
    private ItemDisplay decal(Arena a, Vec3 point, Vec3 normal, Vec3 along, String model, float sx, float sz, int life) {
        Vec3 n = normal.normalize();
        Vec3 at = point.add(n.mul(0.011 + rnd.nextDouble() * 0.008));
        Vector3f ny = new Vector3f((float) n.x(), (float) n.y(), (float) n.z());
        Vector3f nx;
        if (along != null) nx = new Vector3f((float) along.x(), (float) along.y(), (float) along.z());
        else {
            Vector3f ref = Math.abs(ny.y) > 0.9f ? new Vector3f(1, 0, 0) : new Vector3f(0, 1, 0);
            nx = ref.cross(ny, new Vector3f()).normalize();
            nx.rotateAxis(rnd.nextFloat() * 6.283f, ny.x, ny.y, ny.z);
        }
        nx.sub(new Vector3f(ny).mul(nx.dot(ny))).normalize();
        Vector3f nz = new Vector3f(nx).cross(ny).normalize();
        Quaternionf q = new Quaternionf().setFromNormalized(new org.joml.Matrix3f(nx, ny, nz));
        ItemDisplay d;
        try {
            d = a.track(a.world.spawn(Fx.loc(a.world, at), ItemDisplay.class, e -> {
                e.setPersistent(false);
                e.setItemStack(item(model, 0));
                e.setTransformation(new Transformation(new Vector3f(), q, new Vector3f(sx, 1, sz), new Quaternionf()));
                e.setViewRange(1.5f);
                e.setShadowRadius(0);
            }));
        } catch (RuntimeException ex) {
            return null;
        }
        decals.addLast(new Decal(a, d, model, plugin.now() + life));
        while (decals.size() > maxDecals) {
            Decal old = decals.pollFirst();
            if (old != null) {
                old.arena.tracked.remove(old.display);
                if (old.display.isValid()) old.display.remove();
            }
        }
        return d;
    }

    private static ItemStack item(String model, int step) {
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key(model));
        it.setData(DataComponentTypes.CUSTOM_MODEL_DATA, CustomModelData.customModelData().addFloat(step).build());
        return it;
    }

    private static Vec3 floorBelow(Arena a, Vec3 from, double max) {
        RayTraceResult down = a.world.rayTraceBlocks(Fx.loc(a.world, from), new Vector(0, -1, 0), max, FluidCollisionMode.NEVER, true);
        if (down == null) return null;
        Vector hp = down.getHitPosition();
        return new Vec3(hp.getX(), hp.getY(), hp.getZ());
    }

    public void clear() {
        drops.clear();
        decals.clear();
    }

    /** 테스트/미리보기용: 늘어남 비율 (비스듬함 0~1) */
    public static double stretchFor(double glance) {
        return 1.0 + glance * glance * 2.4;
    }
}
