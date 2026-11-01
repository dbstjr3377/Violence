package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.math.Vec3;
import io.papermc.paper.datacomponent.DataComponentTypes;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Random;
import net.kyori.adventure.key.Key;
import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.SoundCategory;
import org.bukkit.World;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.inventory.ItemStack;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 시각 효과. 바닐라 파티클을 쓰지 않고 리소스팩 모델을 씌운 디스플레이 엔티티로 표현한다.
 * (탄환 궤적, 총구 화염, 피 튀김/혈흔, 유리 파편, 탄흔)
 */
public final class Fx {
    private static final Display.Brightness FULL = new Display.Brightness(15, 15);
    private final ViolencePlugin plugin;
    private final Random rnd = new Random();
    private final Deque<Entity> decals = new ArrayDeque<>();
    private int maxDecals = 450;

    public Fx(ViolencePlugin plugin) {
        this.plugin = plugin;
        this.maxDecals = plugin.getConfig().getInt("fx.max-decals", 450);
    }

    public static ItemStack model(String model) {
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key(model));
        return it;
    }

    public static Location loc(World w, Vec3 v) {
        return new Location(w, v.x(), v.y(), v.z());
    }

    private ItemDisplay spawnDisplay(Arena a, Vec3 at, String model, boolean bright) {
        return a.track(a.world.spawn(loc(a.world, at), ItemDisplay.class, d -> {
            d.setItemStack(model(model));
            d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
            d.setPersistent(false);
            d.setViewRange(3.0f);
            d.setShadowRadius(0);
            if (bright) d.setBrightness(FULL);
        }));
    }

    private void removeLater(Arena a, Entity e, int ticks) {
        plugin.later(ticks, () -> {
            a.tracked.remove(e);
            if (e.isValid()) e.remove();
        });
    }

    private static Quaternionf align(Vector3f from, Vec3 to) {
        return new Quaternionf().rotationTo(from, new Vector3f((float) to.x(), (float) to.y(), (float) to.z()).normalize());
    }

    private static Transformation segment(Vec3 dir, double start, double length, float width) {
        Quaternionf q = align(new Vector3f(0, 0, 1), dir);
        double mid = start + length / 2;
        Vector3f t = new Vector3f((float) (dir.x() * mid), (float) (dir.y() * mid), (float) (dir.z() * mid));
        return new Transformation(t, q, new Vector3f(width, width, (float) Math.max(0.01, length)), new Quaternionf());
    }

    /** 총알 궤적: 노란(매그넘은 주황) 선이 총알처럼 빠르게 날아간다. */
    public void tracer(Arena a, Vec3 from, Vec3 to, String color) {
        Vec3 diff = to.sub(from);
        double len = diff.length();
        if (len < 0.5) return;
        Vec3 dir = diff.mul(1 / len);
        String model = "orange".equals(color) ? "violence:fx/tracer_orange" : "violence:fx/tracer";
        float width = "orange".equals(color) ? 0.05f : 0.035f;
        double streak = Math.min(len, 3.0);
        ItemDisplay d = spawnDisplay(a, from, model, true);
        d.setTransformation(segment(dir, 0, streak, width));
        int travel = (int) Math.max(1, Math.ceil(len / 45.0));
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(travel);
            double tail = Math.min(1.2, len);
            d.setTransformation(segment(dir, len - tail, tail, width * 0.6f));
        });
        removeLater(a, d, travel + 2);
    }

    public void muzzle(Arena a, Vec3 eye, Vec3 dir, boolean silenced) {
        Vec3 right = dir.cross(Vec3.UP).normalize();
        Vec3 at = eye.add(dir.mul(0.85)).add(right.mul(0.22)).add(0, -0.18, 0);
        ItemDisplay d = spawnDisplay(a, at, silenced ? "violence:fx/muzzle_small" : "violence:fx/muzzle", true);
        d.setBillboard(Display.Billboard.CENTER);
        float s = silenced ? 0.25f : 0.45f + rnd.nextFloat() * 0.2f;
        d.setTransformation(new Transformation(new Vector3f(), new Quaternionf().rotateZ(rnd.nextFloat() * 6.28f), new Vector3f(s, s, s), new Quaternionf()));
        removeLater(a, d, 2);
    }

    /** 표면에 납작하게 붙는 데칼 (혈흔, 탄흔) */
    public void decal(Arena a, Vec3 point, Vec3 normal, String model, float scale) {
        Vec3 n = normal.normalize();
        Vec3 at = point.add(n.mul(0.012 + rnd.nextDouble() * 0.006));
        ItemDisplay d = spawnDisplay(a, at, model, false);
        Quaternionf q = align(new Vector3f(0, 1, 0), n).rotateY(rnd.nextFloat() * 6.28f);
        d.setTransformation(new Transformation(new Vector3f(), q, new Vector3f(scale, scale, scale), new Quaternionf()));
        d.setViewRange(1.5f);
        decals.addLast(d);
        while (decals.size() > maxDecals) {
            Entity old = decals.pollFirst();
            if (old != null) {
                a.tracked.remove(old);
                if (old.isValid()) old.remove();
            }
        }
    }

    private Vec3 randomDir(Vec3 bias, double biasWeight) {
        Vec3 r = new Vec3(rnd.nextGaussian(), rnd.nextGaussian() * 0.6, rnd.nextGaussian()).normalize();
        return r.add(bias.mul(biasWeight)).normalize();
    }

    /**
     * 피 튀김. 공격 방향으로 핏방울이 날아가 바닥과 벽에 혈흔을 남긴다.
     * @param intensity 1(약) ~ 4(처형/헤드샷)
     */
    public void blood(Arena a, Vec3 point, Vec3 dir, int intensity) {
        World w = a.world;
        int drops = 3 + intensity * 3;
        Vec3 bias = dir.normalize();
        for (int i = 0; i < drops; i++) {
            Vec3 d = randomDir(bias.add(0, -0.35, 0), 1.2 + intensity * 0.2);
            double range = 1.5 + rnd.nextDouble() * (1.5 + intensity);
            RayTraceResult r = w.rayTraceBlocks(loc(w, point), new Vector(d.x(), d.y(), d.z()), range, FluidCollisionMode.NEVER, true);
            Vec3 end;
            Vec3 normal;
            if (r != null && r.getHitBlockFace() != null) {
                Vector hp = r.getHitPosition();
                end = new Vec3(hp.getX(), hp.getY(), hp.getZ());
                Vector fn = r.getHitBlockFace().getDirection();
                normal = new Vec3(fn.getX(), fn.getY(), fn.getZ());
            } else {
                // 허공 → 바로 아래 바닥으로
                Vec3 mid = point.add(d.mul(range));
                RayTraceResult down = w.rayTraceBlocks(loc(w, mid), new Vector(0, -1, 0), 4, FluidCollisionMode.NEVER, true);
                if (down == null) continue;
                Vector hp = down.getHitPosition();
                end = new Vec3(hp.getX(), hp.getY(), hp.getZ());
                normal = Vec3.UP;
            }
            flyDrop(a, point, end, normal, intensity);
        }
        // 맞은 지점의 핏덩이 (짧게 퍼지며 사라짐)
        ItemDisplay mist = spawnDisplay(a, point, "violence:fx/blood_mist", false);
        mist.setBillboard(Display.Billboard.CENTER);
        float s0 = 0.25f + intensity * 0.08f;
        mist.setTransformation(new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(s0, s0, s0), new Quaternionf()));
        plugin.later(1, () -> {
            if (!mist.isValid()) return;
            mist.setInterpolationDelay(0);
            mist.setInterpolationDuration(5);
            float s1 = s0 * 2.4f;
            mist.setTransformation(new Transformation(new Vector3f(0, -0.15f, 0), new Quaternionf(), new Vector3f(s1, 0.01f, s1), new Quaternionf()));
        });
        removeLater(a, mist, 7);
    }

    private void flyDrop(Arena a, Vec3 from, Vec3 to, Vec3 normal, int intensity) {
        ItemDisplay drop = spawnDisplay(a, from, "violence:fx/blood_drop", false);
        float s = 0.08f + rnd.nextFloat() * 0.08f;
        drop.setTransformation(new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(s, s, s), new Quaternionf()));
        int travel = 2 + (int) Math.min(5, from.distance(to) / 1.2);
        drop.setTeleportDuration(travel);
        plugin.later(1, () -> {
            if (drop.isValid()) drop.teleport(loc(a.world, to));
        });
        plugin.later(travel + 1, () -> {
            a.tracked.remove(drop);
            if (drop.isValid()) drop.remove();
            String m = "violence:fx/blood_decal_" + rnd.nextInt(4);
            decal(a, to, normal, m, 0.35f + rnd.nextFloat() * (0.35f + intensity * 0.18f));
        });
    }

    /** 시체 밑 피 웅덩이 */
    public void bloodPool(Arena a, Vec3 feet, float size) {
        RayTraceResult down = a.world.rayTraceBlocks(loc(a.world, feet.add(0, 0.5, 0)), new Vector(0, -1, 0), 3, FluidCollisionMode.NEVER, true);
        if (down == null) return;
        Vector hp = down.getHitPosition();
        Vec3 p = new Vec3(hp.getX(), hp.getY(), hp.getZ());
        decal(a, p, Vec3.UP, "violence:fx/blood_pool", size);
    }

    /** 벽 탄흔 */
    public void bulletHole(Arena a, Vec3 point, Vec3 normal) {
        decal(a, point, normal, "violence:fx/bullet_hole", 0.12f + rnd.nextFloat() * 0.05f);
        ItemDisplay dust = spawnDisplay(a, point.add(normal.mul(0.05)), "violence:fx/impact", true);
        dust.setBillboard(Display.Billboard.CENTER);
        dust.setTransformation(new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(0.18f, 0.18f, 0.18f), new Quaternionf()));
        removeLater(a, dust, 2);
    }

    /** 유리 파편 */
    public void glassShards(Arena a, Vec3 center, Vec3 dir) {
        for (int i = 0; i < 7; i++) {
            ItemDisplay s = spawnDisplay(a, center.add(rnd.nextGaussian() * 0.25, rnd.nextGaussian() * 0.3, rnd.nextGaussian() * 0.25), "violence:fx/glass_shard", false);
            float sc = 0.12f + rnd.nextFloat() * 0.18f;
            s.setTransformation(new Transformation(new Vector3f(), new Quaternionf().rotateXYZ(rnd.nextFloat() * 6, rnd.nextFloat() * 6, rnd.nextFloat() * 6), new Vector3f(sc, sc, sc), new Quaternionf()));
            Vec3 d = randomDir(dir.normalize(), 1.0);
            Vec3 land = center.add(d.mul(0.8 + rnd.nextDouble() * 1.6));
            RayTraceResult down = a.world.rayTraceBlocks(loc(a.world, land), new Vector(0, -1, 0), 6, FluidCollisionMode.NEVER, true);
            Vec3 floor = land;
            if (down != null) {
                Vector hp = down.getHitPosition();
                floor = new Vec3(hp.getX(), hp.getY() + 0.02, hp.getZ());
            }
            Vec3 target = floor;
            s.setTeleportDuration(6);
            plugin.later(1, () -> {
                if (s.isValid()) s.teleport(loc(a.world, target));
            });
            removeLater(a, s, 60 + rnd.nextInt(40));
        }
    }

    public void sound(World w, Vec3 at, String key, float volume, float pitch) {
        w.playSound(loc(w, at), key, SoundCategory.PLAYERS, volume, pitch);
    }

    public void clear() {
        decals.clear();
    }
}
