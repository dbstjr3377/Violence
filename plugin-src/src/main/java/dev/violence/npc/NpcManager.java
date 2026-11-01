package dev.violence.npc;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.arena.GroundWeapon;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.combat.Execution;
import dev.violence.fx.Fx;
import dev.violence.logic.AStar;
import dev.violence.logic.NavGrid;
import dev.violence.math.Vec3;
import dev.violence.weapon.ExecutionStyle;
import dev.violence.weapon.WeaponType;
import io.papermc.paper.datacomponent.item.ResolvableProfile;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.attribute.Attribute;
import org.bukkit.block.Block;
import org.bukkit.entity.Mannequin;

/**
 * NPC 생성과 인공지능.
 * 상태: 배회 → (무기 없으면) 무기 찾기 → 적 발견 시 사격/돌격/투척 → 쓰러진 적 처형.
 * 소음기 없는 총소리를 들으면 그쪽으로 이동한다. NPC 끼리도 서로 싸운다.
 */
public final class NpcManager {
    private static final int[] GANG_COLORS = {0xE8E8E8, 0x2B2B2B, 0x7A1F2B, 0x1F3F7A, 0x5A6B2A, 0xC2A05A, 0x6B3FA0, 0xD06A1A};
    private static final String[] NAMES = {"Vinnie", "Tommy", "Carlos", "Sal", "Dmitri", "Rocco", "Benny", "Luca", "Marco", "Nikolai",
            "Frankie", "Joey", "Paulie", "Victor", "Ivan", "Sergei", "Bruno", "Dante", "Enzo", "Gino"};
    private static final double SPEED = 0.235;
    private static final double HEAVY_SPEED = 0.19;
    private static final int PATH_BUDGET = 4;

    private final ViolencePlugin plugin;
    private int pathsThisTick;

