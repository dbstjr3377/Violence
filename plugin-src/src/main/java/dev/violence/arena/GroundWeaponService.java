package dev.violence.arena;

import dev.violence.ViolencePlugin;
import dev.violence.combat.Combatant;
import dev.violence.fx.Fx;
import dev.violence.math.Vec3;
import dev.violence.player.PlayerCombatant;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponItems;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.UUID;
import org.bukkit.Color;
import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Player;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 바닥에 떨어진 무기 관리.
 * - 조준선에 있는 무기는 하얀 테두리로 빛남 (그 플레이어에게만)
 * - 겹친 경우 가장 최근에 떨어진 무기를 우선
 * - 탄이 없는 총은 5초 동안 줍지 않으면 사라짐
 */
public final class GroundWeaponService {
    public static final double PICK_RANGE = 3.2;
    public static final int EMPTY_GUN_LIFETIME = 100;

    private final ViolencePlugin plugin;

    public GroundWeaponService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    private static Transformation lyingTransform(float yaw, float scale) {
        // 모델의 fixed 표시 설정이 무기를 바닥에 눕힌다. 여기서는 방향(yaw)만 돌림
        Quaternionf q = new Quaternionf().rotateY((float) Math.toRadians(-yaw));
        return new Transformation(new Vector3f(0, 0.04f, 0), q, new Vector3f(scale, scale, scale), new Quaternionf());
    }

