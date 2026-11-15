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
 * 문.
 * - 문 가까이에서 바라보면 흰 테두리와 "F 문 열기 / F 문 닫기" 안내가 뜨고, F 로 열고 닫는다 (여는 사람 반대쪽으로 열림).
 * - 몸으로 밀어서는 열리지 않는다. NPC 는 지나가야 할 닫힌 문 앞에서 문을 연다.
 * - 닫혀 있을 때는 문틀에 보이지 않는 벽(barrier)을 세워 충돌 판정을 준다.
 * - 돈 후안(말 가면)만 Space 로 문을 걷어찰 수 있다 (2초마다). 세게 도는 문에 맞은 적은 즉사, 찬 뒤 2초간 빨라진다.
 */
public final class DoorService {
    public static final double KICK_PUSH = 34;
    /** F 로 문을 다룰 수 있는 거리 (눈에서 문틀·문판 가운데까지, 블록) */
    public static final double INTERACT_RANGE = 2.3;
    /** 발차기 쿨타임 (틱) */
    public static final int KICK_COOLDOWN = 40;
    /** 발차기 뒤 빨라지는 시간 (틱) */
    public static final int KICK_BOOST = 40;

    private final ViolencePlugin plugin;
    /** 플레이어별 지금 F 로 다룰 수 있는 문 */
    private final java.util.Map<java.util.UUID, Door> targets = new java.util.HashMap<>();
    /** 플레이어별 흰 테두리 문 (그 플레이어에게만 보이는 빛나는 복제본, 원래 문은 그 플레이어에게 숨김) */
    private final java.util.Map<java.util.UUID, Highlight> highlights = new java.util.HashMap<>();

