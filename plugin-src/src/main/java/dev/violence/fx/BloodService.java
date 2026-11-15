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
 * 혈흔은 면의 방향에 맞춰 눕거나 서고, 상황에 따라 모양이 다르다 (한 가지 빨강, 굵은 픽셀 그림):
 *  - 바닥에 곧게 떨어짐: 둥근 얼룩 + 왕관처럼 튄 방울 (splat)
 *  - 비스듬히 닿음: 날아가던 쪽으로 넓게 퍼짐 (streak)
 *  - 벽: 아래로 흘러내리는 줄기 (drip)
 *  - 작은 방울: 점 몇 개 (drops)
 *  - 강한 공격(헤드샷·처형·샷건)의 첫 방울: 부채꼴로 흩뿌림 (spray)
 * 5초 뒤 6단계 투명도 모델로 바꿔 가며 서서히 사라진다 (custom_model_data 0 = 투명도 단계).
 * 처형당한 시체는 머리에서 바닥으로 피가 천천히 흘러 퍼진다 (fx/blood_flow).
 */
public final class BloodService {
    /** 상황별 혈흔 모양과 개수 (리소스팩 fx/blood_<모양>_<번호>) */
    private static final java.util.Map<String, Integer> SHAPES = java.util.Map.of("splat", 3, "streak", 3, "drip", 3, "drops", 2, "spray", 2);
    public static final int FADE_STEPS = 6;
    private static final double GRAVITY = 0.045;
    private static final int SPLAT_LIFE = 200;     // 10초
    /** 핏방울 궤적을 계산하는 최대 틱 (그 안에 아무 데도 닿지 않으면 혈흔 없음) */
    private static final int DROP_MAX_TICKS = 50;
    /** 혈흔이 퍼지는 애니메이션: 프레임 3장 (custom_model_data 10~12) 뒤 완성 그림(0), 프레임마다 틱 */
    private static final int SPLAT_ANIM_FRAMES = 3;
    private static final int SPLAT_ANIM_TICKS = 2;
    /** 피 웅덩이가 커지는 시간 (틱, 6초) */
    public static final int POOL_GROW_TICKS = 120;
    private static final int FADE_STEP_TICKS = 4;

    private final ViolencePlugin plugin;
    private final Random rnd = new Random();
    private final Deque<Decal> decals = new ArrayDeque<>();
    private int maxDecals = 180;

    private static final class Drop {
        final Arena arena;
        Vec3 pos;
        Vec3 vel;
        final float size;
        final boolean burst;

        Drop(Arena arena, Vec3 pos, Vec3 vel, float size, boolean burst) {
            this.arena = arena;
            this.pos = pos;
            this.vel = vel;
            this.size = size;
            this.burst = burst;
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
        spray(a, point, dir, intensity, 1.0);
    }

    /** reach: 날아가는 거리 배율 (1 = 보통, 작을수록 가까이 떨어짐) */
    public void spray(Arena a, Vec3 point, Vec3 dir, int intensity, double reach) {
        Vec3 bias = dir.lengthSq() < 1e-6 ? Vec3.UP : dir.normalize();
        int n = Math.max(2, (5 + intensity * 4) / 2);   // 피 효과 0.5배
        for (int i = 0; i < n; i++) {
            Vec3 r = new Vec3(rnd.nextGaussian(), rnd.nextGaussian() * 0.6, rnd.nextGaussian()).normalize();
            Vec3 d = bias.mul(1.4 + intensity * 0.2).add(r).add(0, 0.25, 0).normalize();
            double speed = (0.18 + rnd.nextDouble() * (0.18 + intensity * 0.06)) * reach;
            float size = 0.22f + rnd.nextFloat() * (0.22f + intensity * 0.07f);
            boolean burst = intensity >= 3 && i < 2;
            addDrop(new Drop(a, point.add(r.mul(0.05)), d.mul(burst ? speed * 1.4 : speed), burst ? Math.max(size, 0.4f) : size, burst));
        }
    }

    /**
     * 두 갈래 흩뿌림 (둔기·가벼운 무기 처형, 맨손은 세 번 동시에): 머리에서 사이각 22~30° 인 두 방향을 정해
     * 한 방향으로 길게, 다른 방향으로 0.7 만큼 핏방울을 좁게 흩뿌림. 방향은 위쪽으로 20~40° 들림.
     */
    public void twinSpray(Arena a, Vec3 head, int intensity) {
        double az = rnd.nextDouble() * Math.PI * 2;
        double gap = Math.toRadians(22 + rnd.nextDouble() * 8) * (rnd.nextBoolean() ? 1 : -1);
        int n = Math.max(2, (2 + intensity * 2) / 2 + 1);
        fan(a, head, az, n, 1.0);
        fan(a, head, az + gap, Math.max(2, (int) Math.round(n * 0.7)), 0.7);
    }

