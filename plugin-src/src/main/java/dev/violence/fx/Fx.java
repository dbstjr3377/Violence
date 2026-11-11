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
    /**
     * 탄 궤적: 총구에서 4블록 줄기로 나타나(1틱) 2틱 동안 맞은 곳까지 날아가며 가늘어지고 사라짐.
     * 쏜 사람 시선과 거의 같은 방향이라 너무 가늘면 안 보이므로 굵게, 낮은 프레임에서도 보이게 4틱 동안 남김.
     */
    public void tracer(Arena a, Vec3 from, Vec3 to, String color) {
        Vec3 diff = to.sub(from);
        double len = diff.length();
        if (len < 0.5) return;
        Vec3 dir = diff.mul(1 / len);
        String model = "orange".equals(color) ? "violence:fx/tracer_orange" : "violence:fx/tracer";
        float width = "orange".equals(color) ? 0.07f : 0.055f;
        double streak = Math.min(len, 4.0);
        ItemDisplay d = spawnDisplay(a, from, model, true);
        d.setViewRange(4.0f);
        d.setTransformation(segment(dir, 0.15, streak - 0.15, width));
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(2);
            double tail = Math.min(1.6, len);
            d.setTransformation(segment(dir, len - tail, tail, width * 0.5f));
        });
        removeLater(a, d, 4);
    }

    /**
     * 총구 화염: 3인칭 총구 자리에 한 틱만 보였다가 사라짐 (작아지는 전환 없음).
     * 쏜 사람에게는 숨김: 1인칭 손 모델은 화면 FOV 와 상관없는 고정 시야로 그려져 월드에 놓은 판으로는 총구에 맞출 수 없으므로,
     * 쏜 사람의 화염은 1인칭 총 모델의 화염 프레임(쏜 뒤 정확히 1틱, tools/build_pack.py)이 총구에 붙어 나온다.
     * @param big 산탄총 등 큰 화염
     */
    public void muzzle(Arena a, Vec3 at, Vec3 dir, boolean silenced, boolean big, org.bukkit.entity.Player shooter) {
        ItemDisplay d = spawnDisplay(a, at, silenced ? "violence:fx/muzzle_small" : "violence:fx/muzzle", true);
        d.setBillboard(Display.Billboard.CENTER);
        d.setViewRange(4.0f);
        float s = silenced ? 0.22f : (big ? 0.62f : 0.42f) + rnd.nextFloat() * 0.12f;
        d.setTransformation(new Transformation(new Vector3f(), new Quaternionf().rotateZ(rnd.nextFloat() * 6.28f), new Vector3f(s, s, s), new Quaternionf()));
        if (shooter != null) shooter.hideEntity(plugin, d);
        removeLater(a, d, 1);
    }

    public void muzzle(Arena a, Vec3 at, Vec3 dir, boolean silenced, boolean big) {
        muzzle(a, at, dir, silenced, big, null);
    }

    /**
     * 근접 휘두르기 궤적: 눈앞에서 하얀 호가 베는 방향으로 쓸고 지나간다.
     * @param leftToRight false = 오른쪽 → 왼쪽, true = 왼쪽 → 오른쪽 (좌우 반전)
     */
    public void slash(Arena a, Vec3 eye, Vec3 dir, boolean leftToRight, float size) {
        Vec3 d = dir.normalize();
        Vec3 at = eye.add(d.mul(1.0 * size)).add(0, -0.1 * size, 0);
        ItemDisplay e = spawnDisplay(a, at, "violence:fx/slash", true);
        e.setViewRange(1.0f);
        float yaw = (float) Math.toRadians(d.yaw());
        float pitch = (float) Math.toRadians(d.pitch());
        // 판의 법선을 시선 방향에 맞추고, 베는 끝(왼쪽 아래)으로 살짝 기울임
        Quaternionf face = new Quaternionf().rotateY(-yaw).rotateX(pitch).rotateZ(-0.22f);
        float mirror = leftToRight ? -1f : 1f;
        // 표시 엔티티 기준 +x 가 보는 사람의 왼쪽 → 오→왼 은 -x 에서 +x 로 이동
        float w = 1.7f * size, h = 1.0f * size;
        e.setTransformation(new Transformation(rotate(face, -0.35f * mirror * size, 0.05f * size), face,
                new Vector3f(w * 0.45f * mirror, h * 0.8f, 1f), new Quaternionf()));
        plugin.later(1, () -> {
            if (!e.isValid()) return;
            e.setInterpolationDelay(0);
            e.setInterpolationDuration(3);
            e.setTransformation(new Transformation(rotate(face, 0.3f * mirror * size, -0.08f * size), face,
                    new Vector3f(w * mirror, h, 1f), new Quaternionf()));
        });
        removeLater(a, e, 5);
    }

    /** 판 기준 좌표 (x, y) 를 월드 방향 이동량으로 */
    private static Vector3f rotate(Quaternionf q, float x, float y) {
        return q.transform(new Vector3f(x, y, 0));
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
     * 피 튀김: 핏방울이 공격 방향으로 날아가 바닥과 벽에 혈흔을 남긴다 (BloodService).
     * @param intensity 1(약) ~ 4(처형/헤드샷)
     */
    public void blood(Arena a, Vec3 point, Vec3 dir, int intensity) {
        plugin.blood().spray(a, point, dir, intensity);
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

    /** 시체 피 웅덩이 (맞은 부위 밑, 시체에 붙임) */
    public void bloodPool(Arena a, Vec3 at, float size, org.bukkit.entity.Entity body) {
        plugin.blood().pool(a, at, size, body);
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
