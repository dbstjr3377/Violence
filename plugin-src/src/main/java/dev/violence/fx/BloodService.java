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
    /** 동시에 보이는 날아가는 핏방울 수 (넘으면 궤적만 계산) */
    private static final int MAX_VISIBLE_DROPS = 160;
    private int visibleDrops;
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
        final boolean burst;
        int age;
        /** 날아가는 동안 보이는 핏방울 (작은 붉은 상자), 없으면 null */
        ItemDisplay vis;

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
        int n = 5 + intensity * 4;
        for (int i = 0; i < n; i++) {
            Vec3 r = new Vec3(rnd.nextGaussian(), rnd.nextGaussian() * 0.6, rnd.nextGaussian()).normalize();
            Vec3 d = bias.mul(1.4 + intensity * 0.2).add(r).add(0, 0.25, 0).normalize();
            double speed = (0.18 + rnd.nextDouble() * (0.18 + intensity * 0.06)) * reach;
            float size = 0.22f + rnd.nextFloat() * (0.22f + intensity * 0.07f);
            boolean burst = intensity >= 3 && i < 2;
            addDrop(new Drop(a, point.add(r.mul(0.05)), d.mul(burst ? speed * 1.4 : speed), burst ? Math.max(size, 0.4f) : size, burst));
        }
    }

    /** 핏방울 추가: 날아가는 동안 작은 붉은 상자로 보임 (닿으면 혈흔으로 바뀜) */
    private void addDrop(Drop d) {
        drops.add(d);
        if (visibleDrops >= MAX_VISIBLE_DROPS) return;
        try {
            float s = 0.045f + d.size * 0.07f;
            d.vis = d.arena.track(d.arena.world.spawn(Fx.loc(d.arena.world, d.pos), ItemDisplay.class, e -> {
                e.setPersistent(false);
                e.setItemStack(item("violence:fx/blood_drop", 0));
                e.setTransformation(new Transformation(new Vector3f(-s / 2, -s / 2, -s / 2), new Quaternionf(), new Vector3f(s, s, s), new Quaternionf()));
                e.setTeleportDuration(1);
                e.setViewRange(1.0f);
                e.setShadowRadius(0);
            }));
            visibleDrops++;
        } catch (RuntimeException ex) {
            d.vis = null;
        }
    }

    private void dropGone(Drop d) {
        if (d.vis == null) return;
        visibleDrops--;
        d.arena.tracked.remove(d.vis);
        if (d.vis.isValid()) d.vis.remove();
        d.vis = null;
    }

    /**
     * 시체의 피 웅덩이: 맞은 부위(at, 처형이면 머리) 밑 바닥에서 2초에 걸쳐 퍼짐.
     * 시체(body)에 태워서 붙이므로 시체가 사라지면 함께 사라짐 (시체가 없으면 그 자리에 18초).
     */
    public void pool(Arena a, Vec3 at, float size, org.bukkit.entity.Entity body) {
        Vec3 floor = floorBelow(a, at.add(0, 0.5, 0), 3);
        if (floor == null) return;
        ItemDisplay d = decal(a, floor, Vec3.UP, null, "violence:fx/blood_pool", size, size, 18 * 20);
        if (d == null) return;
        Transformation full = d.getTransformation();
        boolean attach = body != null && body.isValid();
        if (attach) {
            decals.removeIf(c -> c.display == d);   // 시체와 함께 사라짐 (따로 흐려지지 않음)
            body.addPassenger(d);
        }
        // 처음엔 거의 안 보이게 → 다음 틱에 (태운 자리에서 웅덩이 자리까지 옮긴 뒤) 2초에 걸쳐 퍼짐
        d.setTransformation(new Transformation(new Vector3f(), full.getLeftRotation(), new Vector3f(0.001f, 1, 0.001f), full.getRightRotation()));
        Vec3 target = floor.add(0, 0.012, 0);
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            org.bukkit.Location dl = d.getLocation();
            Vector3f off = attach ? new Vector3f((float) (target.x() - dl.getX()), (float) (target.y() - dl.getY()), (float) (target.z() - dl.getZ()))
                    : new Vector3f();
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(0);
            d.setTransformation(new Transformation(new Vector3f(off), full.getLeftRotation(), new Vector3f(size * 0.3f, 1, size * 0.3f), full.getRightRotation()));
            plugin.later(1, () -> {
                if (!d.isValid()) return;
                d.setInterpolationDelay(0);
                d.setInterpolationDuration(40);
                d.setTransformation(new Transformation(new Vector3f(off), full.getLeftRotation(), full.getScale(), full.getRightRotation()));
            });
        });
    }

    /** 처형: 머리·목 밑 바닥에 바로 혈흔 (모양: 둥근 얼룩, 크면 흩뿌림을 하나 더) */
    public void floorSplat(Arena a, Vec3 at, float size) {
        Vec3 floor = floorBelow(a, at.add(0, 0.4, 0), 2.0);
        if (floor == null) return;
        decal(a, floor, Vec3.UP, null, "violence:fx/blood_splat_" + rnd.nextInt(SHAPES.get("splat")), size, size, SPLAT_LIFE + 60);
        if (size >= 0.7f) {
            decal(a, floor, Vec3.UP, null, "violence:fx/blood_spray_" + rnd.nextInt(SHAPES.get("spray")), size * 1.8f, size * 1.4f, SPLAT_LIFE + 60);
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
                for (int i = 0; i < 2; i++) {
                    Vec3 r = new Vec3(rnd.nextGaussian(), rnd.nextGaussian(), rnd.nextGaussian()).mul(0.12);
                    Vec3 v = d.add(r).normalize().mul(0.16 + 0.14 * pulse);
                    addDrop(new Drop(a, from, v, 0.24f + rnd.nextFloat() * 0.12f, false));
                }
            });
        }
    }

    public void tick() {
        if (!drops.isEmpty()) {
            for (Iterator<Drop> it = drops.iterator(); it.hasNext(); ) {
                Drop d = it.next();
                if (plugin.arena() != d.arena || ++d.age > 50) {
                    dropGone(d);
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
                        splat(d.arena, new Vec3(hp.getX(), hp.getY(), hp.getZ()), new Vec3(fn.getX(), fn.getY(), fn.getZ()), d.vel, d.size, d.burst);
                        dropGone(d);
                        it.remove();
                        continue;
                    }
                }
                d.pos = d.pos.add(d.vel);
                if (d.vis != null && d.vis.isValid()) d.vis.teleport(Fx.loc(w, d.pos));
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
        ItemDisplay d = decal(a, point, n, along, model, sx, sz, SPLAT_LIFE);
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
        for (Drop d : drops) dropGone(d);
        drops.clear();
        visibleDrops = 0;
        decals.clear();
    }

}