    private void fan(Arena a, Vec3 head, double az, int n, double reach) {
        double el = Math.toRadians(20 + rnd.nextDouble() * 20);
        Vec3 d0 = new Vec3(Math.cos(az) * Math.cos(el), Math.sin(el), Math.sin(az) * Math.cos(el));
        for (int i = 0; i < n; i++) {
            Vec3 d = d0.add(new Vec3(rnd.nextGaussian(), rnd.nextGaussian(), rnd.nextGaussian()).mul(0.09)).normalize();
            // 앞쪽 핏방울일수록 멀리 (줄지어 흩뿌려짐)
            double speed = (0.13 + 0.17 * (i + 1) / n + rnd.nextDouble() * 0.04) * reach;
            float size = 0.2f + rnd.nextFloat() * 0.18f;
            addDrop(new Drop(a, head.add(d.mul(0.05)), d.mul(speed), size, false));
        }
    }

    /** 상처에서 떨어지는 핏방울 하나 (거의 제자리에서 떨어져 바닥에 작은 혈흔) */
    public void drip(Arena a, Vec3 at) {
        Vec3 v = new Vec3(rnd.nextGaussian() * 0.012, -0.02, rnd.nextGaussian() * 0.012);
        addDrop(new Drop(a, at, v, 0.16f + rnd.nextFloat() * 0.08f, false));
    }

    /**
     * 살아남은 몸의 상처에서 핏방울이 몇 번 떨어짐 (총알 자국): 맞은 자리를 몸 기준으로 기억해 움직이는 몸을 따라감.
     */
    public void bleedFrom(Arena a, dev.violence.combat.Combatant v, Vec3 point, int drops) {
        Vec3 d = point.sub(v.feet());
        org.joml.Vector3d local = FallPose.toWorld(new org.joml.Vector3d(d.x(), d.y(), d.z()), -v.yaw());
        for (int i = 0; i < drops; i++) {
            plugin.laterIn(a, 6 + i * (10 + rnd.nextInt(8)), () -> {
                if (!v.isAlive() || v.entity() == null || !v.entity().isValid() || v.state.isDownedLike()) return;
                org.joml.Vector3d w = FallPose.toWorld(new org.joml.Vector3d(local), v.yaw());
                drip(a, v.feet().add(w.x, w.y, w.z));
            });
        }
    }

    /**
     * 핏방울: 날아가는 개체 없이 궤적(중력·공기 저항, 예전 핏방울과 같은 식)을 튀는 순간 끝까지 계산해
     * 닿을 자리에 바로(맞은 틱에) 혈흔을 붙인다 (혈흔은 4프레임 동안 퍼지는 애니메이션).
     */
    private void addDrop(Drop d) {
        World w = d.arena.world;
        Vec3 pos = d.pos;
        Vec3 vel = d.vel;
        for (int age = 1; age <= DROP_MAX_TICKS; age++) {
            double len = vel.length();
            if (len > 1e-4) {
                RayTraceResult r = w.rayTraceBlocks(Fx.loc(w, pos), new Vector(vel.x(), vel.y(), vel.z()), len, FluidCollisionMode.NEVER, true);
                if (r != null && r.getHitBlockFace() != null) {
                    Vector hp = r.getHitPosition();
                    Vector fn = r.getHitBlockFace().getDirection();
                    Vec3 at = new Vec3(hp.getX(), hp.getY(), hp.getZ());
                    Vec3 n = new Vec3(fn.getX(), fn.getY(), fn.getZ());
                    splat(d.arena, at, n, vel, d.size, d.burst);
                    return;
                }
            }
            pos = pos.add(vel);
            vel = vel.mul(0.98).add(0, -GRAVITY, 0);
        }
    }