    public GroundWeapon spawn(Arena a, WeaponInstance w, Vec3 pos, float yaw) {
        if (w.vanishOnDrop()) return null;
        GroundWeapon g = new GroundWeapon(w, pos, plugin.now(), yaw);
        g.display = a.track(a.world.spawn(new Location(a.world, pos.x(), pos.y(), pos.z()), ItemDisplay.class, d -> {
            d.setItemStack(WeaponItems.create(w.type(), w.ammo()));
            d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.FIXED);
            d.setTransformation(lyingTransform(yaw, 0.75f));
            d.setPersistent(false);
            d.setViewRange(1.5f);
            d.setShadowRadius(0.25f);
            d.setShadowStrength(0.6f);
        }));
        a.groundWeapons.add(g);
        return g;
    }

    /** 개체가 서 있는 곳 근처 바닥에 무기를 떨어뜨림 (살짝 튕겨나가는 연출) */
    public GroundWeapon drop(Arena a, WeaponInstance w, Vec3 from, Vec3 push) {
        if (w == null || w.vanishOnDrop()) return null;
        Vec3 target = from.add(push.horizontal().mul(0.8)).add(plugin.random().nextGaussian() * 0.25, 0, plugin.random().nextGaussian() * 0.25);
        Vec3 floor = floorBelow(a, target.add(0, 0.8, 0));
        if (floor == null) floor = from;
        GroundWeapon g = spawn(a, w, from.add(0, 0.9, 0), plugin.random().nextFloat() * 360);
        if (g == null) return null;
        Vec3 land = floor;
        g.pos = land;
        g.display.setTeleportDuration(5);
        plugin.later(1, () -> {
            if (g.display.isValid()) g.display.teleport(new Location(a.world, land.x(), land.y(), land.z()));
        });
        return g;
    }

    public Vec3 floorBelow(Arena a, Vec3 p) {
        RayTraceResult r = a.world.rayTraceBlocks(new Location(a.world, p.x(), p.y(), p.z()), new Vector(0, -1, 0), 8, FluidCollisionMode.NEVER, true);
        if (r == null) return null;
        Vector hp = r.getHitPosition();
        return new Vec3(hp.getX(), hp.getY(), hp.getZ());
    }

    /** 바닥을 못 찾았을 때 (허공, 맵 밖): 가장 가까운 보행 칸 위 */
    public Vec3 reachableSpot(Arena a, Vec3 p) {
        Vec3 deep = null;
        RayTraceResult r = a.world.rayTraceBlocks(new Location(a.world, p.x(), p.y(), p.z()), new Vector(0, -1, 0), 64, FluidCollisionMode.NEVER, true);
        if (r != null && a.map.inBounds(p)) {
            Vector hp = r.getHitPosition();
            deep = new Vec3(hp.getX(), hp.getY(), hp.getZ());
        }
        if (deep != null) return deep;
        if (a.nav != null && a.nav.size() > 0) {
            var n = a.nav.nearest(p);
            if (n != null) return n.pos();
        }
        return null;
    }

    public void remove(Arena a, GroundWeapon g) {
        a.groundWeapons.remove(g);
        if (g.display != null) {
            a.tracked.remove(g.display);
            g.display.remove();
        }
        for (ItemDisplay h : g.highlights.values()) {
            a.tracked.remove(h);
            h.remove();
        }
        g.highlights.clear();
    }

    /** 조준선이 가리키는 무기 (여러 개가 겹치면 가장 최근 것). */
    public GroundWeapon target(Arena a, Vec3 eye, Vec3 dir, double range, GroundWeapon exclude) {
        GroundWeapon best = null;
        double wallDist = range;
        RayTraceResult wall = a.world.rayTraceBlocks(new Location(a.world, eye.x(), eye.y(), eye.z()), new Vector(dir.x(), dir.y(), dir.z()), range, FluidCollisionMode.NEVER, true);
        if (wall != null) {
            Vector hp = wall.getHitPosition();
            wallDist = eye.distance(new Vec3(hp.getX(), hp.getY(), hp.getZ())) + 0.35;
        }
        for (GroundWeapon g : a.groundWeapons) {
            if (g == exclude) continue;
            if (g.pos.distanceSq(eye) > (range + 1) * (range + 1)) continue;
            double t = g.pickBox().rayIntersect(eye, dir, Math.min(range, wallDist));
            if (t < 0) continue;
            if (best == null || g.dropTick > best.dropTick) best = g;
        }
        return best;
    }

    /** NPC 용: 가까운 무기 */
    public GroundWeapon nearest(Arena a, Vec3 p, double radius, boolean wantGun) {
        GroundWeapon best = null;
        double bd = radius * radius;
        for (GroundWeapon g : a.groundWeapons) {
            if (wantGun && (!g.weapon.type().isGun() || !g.weapon.hasAmmo())) continue;
            if (g.weapon.type().isGun() && !g.weapon.hasAmmo()) continue;
            double d = g.pos.distanceSq(p);
            if (d < bd) {
                bd = d;
                best = g;
            }
        }
        return best;
    }

    public void tick(Arena a, long now) {
        // 빈 총 제거
        Iterator<GroundWeapon> it = new ArrayList<>(a.groundWeapons).iterator();
        while (it.hasNext()) {
            GroundWeapon g = it.next();
            if (g.weapon.type().isGun() && !g.weapon.hasAmmo() && now - g.dropTick > EMPTY_GUN_LIFETIME) {
                remove(a, g);
            }
        }
        // 하이라이트 (2틱마다)
        if (now % 2 != 0) return;
        for (PlayerCombatant pc : a.players.values()) {
            Player p = pc.player();
            GroundWeapon t = pc.canAct(now) ? target(a, pc.eye(), pc.look(), PICK_RANGE, null) : null;
            for (GroundWeapon g : a.groundWeapons) {
                ItemDisplay h = g.highlights.get(p.getUniqueId());
                if (g == t && h == null) {
                    ItemDisplay hd = a.track(a.world.spawn(g.display.getLocation(), ItemDisplay.class, d -> {
                        d.setItemStack(g.display.getItemStack());
                        d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.FIXED);
                        d.setTransformation(lyingTransform(g.yaw, 0.76f));
                        d.setPersistent(false);
                        d.setVisibleByDefault(false);
                        d.setGlowing(true);
                        d.setGlowColorOverride(Color.WHITE);
                    }));
                    p.showEntity(plugin, hd);
                    g.highlights.put(p.getUniqueId(), hd);
                } else if (g != t && h != null) {
                    a.tracked.remove(h);
                    h.remove();
                    g.highlights.remove(p.getUniqueId());
                }
            }
        }
    }

    public void removeHighlights(Arena a, UUID player) {
        for (GroundWeapon g : a.groundWeapons) {
            ItemDisplay h = g.highlights.remove(player);
            if (h != null) {
                a.tracked.remove(h);
                h.remove();
            }
        }
    }

    public void pickUp(Arena a, Combatant c, GroundWeapon g) {
        remove(a, g);
        c.weapon = g.weapon;
    }
}
