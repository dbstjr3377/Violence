package dev.violence.arena;

import dev.violence.ViolencePlugin;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.fx.Fx;
import dev.violence.logic.KillType;
import dev.violence.mask.Mask;
import dev.violence.math.Vec3;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.block.Block;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 밀어서 여는 문.
 * - 닫힌 문 앞에서 앞으로 걸어가면 반대쪽으로 밀려 열린다.
 * - 닫혀 있을 때는 문틀에 보이지 않는 벽(barrier)을 세워 충돌 판정을 준다.
 * - 총알/투척물에 맞으면 그 방향으로 열린다.
 * - 발차기로 크게 열리며, 빠르게 도는 문에 부딪힌 개체는 쓰러진다.
 */
public final class DoorService {
    public static final double WALK_PUSH = 9;
    public static final double BULLET_PUSH = 11;
    public static final double KICK_PUSH = 34;

    private final ViolencePlugin plugin;

    public DoorService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public void spawnDoors(Arena a) {
        for (GameMap.DoorSpec s : a.map.doors) {
            Door d = new Door(s.x(), s.y(), s.z(), s.alongX(), s.hingeMax());
            Vec3 h = d.hinge();
            d.display = a.track(a.world.spawn(new Location(a.world, h.x(), h.y(), h.z()), ItemDisplay.class, e -> {
                e.setItemStack(Fx.model("violence:misc/door"));
                e.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
                e.setPersistent(false);
                e.setViewRange(2f);
                e.setShadowRadius(0);
            }));
            a.doors.add(d);
            updateVisual(d, true);
            setBarrier(a, d, true);
        }
    }

    private void setBarrier(Arena a, Door d, boolean on) {
        if (d.barrierPlaced == on) return;
        for (int dy = 0; dy < 2; dy++) {
            Block b = a.world.getBlockAt(d.bx, d.by + dy, d.bz);
            if (on && b.getType() == Material.AIR) b.setType(Material.BARRIER, false);
            else if (!on && b.getType() == Material.BARRIER) b.setType(Material.AIR, false);
        }
        d.barrierPlaced = on;
    }

    private void updateVisual(Door d, boolean instant) {
        if (d.display == null || !d.display.isValid()) return;
        double angle = d.physics.angle();
        if (!instant && Math.abs(angle - d.lastSentAngle) < 0.2) return;
        d.lastSentAngle = angle;
        // 모델: 경첩(원점)에서 +X 방향 1블록, 높이 2블록 문판. 아이템 모델은 중심 기준이므로 (0.5,0.5,0) 이동 후 회전
        float yaw = (float) -d.yawRad();
        Quaternionf q = new Quaternionf().rotateY(yaw);
        Vector3f offset = q.transform(new Vector3f(0.5f, 0.5f, 0f));
        d.display.setInterpolationDelay(0);
        d.display.setInterpolationDuration(instant ? 0 : 2);
        d.display.setTransformation(new Transformation(offset, q, new Vector3f(1, 1, 1), new Quaternionf()));
        d.display.setBrightness(null);
    }

    /** 총알이 문에 맞음 */
    public void bulletHit(Door d, Vec3 dir, Combatant shooter) {
        d.pushAlong(dir, BULLET_PUSH, shooter, false);
        plugin.fx().sound(d.display.getWorld(), d.center(), "violence:world.door_hit", 1f, 1f);
    }

    /** 발차기 */
    public void kick(Door d, Combatant kicker) {
        Vec3 dir = d.center().sub(kicker.feet()).horizontal().normalize();
        d.pushAlong(dir, KICK_PUSH, kicker, true);
        plugin.fx().sound(d.display.getWorld(), d.center(), "violence:world.door_kick", 1.6f, 0.9f);
        if (plugin.npcs() != null) plugin.npcs().hearNoise(d.center(), 14);
    }