    /**
     * 시체의 피 웅덩이: 맞은 부위(at, 처형이면 머리) 밑 바닥에서 6초에 걸쳐 커짐 (완성 그림 1장을 작게 시작해 크기 보간).
     * 시체(body)에 태워서 붙이므로 시체가 사라지면 함께 사라짐 (시체가 없으면 그 자리에 18초).
     */
    public void pool(Arena a, Vec3 at, float size0, org.bukkit.entity.Entity body) {
        float size = size0 * 1.8f;   // 웅덩이 1.8배
        Vec3 floor = floorBelow(a, at.add(0, 0.5, 0), 3);
        if (floor == null) return;
        // 다 퍼진 크기에 맞춘 그림 (리소스팩 build_pack.POOL_SIZES)
        String model = size0 > 1.35f ? "violence:fx/blood_pool_l" : "violence:fx/blood_pool_s";
        ItemDisplay d = decal(a, floor, Vec3.UP, null, model, size, size, 18 * 20);
        if (d == null) return;
        Transformation full = d.getTransformation();
        boolean attach = body != null && body.isValid();
        if (attach) {
            decals.removeIf(c -> c.display == d);   // 시체와 함께 사라짐 (따로 흐려지지 않음)
            body.addPassenger(d);
        }
        // 처음엔 안 보이게 → 다음 틱에 (태운 자리에서 웅덩이 자리까지 옮긴 뒤) 작게 → 6초에 걸쳐 다 퍼진 크기로
        d.setTransformation(new Transformation(new Vector3f(), full.getLeftRotation(), new Vector3f(0.001f, 1, 0.001f), full.getRightRotation()));
        Vec3 target = floor.add(0, 0.012, 0);
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            org.bukkit.Location dl = d.getLocation();
            Vector3f off = attach ? new Vector3f((float) (target.x() - dl.getX()), (float) (target.y() - dl.getY()), (float) (target.z() - dl.getZ()))
                    : new Vector3f();
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(0);
            d.setTransformation(new Transformation(new Vector3f(off), full.getLeftRotation(), new Vector3f(size * 0.12f, 1, size * 0.12f), full.getRightRotation()));
            plugin.later(1, () -> {
                if (!d.isValid()) return;
                d.setInterpolationDelay(0);
                d.setInterpolationDuration(POOL_GROW_TICKS);
                d.setTransformation(new Transformation(new Vector3f(off), full.getLeftRotation(), full.getScale(), full.getRightRotation()));
            });
        });
    }

    /**
     * 시체 몸 위의 상처 혈흔: 면(normal)에 붙여 시체에 태움 → 시체와 함께 사라짐 (따로 흐려지지 않음).
     * 태운 자리와 실제 자리의 차이는 다음 틱에 변환으로 메움 (그동안은 거의 안 보이게).
     */
    public void bodyDecal(Arena a, Vec3 at, Vec3 normal, Vec3 along, String model, float size, org.bukkit.entity.Entity body) {
        ItemDisplay d = decal(a, at, normal, along, model, size, size, 20 * 60);
        if (d == null) return;
        if (body == null || !body.isValid()) return;
        decals.removeIf(c -> c.display == d);
        Transformation full = d.getTransformation();
        org.bukkit.Location spawned = d.getLocation();
        d.setTransformation(new Transformation(full.getTranslation(), full.getLeftRotation(), new Vector3f(0.001f, 1, 0.001f), full.getRightRotation()));
        body.addPassenger(d);
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            org.bukkit.Location dl = d.getLocation();
            Vector3f off = new Vector3f((float) (spawned.getX() - dl.getX()), (float) (spawned.getY() - dl.getY()), (float) (spawned.getZ() - dl.getZ()))
                    .add(full.getTranslation());
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(0);
            d.setTransformation(new Transformation(off, full.getLeftRotation(), full.getScale(), full.getRightRotation()));
        });
    }

    /** 처형: 머리·목 밑 바닥에 바로 혈흔 (모양: 둥근 얼룩, 크면 흩뿌림을 하나 더) */
    public void floorSplat(Arena a, Vec3 at, float size) {
        Vec3 floor = floorBelow(a, at.add(0, 0.4, 0), 2.0);
        if (floor == null) return;
        decal(a, floor, Vec3.UP, null, "violence:fx/blood_splat_" + rnd.nextInt(SHAPES.get("splat")), size, size, SPLAT_LIFE + 60, 0, true);
        if (size >= 0.7f) {
            decal(a, floor, Vec3.UP, null, "violence:fx/blood_spray_" + rnd.nextInt(SHAPES.get("spray")), size * 1.8f, size * 1.4f, SPLAT_LIFE + 60, 0, true);
        }
    }

    /** 비스듬히 닿은 혈흔 크기 [길이, 폭]: 넓게 퍼짐 (길이 ÷ 폭 ≤ 1.75, 가늘고 길게 늘이지 않음) */
    public static float[] streakSize(float size, double glance) {
        float stretch = (float) (1.0 + Math.min(1.0, glance) * 0.45);
        return new float[] {size * 1.6f * stretch, size * 1.35f};
    }

    /** 동맥: from 에서 dir 쪽으로 ticks 동안 맥박치듯 뿜어져 나옴 (날붙이 처형) */
    public void jet(Arena a, Vec3 from, Vec3 dir, int ticks) {
        Vec3 d = dir.normalize();
        for (int t = 0; t < ticks; t++) {
            final int k = t;
            plugin.laterIn(a, t, () -> {
                double pulse = (k % 4 < 2 ? 1.0 : 0.55) * (1.0 - k / (double) (ticks + 4));
                for (int i = 0; i < 1; i++) {   // 피 효과 0.5배 (틱마다 2 → 1방울)
                    Vec3 r = new Vec3(rnd.nextGaussian(), rnd.nextGaussian(), rnd.nextGaussian()).mul(0.12);
                    Vec3 v = d.add(r).normalize().mul(0.16 + 0.14 * pulse);
                    addDrop(new Drop(a, from, v, 0.24f + rnd.nextFloat() * 0.12f, false));
                }
            });
        }
    }

    public void tick() {
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

    /** 표면에 닿은 핏방울 → 상황에 맞는 모양의 혈흔 */
    private void splat(Arena a, Vec3 point, Vec3 normal, Vec3 vel, float size, boolean burst) {
        Vec3 n = normal.normalize();
        Vec3 tang = vel.sub(n.mul(vel.dot(n)));
        double speed = Math.max(1e-4, vel.length());
        double glance = Math.min(1.0, tang.length() / speed);
        boolean wall = Math.abs(n.y()) < 0.7;
        Vec3 along = tang.lengthSq() < 1e-6 ? null : tang.normalize();
        String shape;
        float sx;
        float sz;
        double head;      // 부딪힌 점을 그림의 어느 쪽에 둘지 (+x 방향으로 밀기, 판 길이 비율)
        if (burst) {
            shape = "spray";
            sx = size * 2.2f;
            sz = size * 1.7f;
            head = 0.36;
        } else if (size < 0.27f) {
            shape = "drops";
            along = null;
            sx = sz = size * 1.4f;
            head = 0;
        } else if (wall && glance < 0.6) {
            // 벽: 판의 +x 를 아래로 → 줄기가 흘러내림
            Vec3 down = new Vec3(0, -1, 0);
            along = down.sub(n.mul(down.dot(n))).normalize();
            shape = "drip";
            sx = size * 1.7f;
            sz = size * 1.1f;
            head = 0.24;
        } else if (glance >= 0.45 && along != null) {
            // 넓게 퍼짐 (가늘고 길게 늘이지 않음)
            shape = "streak";
            float[] wh = streakSize(size, glance);
            sx = wh[0];
            sz = wh[1];
            head = 0.26;
        } else {
            shape = "splat";
            along = null;
            sx = sz = size * 1.25f;
            head = 0;
        }
        String model = "violence:fx/blood_" + shape + "_" + rnd.nextInt(SHAPES.get(shape));
        ItemDisplay d = decal(a, point, n, along, model, sx, sz, SPLAT_LIFE, 0, true);
        if (d == null || along == null || head == 0) return;
        Transformation t = d.getTransformation();
        Vector3f shift = new Vector3f((float) along.x(), (float) along.y(), (float) along.z()).mul((float) (sx * head));
        d.setTransformation(new Transformation(shift, t.getLeftRotation(), t.getScale(), t.getRightRotation()));
    }

    /**
     * 면에 붙는 판 (+y 가 법선). along 이 있으면 판의 +x 를 그쪽으로(늘어나는 방향), 없으면 아무 방향.
     * life 틱 뒤 투명도 단계를 올리며 사라진다.
     */
    private ItemDisplay decal(Arena a, Vec3 point, Vec3 normal, Vec3 along, String model, float sx, float sz, int life) {
        return decal(a, point, normal, along, model, sx, sz, life, 0, false);
    }

    /**
     * step: 처음 보일 그림 번호 (custom_model_data). animate: 튄 피 혈흔이 퍼지는 4프레임 애니메이션 (10, 11, 12 → 완성 0)
     */
    private ItemDisplay decal(Arena a, Vec3 point, Vec3 normal, Vec3 along, String model, float sx, float sz, int life,
                              int step0, boolean animate) {
        final int first = animate ? 10 : step0;
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
                e.setItemStack(item(model, first));
                e.setTransformation(new Transformation(new Vector3f(), q, new Vector3f(sx, 1, sz), new Quaternionf()));
                e.setViewRange(1.5f);
                e.setShadowRadius(0);
            }));
        } catch (RuntimeException ex) {
            return null;
        }
        if (animate) {
            for (int k = 1; k <= SPLAT_ANIM_FRAMES; k++) {
                final int step = k < SPLAT_ANIM_FRAMES ? 10 + k : 0;
                plugin.laterIn(a, k * SPLAT_ANIM_TICKS, () -> {
                    if (d.isValid()) d.setItemStack(item(model, step));
                });
            }
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
        decals.clear();
    }

}