    public NpcManager(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public void spawn(Arena a, int count) {
        double heavyChance = plugin.getConfig().getDouble("npc.heavy-chance", 0.12);
        double skillMin = plugin.getConfig().getDouble("npc.skill-min", 0.35);
        double skillMax = plugin.getConfig().getDouble("npc.skill-max", 0.8);
        for (int i = 0; i < count; i++) {
            boolean heavy = plugin.random().nextDouble() < heavyChance;
            String nm = NAMES[plugin.random().nextInt(NAMES.length)] + (i + 1);
            ResolvableProfile prof = ResolvableProfile.resolvableProfile()
                    .name(nm.length() > 16 ? nm.substring(0, 16) : nm)
                    .uuid(UUID.randomUUID())
                    .build();
            int color = GANG_COLORS[plugin.random().nextInt(GANG_COLORS.length)];
            Vec3 spot = a.map.spawns.isEmpty() ? a.map.lobbySpawn : a.map.spawns.get(plugin.random().nextInt(a.map.spawns.size()));
            Location l = Fx.loc(a.world, spot);
            Mannequin m = a.track(a.world.spawn(l, Mannequin.class, b -> {
                b.setPersistent(false);
                b.setImmovable(true);
                b.setDescription(null);
                b.setGravity(false);
                b.setSilent(true);
                b.setProfile(prof);
                b.setCollidable(false);
                b.setCustomNameVisible(false);
                if (heavy) {
                    var s = b.getAttribute(Attribute.SCALE);
                    if (s != null) s.setBaseValue(1.2);
                }
            }));
            double skill = skillMin + plugin.random().nextDouble() * (skillMax - skillMin);
            NpcCombatant n = new NpcCombatant(m, prof, nm, color, heavy, skill);
            n.copyOutfitTo(m.getEquipment());
            a.add(n);
            // 시작 위치는 숨겨진 곳으로
            Vec3 start = plugin.spawns().choose(a, n);
            Location sl = Fx.loc(a.world, start);
            sl.setYaw(plugin.random().nextFloat() * 360);
            n.teleport(sl);
            n.nextThink = plugin.now() + plugin.random().nextInt(10);
        }
    }

    /** 총소리/유리 깨지는 소리 등: 반경 안의 NPC 가 그쪽을 살피러 간다 */
    public void hearNoise(Vec3 at, double radius) {
        Arena a = plugin.arena();
        if (a == null) return;
        long now = plugin.now();
        for (NpcCombatant n : a.npcs) {
            if (n.state != CombatState.ALIVE) continue;
            if (n.target != null && now - n.targetSeenAt < 40) continue;
            if (n.pos.distanceSq(at) > radius * radius) continue;
            n.noisePos = at;
            n.noiseUntil = now + 160;
            n.nextRepath = 0;
        }
    }

    public void tick(Arena a, long now) {
        pathsThisTick = 0;
        for (NpcCombatant n : new ArrayList<>(a.npcs)) {
            try {
                tickNpc(a, n, now);
            } catch (RuntimeException ex) {
                plugin.getLogger().warning("NPC 처리 오류 (" + n.name + "): " + ex);
            }
        }
    }

    private void tickNpc(Arena a, NpcCombatant n, long now) {
        switch (n.state) {
            case DEAD, BEING_EXECUTED -> {
                return;
            }
            case DOWNED -> {
                // 밀려나는 중
                applySlide(a, n);
                n.sync();
                return;
            }
            case EXECUTING -> {
                Execution e = n.execution;
                if (e != null && e.style == ExecutionStyle.HITS && now % 5 == 0) plugin.combat().executionClick(n, now);
                return;
            }
            default -> {
            }
        }
        applySlide(a, n);
        if (now >= n.nextThink) {
            think(a, n, now);
            n.nextThink = now + 4;
        }
        act(a, n, now);
        n.sync();
    }

    private void applySlide(Arena a, NpcCombatant n) {
        if (n.slide.lengthSq() < 0.0004) {
            n.slide = Vec3.ZERO;
            return;
        }
        tryMove(a, n, n.slide);
        n.slide = n.slide.mul(0.7);
    }

    // ───────── 인지 ─────────

    private void think(Arena a, NpcCombatant n, long now) {
        Combatant best = null;
        double bestScore = Double.MAX_VALUE;
        Vec3 eye = n.eye();
        Vec3 look = n.look().horizontal().normalize();
        for (Combatant c : a.combatants.values()) {
            if (c == n || !c.isAlive()) continue;
            Vec3 ce = c.state.isDownedLike() ? c.feet().add(0, 0.4, 0) : c.eye();
            double d = ce.distance(eye);
            if (d > 42) continue;
            Vec3 to = ce.sub(eye).horizontal().normalize();
            boolean inFov = d < 5 || to.dot(look) > -0.2 || c == n.target;
            if (!inFov) continue;
            if (!plugin.combat().lineOfSight(a, eye, ce)) continue;
            double score = d;
            if (c.state.isDownedLike()) score -= 4; // 쓰러진 적 우선 처리
            if (c.isPlayer()) score -= 2;
            if (score < bestScore) {
                bestScore = score;
                best = c;
            }
        }
        if (best != null) {
            if (n.target != best || now - n.targetSeenAt > 40) {
                // 처음 발견하면 반응 시간
                n.reactionUntil = now + (long) (6 + (1 - n.skill) * 14 + plugin.random().nextInt(5));
            }
            n.target = best;
            n.targetSeenAt = now;
            n.targetLastPos = best.feet();
            n.noisePos = null;
        } else if (n.target != null && (now - n.targetSeenAt > 100 || !n.target.isAlive())) {
            n.target = null;
        }
    }

    // ───────── 행동 ─────────

    private void act(Arena a, NpcCombatant n, long now) {
        WeaponType fist = plugin.weapons().fist();
        WeaponType t = n.weaponType(fist);
        Combatant tgt = n.target;
        boolean seesTarget = tgt != null && now - n.targetSeenAt <= 8 && tgt.isAlive();
        n.moveDir = Vec3.ZERO;

        // 1) 무기 줍기
        if (n.canAct(now)) {
            GroundWeapon near = plugin.ground().nearest(a, n.pos, 1.4, false);
            boolean wants = n.weapon == null || (n.weapon.type().isGun() && !n.weapon.hasAmmo());
            if (near != null && wants) {
                if (n.weapon != null) plugin.combat().throwWeapon(n, now);
                plugin.combat().pickUp(n, near);
                return;
            }
        }

        if (seesTarget) {
            double dist = tgt.feet().distance(n.pos);
            // 쓰러진 적: 다가가서 처형
            if (tgt.state == CombatState.DOWNED) {
                if (t.isGun() && n.weapon.hasAmmo() && dist > 3) {
                    aimAndFire(a, n, tgt, t, now, dist);
                    return;
                }
                if (dist < 1.6) {
                    face(n, tgt.feet(), 30);
                    plugin.combat().space(n, now);
                    return;
                }
                moveToward(a, n, tgt.feet(), now);
                return;
            }
            switch (t.category()) {
                case GUN -> {
                    if (n.weapon.hasAmmo()) {
                        if (dist > 26) moveToward(a, n, tgt.feet(), now);
                        else if (dist < 4 && n.skill > 0.6) strafe(a, n, tgt);
                        aimAndFire(a, n, tgt, t, now, dist);
                    } else if (dist < 13 && dist > 2.5) {
                        face(n, tgt.eye(), 40);
                        if (now >= n.reactionUntil && n.canAct(now)) plugin.combat().throwWeapon(n, now);
                    } else {
                        seekWeaponOrChase(a, n, tgt, now);
                    }
                }
                case THROWABLE -> {
                    if (dist < 14) {
                        face(n, tgt.eye(), 30);
                        if (now >= n.reactionUntil && n.canAct(now)) plugin.combat().throwWeapon(n, now);
                    } else moveToward(a, n, tgt.feet(), now);
                }
                case MELEE, FIST -> {
                    // 무기 없이 멀리 있는 적이면 근처 무기부터
                    if (t.isFist() && dist > 8) {
                        GroundWeapon g = plugin.ground().nearest(a, n.pos, 10, false);
                        if (g != null) {
                            moveToward(a, n, g.pos, now);
                            return;
                        }
                    }
                    double reach = t.meleeRange() - 0.3;
                    if (dist <= reach) {
                        face(n, tgt.feet().add(0, 1.0, 0), 45);
                        if (now >= n.reactionUntil) plugin.combat().trigger(n, now, true, false);
                    } else {
                        moveToward(a, n, tgt.feet(), now);
                        face(n, tgt.feet().add(0, 1.4, 0), 20);
                    }
                }
            }
            return;
        }

        // 2) 적이 안 보임
        if (n.weapon == null || (n.weapon.type().isGun() && !n.weapon.hasAmmo())) {
            GroundWeapon g = plugin.ground().nearest(a, n.pos, 18, false);
            if (g != null) {
                moveToward(a, n, g.pos, now);
                return;
            }
        }
        if (n.target != null && n.targetLastPos != null) {
            moveToward(a, n, n.targetLastPos, now);
            if (n.pos.distance(n.targetLastPos) < 1.5) n.target = null;
            return;
        }
        if (n.noisePos != null && now < n.noiseUntil) {
            moveToward(a, n, n.noisePos, now);
            if (n.pos.distance(n.noisePos) < 2) n.noisePos = null;
            return;
        }
        wander(a, n, now);
    }

    private void seekWeaponOrChase(Arena a, NpcCombatant n, Combatant tgt, long now) {
        GroundWeapon g = plugin.ground().nearest(a, n.pos, 10, false);
        if (g != null) moveToward(a, n, g.pos, now);
        else moveToward(a, n, tgt.feet(), now);
    }

    private void aimAndFire(Arena a, NpcCombatant n, Combatant tgt, WeaponType t, long now, double dist) {
        // 머리 대신 주로 몸통을 노리고, 거리가 멀수록 부정확
        Vec3 aim = tgt.state.isDownedLike() ? tgt.feet().add(0, 0.3, 0) : tgt.feet().add(0, plugin.random().nextDouble() < 0.2 ? 1.55 : 1.1, 0);
        face(n, aim, 18 + n.skill * 20);
        if (now < n.reactionUntil || !n.canAct(now)) return;
        Vec3 want = aim.sub(n.eye()).normalize();
        if (want.angleTo(n.look()) > 6) return;
        if (t.automatic()) {
            if (now >= n.burstUntil + 10 + (long) ((1 - n.skill) * 14)) n.burstUntil = now + 8 + plugin.random().nextInt(10);
            if (now <= n.burstUntil) plugin.combat().trigger(n, now, false, true);
        } else if (now >= n.nextShotAt) {
            plugin.combat().trigger(n, now, true, false);
            n.nextShotAt = now + 6 + (long) ((1 - n.skill) * 12) + plugin.random().nextInt(6);
        }
    }

    private void face(NpcCombatant n, Vec3 point, double maxTurn) {
        Vec3 d = point.sub(n.eye());
        if (d.lengthSq() < 1e-4) return;
        float wantYaw = (float) d.yaw();
        float wantPitch = (float) d.pitch();
        float dy = wrap(wantYaw - n.yaw);
        dy = (float) Math.max(-maxTurn, Math.min(maxTurn, dy));
        n.yaw = wrap(n.yaw + dy);
        float dp = wantPitch - n.pitch;
        dp = (float) Math.max(-maxTurn, Math.min(maxTurn, dp));
        n.pitch = Math.max(-80, Math.min(80, n.pitch + dp));
    }

    private static float wrap(float a) {
        a %= 360;
        if (a >= 180) a -= 360;
        if (a < -180) a += 360;
        return a;
    }

    private void strafe(Arena a, NpcCombatant n, Combatant tgt) {
        Vec3 to = tgt.feet().sub(n.pos).horizontal().normalize();
        Vec3 side = new Vec3(-to.z(), 0, to.x()).mul(((plugin.now() / 30) % 2 == 0) ? 1 : -1);
        tryMove(a, n, side.mul(speed(n) * 0.6));
    }

    private double speed(NpcCombatant n) {
        return n.heavy ? HEAVY_SPEED : SPEED;
    }

    private void wander(Arena a, NpcCombatant n, long now) {
        if (n.path.isEmpty() || n.pathIndex >= n.path.size()) {
            if (now < n.nextRepath || a.nav.size() == 0 || pathsThisTick >= PATH_BUDGET) return;
            NavGrid.Node start = a.nav.nearest(n.pos);
            NavGrid.Node goal = null;
            for (int i = 0; i < 6 && goal == null; i++) {
                NavGrid.Node cand = a.nav.nodes().get(plugin.random().nextInt(a.nav.size()));
                double d = cand.pos().distance(n.pos);
                if (d > 8 && d < 40) goal = cand;
            }
            if (goal == null) return;
            pathsThisTick++;
            n.path = new ArrayList<>(AStar.find(a.nav, start, goal, 3000));
            n.pathIndex = 0;
            n.pathGoal = goal.pos();
            n.nextRepath = now + 40;
        }
        followPath(a, n, 0.75);
    }

    private void moveToward(Arena a, NpcCombatant n, Vec3 goal, long now) {
        boolean needPath = n.path.isEmpty() || n.pathIndex >= n.path.size() || n.pathGoal == null
                || n.pathGoal.distance(goal) > 2.5;
        if (needPath && now >= n.nextRepath && pathsThisTick < PATH_BUDGET && a.nav.size() > 0) {
            pathsThisTick++;
            NavGrid.Node s = a.nav.nearest(n.pos);
            NavGrid.Node g = a.nav.nearest(goal);
            n.path = new ArrayList<>(AStar.find(a.nav, s, g, 4000));
            n.pathIndex = 0;
            n.pathGoal = goal;
            n.nextRepath = now + 12;
        }
        if (n.path.isEmpty()) {
            // 경로가 없으면 직선으로 시도
            Vec3 d = goal.sub(n.pos).horizontal();
            if (d.length() > 0.5) {
                Vec3 step = d.normalize().mul(speed(n));
                n.moveDir = step.normalize();
                tryMove(a, n, step);
                faceMove(n);
            }
            return;
        }
        followPath(a, n, 1.0);
    }

    private void followPath(Arena a, NpcCombatant n, double speedMul) {
        if (!n.canMove(plugin.now())) return;
        while (n.pathIndex < n.path.size() && n.path.get(n.pathIndex).horizontalDistance(n.pos) < 0.35) n.pathIndex++;
        if (n.pathIndex >= n.path.size()) return;
        Vec3 wp = n.path.get(n.pathIndex);
        Vec3 d = wp.sub(n.pos).horizontal();
        double len = d.length();
        double sp = Math.min(len, speed(n) * speedMul);
        Vec3 step = d.normalize().mul(sp);
        n.moveDir = d.normalize();
        boolean moved = tryMove(a, n, step);
        if (n.target == null || plugin.now() - n.targetSeenAt > 8) faceMove(n);
        // 막힘 감지 (닫힌 문은 밀면서 기다림)
        if (n.lastProgressPos == null || n.lastProgressPos.distance(n.pos) > 0.5) {
            n.lastProgressPos = n.pos;
            n.stuckSince = plugin.now();
        } else if (plugin.now() - n.stuckSince > 50) {
            n.path.clear();
            n.nextRepath = plugin.now() + 10;
            n.stuckSince = plugin.now();
        }
        if (!moved) n.moveDir = d.normalize();
    }

    private void faceMove(NpcCombatant n) {
        if (n.moveDir.lengthSq() < 0.01) return;
        Vec3 p = n.eye().add(n.moveDir.mul(3));
        face(n, new Vec3(p.x(), n.eye().y(), p.z()), 25);
    }

    /** 운동학적 이동: 막히지 않으면 이동하고 바닥 높이를 맞춘다. */
    private boolean tryMove(Arena a, NpcCombatant n, Vec3 step) {
        Vec3 next = n.pos.add(step.x(), 0, step.z());
        // 몸 폭(0.3) 고려한 충돌
        double r = 0.28;
        double[] off = {-r, r};
        double y = n.pos.y();
        NavGrid.Node node = a.nav.nodeAt((int) Math.floor(next.x()), (int) Math.floor(next.z()), y, 0.62);
        double newY = node != null ? node.h : y;
        if (node == null) {
            // 그리드 밖: 블록 충돌만 검사
            if (!passable(a, next.x(), newY, next.z())) return false;
        }
        for (double ox : off) {
            for (double oz : off) {
                if (!passable(a, next.x() + ox, newY, next.z() + oz)) return false;
            }
        }
        n.pos = new Vec3(next.x(), newY, next.z());
        return true;
    }

    private boolean passable(Arena a, double x, double y, double z) {
        Block feet = a.world.getBlockAt((int) Math.floor(x), (int) Math.floor(y + 0.6), (int) Math.floor(z));
        Block head = a.world.getBlockAt((int) Math.floor(x), (int) Math.floor(y + 1.5), (int) Math.floor(z));
        return open(feet) && open(head);
    }

    private static boolean open(Block b) {
        Material m = b.getType();
        if (m == Material.BARRIER) return false;
        return b.isPassable();
    }

    public void clear() {
    }
}