    /** c 의 정면 range 이내에 있는 문 */
    public Door doorInFront(Arena a, Combatant c, double range) {
        Vec3 f = c.feet().add(0, 1, 0);
        Vec3 look = c.look().horizontal().normalize();
        Door best = null;
        double bd = range;
        for (Door d : a.doors) {
            Vec3 to = d.obb().center().sub(f);
            double dist = to.horizontal().length();
            if (dist > bd) continue;
            if (dist > 0.6 && to.horizontal().normalize().dot(look) < 0.35) continue;
            bd = dist;
            best = d;
        }
        return best;
    }

    public void tick(Arena a, long now) {
        for (Door d : a.doors) {
            // 1) 사람이 닫힌 문에 몸을 붙이고 앞으로 걸어가면 밀린다
            for (Combatant c : a.combatants.values()) {
                if (c.state != CombatState.ALIVE) continue;
                Vec3 p = c.feet();
                if (Math.abs(p.y() - d.by) > 1.2) continue;
                if (d.lateralDistance(p) > 0.75) continue;
                double plane = d.planeDistance(p);
                if (Math.abs(plane) > 1.0) continue;
                boolean pushing = c.wantsToWalkThrough(d, now);
                if (d.physics.isClosed()) {
                    if (pushing && Math.abs(plane) < 0.95) {
                        Vec3 dir = new Vec3(0, 0, 0).sub(d.normal().mul(Math.signum(plane)));
                        d.pushAlong(dir, WALK_PUSH, c, false);
                        if (!d.physics.isMoving()) continue;
                        plugin.fx().sound(a.world, d.center(), "violence:world.door_push", 0.8f, 1f);
                    }
                } else if (d.obb().overlapsPoint(p.add(0, 0.9, 0), 0.32)) {
                    // 2) 열린 문판과 몸이 겹침
                    if (d.physics.isDangerous() && d.lastPusher != c) {
                        hitByDoor(a, d, c, now);
                    } else {
                        // 밀어서 통과: 문판이 몸에서 비켜나도록 돌림 (몸이 문판을 뚫고 지나가 보이지 않게)
                        Vec3 away = p.sub(d.hinge()).horizontal();
                        Vec3 tangent = new Vec3(-d.dir().z(), 0, d.dir().x());
                        int side = away.dot(tangent) >= 0 ? -1 : 1;
                        Vec3 pushDir = tangent.mul(side);
                        int towardSide = pushDir.dot(d.normal()) >= 0 ? 1 : -1;
                        if (d.pushOutOf(p.add(0, 0.9, 0), 0.32, d.rotationSignToward(towardSide))) {
                            d.lastPusher = c;
                            d.lastPushWasKick = false;
                        }
                    }
                }
            }
            d.physics.tick();
            setBarrier(a, d, d.physics.isClosed() && !d.physics.isMoving() && !someoneInDoorway(a, d));
            updateVisual(d, false);
        }
    }

    private boolean someoneInDoorway(Arena a, Door d) {
        for (Combatant c : a.combatants.values()) {
            if (!c.isAlive()) continue;
            Vec3 p = c.feet();
            if (Math.abs(p.y() - d.by) > 1.2) continue;
            if (d.lateralDistance(p) < 0.8 && Math.abs(d.planeDistance(p)) < 0.4) return true;
        }
        return false;
    }

    private void hitByDoor(Arena a, Door d, Combatant victim, long now) {
        Combatant pusher = d.lastPusher;
        Vec3 dir = victim.feet().sub(d.hinge()).horizontal().normalize();
        plugin.fx().sound(a.world, victim.eye(), "violence:world.door_slam", 1.4f, 0.8f);
        if (pusher != null && pusher.mask == Mask.DON_JUAN) {
            plugin.combat().kill(victim, pusher, KillType.DOOR, dir, false);
        } else {
            plugin.combat().knockdown(victim, dir, pusher, false);
        }
        // 한 번 맞히면 위험 상태 해제
        d.physics.set(d.physics.angle(), d.physics.velocity() * 0.5);
    }

    public void clear(Arena a) {
        for (Door d : a.doors) setBarrier(a, d, false);
    }

}