    private record Highlight(Door door, ItemDisplay display) {}

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
        Transformation tr = new Transformation(offset, q, new Vector3f(1, 1, 1), new Quaternionf());
        d.display.setTransformation(tr);
        d.display.setBrightness(null);
        for (Highlight h : highlights.values()) {
            if (h.door() != d || !h.display().isValid()) continue;
            h.display().setInterpolationDelay(0);
            h.display().setInterpolationDuration(instant ? 0 : 2);
            h.display().setTransformation(tr);
        }
    }

    /** 총알이 문에 맞음 (문은 F 로만 열림: 소리만) */
    public void bulletHit(Door d, Vec3 dir, Combatant shooter) {
        plugin.fx().sound(d.display.getWorld(), d.center(), "violence:world.door_hit", 1f, 1f);
    }

    /** F: 문 열기 / 닫기 */
    public void toggle(Arena a, Door d, Combatant c) {
        if (d.isOpen()) {
            d.close(c);
            plugin.fx().sound(a.world, d.center(), "violence:world.door_push", 0.8f, 0.85f);
        } else {
            d.open(c.feet(), c);
            plugin.fx().sound(a.world, d.center(), "violence:world.door_push", 0.8f, 1.1f);
        }
    }

    /** F 로 다룰 수 있는 문: 눈에서 INTERACT_RANGE 안, 바라보는 쪽 (문틀 가운데 또는 열린 문판 가운데) */
    public Door interactable(Arena a, Combatant c) {
        if (!c.isAlive() || c.state != CombatState.ALIVE) return null;
        Vec3 eye = c.eye();
        Vec3 look = c.look();
        Door best = null;
        double bd = INTERACT_RANGE;
        for (Door d : a.doors) {
            for (Vec3 p : new Vec3[] {d.center(), d.obb().center()}) {
                Vec3 to = p.sub(eye);
                double dist = to.length();
                if (dist > bd) continue;
                if (dist > 0.9 && to.normalize().dot(look) < 0.55) continue;
                bd = dist;
                best = d;
            }
        }
        return best;
    }

    /** 지금 F 로 다룰 수 있는 문 (매 틱 갱신, HUD 와 F 키가 씀) */
    public Door target(Combatant c) {
        return targets.get(c.id);
    }

    /** 돈 후안 발차기를 할 수 있는가 (닫힌 문, 쿨타임 끝) */
    public boolean canKick(Combatant c, Door d, long now) {
        return d != null && c.mask == Mask.DON_JUAN && !d.isOpen() && now >= c.doorKickReadyAt;
    }

    /** 발차기 (돈 후안) */
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
            for (Combatant c : a.combatants.values()) {
                if (c.state != CombatState.ALIVE) continue;
                Vec3 p = c.feet();
                if (Math.abs(p.y() - d.by) > 1.2) continue;
                // NPC: 지나가야 할 닫힌 문 앞이면 문을 엶 (돈 후안이면 걷어참)
                if (c instanceof dev.violence.npc.NpcCombatant && !d.isOpen() && d.lateralDistance(p) < 0.75
                        && Math.abs(d.planeDistance(p)) < 1.3 && c.wantsToWalkThrough(d, now) && now >= c.nextDoorUse) {
                    c.nextDoorUse = now + 20;   // 같은 문을 연달아 건드리지 않게
                    if (canKick(c, d, now)) plugin.combat().kickDoor(c, d, now);
                    else toggle(a, d, c);
                    continue;
                }
                // 발차기로 세게 도는 문판에 맞으면 쓰러짐 (돈 후안이 찼으면 즉사)
                if (d.physics.isDangerous() && d.lastPusher != c && d.obb().overlapsPoint(p.add(0, 0.9, 0), 0.32)) {
                    hitByDoor(a, d, c, now);
                }
            }
            d.physics.tick();
            setBarrier(a, d, d.physics.isClosed() && !d.physics.isMoving() && !someoneInDoorway(a, d));
            updateVisual(d, false);
        }
        // 플레이어별 F 대상 문 + 흰 테두리
        for (dev.violence.player.PlayerCombatant pc : a.players.values()) {
            org.bukkit.entity.Player p = pc.player();
            Door t = pc.canAct(now) && !plugin.camera().isViewing(p) ? interactable(a, pc) : null;
            if (t == null) targets.remove(pc.id);
            else targets.put(pc.id, t);
            Highlight h = highlights.get(p.getUniqueId());
            if (h != null && (h.door() != t || !h.display().isValid())) {
                removeHighlight(a, p, h);
                highlights.remove(p.getUniqueId());
                h = null;
            }
            if (t != null && h == null && t.display != null && t.display.isValid()) {
                ItemDisplay src = t.display;
                ItemDisplay hd = a.track(a.world.spawn(src.getLocation(), ItemDisplay.class, e -> {
                    e.setItemStack(src.getItemStack());
                    e.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
                    e.setTransformation(src.getTransformation());
                    e.setPersistent(false);
                    e.setViewRange(2f);
                    e.setShadowRadius(0);
                    e.setVisibleByDefault(false);
                    e.setGlowing(true);
                    e.setGlowColorOverride(org.bukkit.Color.WHITE);
                }));
                p.showEntity(plugin, hd);
                p.hideEntity(plugin, src);   // 원래 문은 이 플레이어에게만 숨김 (같은 자리에 겹쳐 깜빡이지 않게)
                highlights.put(p.getUniqueId(), new Highlight(t, hd));
            }
        }
    }

    private void removeHighlight(Arena a, org.bukkit.entity.Player p, Highlight h) {
        if (h.door().display != null && h.door().display.isValid() && p.isOnline()) p.showEntity(plugin, h.door().display);
        a.tracked.remove(h.display());
        if (h.display().isValid()) h.display().remove();
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
        for (java.util.Map.Entry<java.util.UUID, Highlight> en : highlights.entrySet()) {
            org.bukkit.entity.Player p = plugin.getServer().getPlayer(en.getKey());
            if (p != null) removeHighlight(a, p, en.getValue());
            else if (en.getValue().display().isValid()) en.getValue().display().remove();
        }
        highlights.clear();
        targets.clear();
    }

}
