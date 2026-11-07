package dev.violence.combat;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.arena.Door;
import dev.violence.arena.GlassService;
import dev.violence.arena.GroundWeapon;
import dev.violence.arena.GroundWeaponService;
import dev.violence.fx.Fx;
import dev.violence.logic.FireAccumulator;
import dev.violence.logic.KillType;
import dev.violence.logic.Spread;
import dev.violence.mask.Mask;
import dev.violence.math.Aabb;
import dev.violence.math.Hitbox;
import dev.violence.math.Vec3;
import dev.violence.player.PlayerCombatant;
import dev.violence.weapon.ExecutionStyle;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponItems;
import dev.violence.weapon.WeaponType;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.block.Block;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 전투 규칙의 중심.
 * 사용(왼클릭) / 던지기·줍기(우클릭) / Space(올라타기·발차기·가면 능력) 와
 * 피격 → 쓰러짐 → 처형 → 사망 → 리스폰 흐름을 처리한다.
 */
public final class CombatService {
    public static final int DOWNED_TICKS = 60;
    public static final int RESPAWN_TICKS = 40;
    public static final int STANDUP_LOCK = 3;
    public static final double THROW_SPEED = 1.65;
    public static final double THROW_GRAVITY = 0.028;
    /** 연타 처형을 이 틱 동안 끝내지 않으면 자동으로 내려옴 */
    public static final int EXECUTION_TIMEOUT = 160;

    private final ViolencePlugin plugin;
    private final List<Projectile> projectiles = new ArrayList<>();
    private final List<Execution> executions = new ArrayList<>();

    public CombatService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    private Arena arena() { return plugin.arena(); }

    private WeaponType fist() { return plugin.weapons().fist(); }

    // ───────────────────────────── 사용 (왼클릭) ─────────────────────────────

    /**
     * 방아쇠/공격 입력 처리 (매 틱 호출).
     * @param pressed 이번 틱에 새로 누름
     * @param held 누르고 있는 중
     */
    public void trigger(Combatant c, long now, boolean pressed, boolean held) {
        if (arena() == null || !c.canAct(now)) return;
        WeaponType t = c.weaponType(fist());
        switch (t.category()) {
            case GUN -> fireGun(c, t, now, pressed, held);
            case MELEE, FIST -> {
                if (pressed || held) melee(c, now);
            }
            case THROWABLE -> {
                // 투척 전용 무기는 왼클릭으로 사용할 수 없다
            }
        }
    }

    private double rpmMultiplier(Combatant c, WeaponType t) {
        if (c.mask == Mask.PIG_BUTCHER && (t.id().equals("shotgun") || t.id().equals("double_barrel"))) return 1.6;
        return 1.0;
    }

    private void fireGun(Combatant c, WeaponType t, long now, boolean pressed, boolean held) {
        WeaponInstance w = c.weapon;
        if (w == null) return;
        if (!w.hasAmmo()) {
            if (pressed) plugin.fx().sound(c.world(), c.eye(), "violence:gun.empty", 0.8f, 1.2f);
            return;
        }
        FireAccumulator acc = c.fireAccumulator(t, rpmMultiplier(c, t));
        int shots;
        if (t.automatic()) {
            shots = (pressed || held) ? acc.tickHeld(now) : 0;
        } else {
            shots = pressed && acc.trySingle(now) ? 1 : 0;
        }
        if (shots <= 0) return;
        for (int i = 0; i < shots; i++) {
            if (!w.consume(now)) break;
            shoot(c, t, false);
            // 양손 MP5: 왼손도 같이 발사
            if (c.offhand != null && c.offhand.consume(now)) shoot(c, c.offhand.type(), true);
        }
        c.lastFireTick = now;
        c.refreshEquipment();
    }

    /** 한 발(산탄이면 여러 펠릿) 발사 */
    public void shoot(Combatant c, WeaponType t, boolean leftHand) {
        Arena a = arena();
        Vec3 eye = c.eye();
        Vec3 dir = c.look();
        double spread = t.spread() * (c.mask != null ? c.mask.spreadMultiplier() : 1.0) * c.spreadPenalty();
        int pellets = t.pelletsMin() + (t.pelletsMax() > t.pelletsMin() ? plugin.random().nextInt(t.pelletsMax() - t.pelletsMin() + 1) : 0);
        boolean silenced = t.silenced() || c.mask == Mask.PETER;
        Vec3 right = dir.cross(Vec3.UP).normalize();
        // 궤적 시작점: 1인칭 총 모델의 총구가 보이는 방향 (화면 중앙에서 오른쪽 아래)
        Vec3 camUp = right.cross(dir).normalize();
        Vec3 muzzle = eye.add(dir.mul(0.6)).add(right.mul(leftHand ? -0.15 : 0.15)).add(camUp.mul(-0.13));
        for (int i = 0; i < pellets; i++) {
            Vec3 d = Spread.jitter(dir, spread, plugin.random());
            TraceResult r = hitscan(a, c, eye, d, t.range(), t.pierce());
            plugin.fx().tracer(a, muzzle, r.end, t.tracer());
            for (TraceResult.EntityHit h : r.hits) {
                bulletHit(h.target(), h.part(), c, d, h.point());
            }
            if (r.door != null) plugin.doors().bulletHit(r.door, d, c);
            else if (r.wallNormal != null && i < 6) plugin.fx().bulletHole(a, r.end, r.wallNormal);
        }
        plugin.fx().muzzle(a, eye, dir, silenced, c instanceof PlayerCombatant shooter ? shooter.player() : null);
        if (c instanceof PlayerCombatant pcs && !leftHand) {
            // 1인칭: 총구 화염 → 반동 → 반동 잡기 키프레임 (조준점은 움직이지 않음)
            pcs.playAnim(WeaponItems.GUNFIRE, t.fireAnimTicks());
        }
        float vol = silenced ? 0.35f : (pellets > 1 ? 3.2f : 2.6f);
        plugin.fx().sound(c.world(), eye, silenced ? "violence:gun.silenced" : t.sound(), vol, 0.95f + plugin.random().nextFloat() * 0.1f);
        if (!silenced && plugin.npcs() != null) plugin.npcs().hearNoise(eye, pellets > 1 ? 45 : 40);
        if (t.automatic()) {
            // 연사: 발마다 쌓지 않고 일정한 잔떨림만 유지 (조준이 크게 흔들리지 않게)
            c.feelSustained(0.3);
        } else {
            double kick = pellets > 1 ? 0.45 : (t.pierce() ? 0.4 : 0.12);
            c.feelImpact(kick);
        }
    }


    /** 히트스캔 판정: 유리는 깨며 관통, 문/벽에서 멈춤, 개체는 머리/몸통 판정. */
    public TraceResult hitscan(Arena a, Combatant shooter, Vec3 origin, Vec3 dir, double range, boolean pierce) {
        TraceResult res = new TraceResult();
        double endDist = range;
        Vec3 pos = origin;
        double travelled = 0;
        for (int i = 0; i < 12; i++) {
            RayTraceResult r = a.world.rayTraceBlocks(Fx.loc(a.world, pos), new Vector(dir.x(), dir.y(), dir.z()),
                    range - travelled, FluidCollisionMode.NEVER, true);
            if (r == null || r.getHitBlock() == null) {
                endDist = range;
                break;
            }
            Vector hp = r.getHitPosition();
            Vec3 hit = new Vec3(hp.getX(), hp.getY(), hp.getZ());
            double hitDist = origin.distance(hit);
            Block b = r.getHitBlock();
            if (GlassService.isGlass(b.getType())) {
                plugin.glass().shatter(a, b, dir);
                res.brokenGlass.add(hit);
                // 깨진 자리에서 다시 추적 (관통)
                travelled = hitDist;
                pos = hit.add(dir.mul(0.001));
                continue;
            }
            if (b.getType() == Material.BARRIER) {
                Door d = a.doorAt(b.getX(), b.getY(), b.getZ());
                if (d != null) res.door = d;
            }
            endDist = hitDist;
            if (res.door == null && r.getHitBlockFace() != null) {
                Vector n = r.getHitBlockFace().getDirection();
                res.wallNormal = new Vec3(n.getX(), n.getY(), n.getZ());
            }
            break;
        }
        // 열려 있는 문판
        for (Door d : a.doors) {
            if (d.barrierPlaced) continue;
            double t = d.obb().rayIntersect(origin, dir, endDist);
            if (t >= 0 && t < endDist) {
                endDist = t;
                res.door = d;
                res.wallNormal = null;
            }
        }
        // 개체 (지연 보상 적용)
        int rewind = shooter instanceof PlayerCombatant pc ? Math.min(6, Math.max(0, pc.player().getPing() / 50)) : 0;
        List<TraceResult.EntityHit> hits = new ArrayList<>();
        for (Combatant c : a.combatants.values()) {
            if (c == shooter || !c.state.canBeHit()) continue;
            Vec3 feet = rewind > 0 && c.history.get(rewind) != null ? c.history.get(rewind) : c.feet();
            if (feet.distanceSq(origin) > (endDist + 3) * (endDist + 3)) continue;
            // 지연 보상: 그때의 자세(서 있음/쓰러짐)로 판정
            Boolean wasDowned = rewind > 0 ? c.history.downed(rewind) : null;
            boolean downedBox = wasDowned != null ? wasDowned : c.state.isDownedLike();
            Hitbox.Result hr = downedBox
                    ? (plugin.falls().wallStunned(c) ? Hitbox.raycastSitting(feet, c.scale(), origin, dir, endDist)
                            : Hitbox.raycastDowned(feet, c.scale(), origin, dir, endDist))
                    : Hitbox.raycastStanding(feet, c.scale(), origin, dir, endDist);
            if (hr.hit()) hits.add(new TraceResult.EntityHit(c, hr.part(), hr.distance(), origin.add(dir.mul(hr.distance()))));
        }
        hits.sort(Comparator.comparingDouble(TraceResult.EntityHit::distance));
        if (!pierce && !hits.isEmpty()) {
            TraceResult.EntityHit first = hits.getFirst();
            hits.clear();
            hits.add(first);
            endDist = first.distance();
            res.door = null;
            res.wallNormal = null;
        }
        res.hits.addAll(hits);
        res.end = origin.add(dir.mul(endDist));
        return res;
    }

    /** 총알 피격 */
    public void bulletHit(Combatant v, Hitbox.Part part, Combatant shooter, Vec3 dir, Vec3 point) {
        long now = plugin.now();
        if (!v.isAlive()) return;
        if (now < v.rollUntil) return; // 구르는 중 회피
        if (v.bulletShield > 0) {
            v.bulletShield--;
            plugin.fx().sound(v.world(), point, "violence:hit.shield", 1.2f, 1.0f);
            plugin.fx().blood(arena(), point, dir, 1);
            v.feelImpact(0.4);
            if (shooter instanceof PlayerCombatant ps) plugin.hud().hitmarker(ps.player(), false);
            return;
        }
        v.lastAttacker = shooter;
        // 샷건처럼 펠릿이 여러 개인 총 = 강한 공격 (팔을 벌리고 뒤로 날아가며 넘어짐)
        if (shooter != null && shooter.weapon != null && shooter.weapon.type().pelletsMax() > 1) v.strongHitTick = now;
        boolean headshot = part == Hitbox.Part.HEAD;
        if (headshot || v.state.isDownedLike()) {
            plugin.fx().blood(arena(), point, dir, headshot ? 4 : 2);
            kill(v, shooter, KillType.GUN, dir, headshot);
            if (shooter instanceof PlayerCombatant ps) plugin.hud().hitmarker(ps.player(), true);
            return;
        }
        // 몸통: 쓰러뜨리는 정도의 피해
        v.hp -= 40;
        plugin.fx().blood(arena(), point, dir, 2);
        if (v.hp <= 0) kill(v, shooter, KillType.GUN, dir, false);
        else knockdown(v, dir, shooter, false);
        if (shooter instanceof PlayerCombatant ps) plugin.hud().hitmarker(ps.player(), v.state == CombatState.DEAD);
    }

    // ───────────────────────────── 근접 ─────────────────────────────

    public void melee(Combatant c, long now) {
        if (now < c.meleeReadyAt) return;
        Arena a = arena();
        WeaponType t = c.weaponType(fist());
        c.meleeReadyAt = now + t.meleeCooldown();
        // 왼클릭을 이어서 누르면 오→왼→오→왼 으로 번갈아 휘두른다 (잠깐 쉬면 다시 오→왼부터)
        boolean chained = now - c.lastSwingTick <= t.meleeCooldown() + 12;
        c.swingChain = chained ? c.swingChain + 1 : 0;
        boolean swings = WeaponItems.swings(t);
        boolean backhand = swings && (c.swingChain & 1) == 1;
        c.lastSwingTick = now;
        // 3인칭: 두 손 대기 자세에서 무기를 옆으로 크게 휘두름 (연속 공격은 좌우를 번갈아, 늘 오른팔이 휘두름)
        if (swings) plugin.game().tpSwing(c, t, backhand, now);
        else c.entity().swingMainHand();
        int animTicks = Math.max(6, Math.min(9, t.meleeCooldown()));
        if (c instanceof PlayerCombatant pcm) {
            if (swings) {
                pcm.setBackhand(backhand);
                pcm.playAnim(backhand ? WeaponItems.MELEE_B : WeaponItems.MELEE, animTicks);
            } else {
                pcm.playAnim(WeaponItems.animGroup(t), animTicks);
            }
        }
        plugin.fx().sound(c.world(), c.eye(), t.isFist() ? "violence:melee.punch_swing" : "violence:melee.swing", 0.9f,
                (t.meleeCooldown() <= 6 ? 1.4f : 1.0f) * (backhand ? 1.08f : 1.0f));
        Vec3 eye = c.eye();
        Vec3 dir = c.look();
        if (swings) plugin.fx().slash(arena(), eye, dir, backhand, (float) c.scale());
        double range = t.meleeRange();
        // 유리 깨기 / 벽까지 거리
        double wallDist = range;
        RayTraceResult r = a.world.rayTraceBlocks(Fx.loc(a.world, eye), new Vector(dir.x(), dir.y(), dir.z()), range, FluidCollisionMode.NEVER, true);
        if (r != null && r.getHitBlock() != null) {
            if (GlassService.isGlass(r.getHitBlock().getType())) plugin.glass().shatter(a, r.getHitBlock(), dir);
            else {
                Vector hp = r.getHitPosition();
                wallDist = eye.distance(new Vec3(hp.getX(), hp.getY(), hp.getZ())) + 0.3;
            }
        }
        // 문을 치면 밀림
        Door door = plugin.doors().doorInFront(a, c, Math.min(range, 1.6));
        if (door != null && door.physics.isClosed()) door.pushAlong(door.center().sub(c.feet()).horizontal(), 12, c, false);
        Combatant target = meleeTarget(a, c, eye, dir, Math.min(range, wallDist));
        if (target == null) return;
        meleeHit(c, target, t, dir);
    }

    private Combatant meleeTarget(Arena a, Combatant attacker, Vec3 eye, Vec3 dir, double range) {
        Combatant best = null;
        double bestScore = Double.MAX_VALUE;
        for (Combatant c : a.combatants.values()) {
            if (c == attacker || !c.state.canBeHit()) continue;
            Vec3 center = c.state.isDownedLike() ? c.feet().add(0, plugin.falls().wallStunned(c) ? 0.6 : 0.3, 0) : c.feet().add(0, 1.0 * c.scale(), 0);
            Vec3 to = center.sub(eye);
            double dist = to.length();
            if (dist > range + 0.5) continue;
            double angle = to.angleTo(dir);
            double maxAngle = dist < 1.2 ? 75 : 42;
            if (c.state.isDownedLike()) maxAngle = 60;
            if (angle > maxAngle) continue;
            if (!lineOfSight(a, eye, center)) continue;
            double score = dist + angle / 30.0;
            if (score < bestScore) {
                bestScore = score;
                best = c;
            }
        }
        return best;
    }

    /** 두 지점 사이 시야가 뚫려 있는가 (유리는 투명하게 취급). */
    public boolean lineOfSight(Arena a, Vec3 from, Vec3 to) {
        Vec3 d = to.sub(from);
        double len = d.length();
        if (len < 0.01) return true;
        Vec3 dir = d.mul(1 / len);
        Vec3 pos = from;
        double remaining = len;
        for (int i = 0; i < 6; i++) {
            RayTraceResult r = a.world.rayTraceBlocks(Fx.loc(a.world, pos), new Vector(dir.x(), dir.y(), dir.z()), remaining, FluidCollisionMode.NEVER, true);
            if (r == null || r.getHitBlock() == null) return true;
            if (!GlassService.isGlass(r.getHitBlock().getType())) return false;
            Vector hp = r.getHitPosition();
            Vec3 hit = new Vec3(hp.getX(), hp.getY(), hp.getZ());
            double used = pos.distance(hit) + 0.35;
            remaining -= used;
            if (remaining <= 0) return true;
            pos = pos.add(dir.mul(used));
        }
        return false;
    }

    private void meleeHit(Combatant attacker, Combatant v, WeaponType t, Vec3 dir) {
        Vec3 point = v.state.isDownedLike() ? v.feet().add(0, plugin.falls().wallStunned(v) ? 0.7 : 0.3, 0) : v.feet().add(0, 1.3 * v.scale(), 0);
        v.lastAttacker = attacker;
        if (t.isFist()) {
            plugin.fx().sound(v.world(), point, "violence:melee.punch_hit", 1.2f, 1f);
            if (v.state.isDownedLike() || attacker.mask == Mask.TONY) {
                plugin.fx().blood(arena(), point, dir, 3);
                kill(v, attacker, KillType.FIST, dir, false);
            } else if (v.heavy) {
                // 덩치는 맨주먹으로 쓰러지지 않음 - 잠깐 휘청
                v.moveLockUntil = plugin.now() + 4;
                v.feelImpact(0.3);
            } else {
                plugin.fx().blood(arena(), point, dir, 1);
                knockdown(v, dir, attacker, true);
            }
            attacker.feelImpact(0.15);
            return;
        }
        // 근접 무기: 몸통/머리 상관없이 즉사
        plugin.fx().sound(v.world(), point, sharp(t) ? "violence:melee.slash_hit" : "violence:melee.blunt_hit", 1.3f, 1f);
        plugin.fx().blood(arena(), point, dir, 3);
        kill(v, attacker, KillType.MELEE, dir, false);
        attacker.feelImpact(0.3);
        // 당구 큐대는 한 번 맞히면 부러진다
        if (t.breaksInto() != null && attacker.weapon != null) {
            WeaponType broken = plugin.weapons().get(t.breaksInto());
            if (broken != null) {
                attacker.weapon.setType(broken);
                plugin.fx().sound(attacker.world(), attacker.eye(), "violence:melee.cue_break", 1.2f, 1f);
                attacker.refreshEquipment();
            }
        }
    }

    private static boolean sharp(WeaponType t) {
        return t.execution() == ExecutionStyle.AUTO;
    }

    // ───────────────────────────── 던지기 / 줍기 (우클릭) ─────────────────────────────

    /** 우클릭: 들고 있는 무기를 던지고, 조준선에 무기가 있으면 곧바로 줍는다. */
    public void secondary(Combatant c, long now) {
        Arena a = arena();
        if (a == null) return;
        if (c.state == CombatState.EXECUTING) {
            cancelExecution(c.execution);
            return;
        }
        if (!c.canAct(now)) return;
        GroundWeapon target = plugin.ground().target(a, c.eye(), c.look(), GroundWeaponService.PICK_RANGE, null);
        if (c.weapon != null) throwWeapon(c, now);
        if (target != null && a.groundWeapons.contains(target)) pickUp(c, target);
    }

    public void pickUp(Combatant c, GroundWeapon g) {
        Arena a = arena();
        if (a == null || g == null || !a.groundWeapons.contains(g)) return;
        // 손에 남은 무기(임시 무기를 던진 뒤 돌아온 원래 무기 등)는 사라지지 않게 발밑에 내려놓음
        if (c.weapon != null) {
            plugin.ground().drop(a, c.weapon, c.feet(), c.look());
            c.weapon = null;
        }
        plugin.ground().pickUp(a, c, g);
        WeaponInstance w = c.weapon;
        if (w == null) return;
        if (c.mask == Mask.RAMI && w.type().isGun() && !w.ramiBonusGiven()) {
            // 라미: 총을 주우면 탄창 추가 (같은 총은 한 번만)
            w.setAmmo(w.ammo() + w.type().ammo());
            w.markRamiBonus();
        }
        plugin.fx().sound(c.world(), g.pos, "violence:weapon.pickup", 0.9f, 1f);
        c.refreshEquipment();
    }

    public void throwWeapon(Combatant c, long now) {
        Arena a = arena();
        WeaponInstance w = c.weapon;
        if (w == null) return;
        c.weapon = null;
        if (w.expireTick() > 0) {
            // 가면 F키 임시 무기를 던지면 원래 들고 있던 무기로 돌아감
            c.weapon = c.stashedWeapon;
            c.stashedWeapon = null;
        }
        if (c.offhand != null) c.offhand = null;
        c.refreshEquipment();
        c.entity().swingMainHand();
        if (c instanceof PlayerCombatant pct) pct.playAnim(WeaponItems.FIST, 6);   // 던진 뒤 팔을 뻗는 동작
        Vec3 dir = c.look();
        Vec3 start = c.eye().add(dir.mul(0.4)).add(0, -0.1, 0);
        Projectile p = new Projectile(w, c, start, dir.mul(THROW_SPEED).add(0, 0.04, 0));
        p.display = a.track(a.world.spawn(Fx.loc(a.world, start), ItemDisplay.class, d -> {
            d.setItemStack(WeaponItems.create(w.type(), w.ammo()));
            d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.FIXED);
            d.setTeleportDuration(1);
            d.setInterpolationDuration(1);
            d.setPersistent(false);
            d.setViewRange(2f);
        }));
        projectiles.add(p);
        plugin.fx().sound(c.world(), start, "violence:weapon.throw", 1f, 1f);
        if (w.expireTick() > 0) w.setVanishOnDrop(true);
    }

    private void tickProjectiles(Arena a, long now) {
        Iterator<Projectile> it = projectiles.iterator();
        while (it.hasNext()) {
            Projectile p = it.next();
            if (p.dead) {
                it.remove();
                continue;
            }
            if (!p.display.isValid()) {
                // 표시 엔티티가 사라져도 무기는 잃지 않음
                land(a, p, p.pos);
                it.remove();
                continue;
            }
            p.age++;
            Vec3 step = p.vel;
            double len = step.length();
            Vec3 dir = step.mul(1 / len);
            boolean stop = false;
            Vec3 stopAt = p.pos.add(step);
            // 블록
            RayTraceResult r = a.world.rayTraceBlocks(Fx.loc(a.world, p.pos), new Vector(dir.x(), dir.y(), dir.z()), len, FluidCollisionMode.NEVER, true);
            double blockDist = len;
            Door doorHit = null;
            if (r != null && r.getHitBlock() != null) {
                Block b = r.getHitBlock();
                Vector hp = r.getHitPosition();
                Vec3 hit = new Vec3(hp.getX(), hp.getY(), hp.getZ());
                if (GlassService.isGlass(b.getType())) {
                    plugin.glass().shatter(a, b, dir); // 관통
                } else {
                    blockDist = p.pos.distance(hit);
                    stop = true;
                    stopAt = hit.sub(dir.mul(0.15));
                    if (b.getType() == Material.BARRIER) doorHit = a.doorAt(b.getX(), b.getY(), b.getZ());
                }
            }
            for (Door d : a.doors) {
                if (d.barrierPlaced) continue;
                double t = d.obb().rayIntersect(p.pos, dir, blockDist);
                if (t >= 0 && t < blockDist) {
                    blockDist = t;
                    doorHit = d;
                    stop = true;
                    stopAt = p.pos.add(dir.mul(Math.max(0, t - 0.15)));
                }
            }
            // 개체
            Combatant victim = null;
            double vd = blockDist;
            for (Combatant c : a.combatants.values()) {
                if (c == p.thrower && p.age < 6) continue;
                if (!c.state.canBeHit()) continue;
                Aabb box = c.state.isDownedLike() ? Hitbox.downed(c.feet(), c.scale()) : Hitbox.body(c.feet(), c.scale()).grow(0.18);
                double t = box.rayIntersect(p.pos, dir, vd);
                if (t >= 0 && t < vd) {
                    vd = t;
                    victim = c;
                }
            }
            if (victim != null) {
                Vec3 hitPoint = p.pos.add(dir.mul(vd));
                throwHit(p, victim, dir, hitPoint);
                stop = true;
                stopAt = hitPoint.sub(dir.mul(0.3));
            } else if (doorHit != null) {
                doorHit.pushAlong(dir, 14, p.thrower, false);
                plugin.fx().sound(a.world, stopAt, "violence:world.door_hit", 1f, 1.1f);
            } else if (stop) {
                plugin.fx().sound(a.world, stopAt, "violence:weapon.land", 1f, 1f);
            }
            if (stop || p.age > 80) {
                land(a, p, stopAt);
                it.remove();
                continue;
            }
            p.pos = p.pos.add(step);
            p.vel = p.vel.add(0, -THROW_GRAVITY, 0).mul(0.99);
            p.spin += 0.9f;
            p.display.teleport(Fx.loc(a.world, p.pos));
            p.display.setInterpolationDelay(0);
            p.display.setInterpolationDuration(1);
            Quaternionf q = new Quaternionf().rotateY((float) Math.toRadians(-dir.yaw())).rotateX(p.spin);
            p.display.setTransformation(new Transformation(new Vector3f(), q, new Vector3f(0.8f, 0.8f, 0.8f), new Quaternionf()));
        }
    }

    private void land(Arena a, Projectile p, Vec3 at) {
        a.tracked.remove(p.display);
        p.display.remove();
        p.dead = true;
        if (p.weapon.type().id().equals("bottle")) {
            // 유리병은 깨진다
            plugin.fx().glassShards(a, at, p.vel.normalize());
            plugin.fx().sound(a.world, at, "violence:world.glass_break", 1f, 1.4f);
            return;
        }
        Vec3 floor = plugin.ground().floorBelow(a, at.add(0, 0.2, 0));
        if (floor == null) floor = plugin.ground().reachableSpot(a, at);   // 창밖/허공으로 던진 무기 → 가까운 바닥
        if (floor == null) return;
        plugin.ground().spawn(a, p.weapon, floor, plugin.random().nextFloat() * 360);
    }

    private void throwHit(Projectile p, Combatant v, Vec3 dir, Vec3 point) {
        WeaponType t = p.weapon.type();
        Combatant thrower = p.thrower;
        v.lastAttacker = thrower;
        plugin.fx().sound(v.world(), point, "violence:melee.blunt_hit", 1.2f, 1.2f);
        boolean lethal = v.state.isDownedLike()
                || (thrower != null && thrower.mask == Mask.JAKE)
                || plugin.random().nextDouble() < t.throwKillChance();
        if (lethal) {
            plugin.fx().blood(arena(), point, dir, 3);
            kill(v, thrower, KillType.THROW, dir, false);
        } else {
            plugin.fx().blood(arena(), point, dir, 1);
            knockdown(v, dir, thrower, false);
        }
    }

    // ───────────────────────────── Space ─────────────────────────────

    /** Space: 쓰러진 적 올라타기 > 문 발차기 > 가면 능력 */
    public void space(Combatant c, long now) {
        Arena a = arena();
        if (a == null || !c.canAct(now) || now < c.spaceReadyAt) return;
        Combatant downed = downedNear(a, c);
        if (downed != null) {
            startExecution(c, downed, now);
            return;
        }
        Door door = plugin.doors().doorInFront(a, c, 1.9);
        if (door != null) {
            kick(c, door, now);
            return;
        }
        plugin.masks().onSpace(c, now);
    }

    private Combatant downedNear(Arena a, Combatant c) {
        Combatant best = null;
        double bd = 2.0;
        Vec3 f = c.feet();
        Vec3 look = c.look().horizontal().normalize();
        for (Combatant o : a.combatants.values()) {
            if (o == c || o.state != CombatState.DOWNED) continue;
            if (Math.abs(o.feet().y() - f.y()) > 1.0) continue;
            Vec3 to = o.feet().sub(f).horizontal();
            double d = to.length();
            // 바로 위(1.1 이내)이거나 정면 2블록 이내
            if (d > 1.1 && (d > 2.0 || to.normalize().dot(look) < 0.3)) continue;
            // 벽이나 닫힌 문 너머로 올라타지 못하게
            if (!lineOfSight(a, c.eye(), o.feet().add(0, 0.3, 0))) continue;
            if (d < bd) {
                bd = d;
                best = o;
            }
        }
        return best;
    }

    private void kick(Combatant c, Door door, long now) {
        c.actionLockUntil = now + 10;
        c.moveLockUntil = now + 10;
        c.spaceReadyAt = now + 12;
        c.entity().swingOffHand();
        c.feelImpact(0.25);
        plugin.fx().sound(c.world(), c.eye(), "violence:melee.kick", 1f, 1f);
        c.applyStateVisuals();
        Arena a = arena();
        plugin.laterIn(a, 4, () -> {
            if (c.state == CombatState.ALIVE && a.combatants.containsKey(c.id)) {
                plugin.doors().kick(door, c);
                c.feelImpact(0.45);
            }
        });
        plugin.laterIn(a, 11, () -> {
            if (a.combatants.containsKey(c.id)) c.applyStateVisuals();
        });
    }

    // ───────────────────────────── 쓰러짐 ─────────────────────────────

    public void knockdown(Combatant v, Vec3 dir, Combatant attacker, boolean byFist) {
        long now = plugin.now();
        if (!v.isAlive() || v.state.isDownedLike()) return;
        if (v.state == CombatState.EXECUTING && v.execution != null) cancelExecution(v.execution);
        v.lastAttacker = attacker;
        dropWeapons(v, dir);
        v.downedUntil = now + DOWNED_TICKS;
        v.setState(CombatState.DOWNED, now);
        v.feelImpact(0.5);
        plugin.fx().sound(v.world(), v.eye(), "violence:hit.knockdown", 1.2f, 1f);
        v.refreshEquipment();
        // 넘어지는 동작: 언제나 뒤로 넘어지며 공격 방향으로 밀려남 (샷건이면 팔을 벌리고 날아감).
        // 뒤쪽 벽에 부딪히면 벽에 기대 앉아 기절 (밀려나지 않음)
        boolean wall = plugin.falls().knockdown(v, dir, now - v.strongHitTick <= 1);
        if (!wall) v.knockback(dir.horizontal().normalize(), byFist ? 0.55 : 0.8);
    }

    private void standUp(Combatant v, long now) {
        v.lastAttacker = null;     // 일어난 뒤 한참 지나 떨어져 죽어도 예전 공격자에게 킬이 가지 않게
        v.hp = Combatant.MAX_HP;
        v.actionLockUntil = now + STANDUP_LOCK;
        v.setState(CombatState.ALIVE, now);
        v.refreshEquipment();
    }

    public void dropWeapons(Combatant v, Vec3 dir) {
        Arena a = arena();
        if (v.weapon != null) {
            plugin.ground().drop(a, v.weapon, v.feet(), dir);
            v.weapon = null;
        }
        v.offhand = null;
        if (v.stashedWeapon != null) {
            plugin.ground().drop(a, v.stashedWeapon, v.feet(), dir.mul(-1));
            v.stashedWeapon = null;
        }
    }

    // ───────────────────────────── 처형 ─────────────────────────────

    public void startExecution(Combatant ex, Combatant victim, long now) {
        Execution e = new Execution(ex, victim);
        WeaponType t = ex.weaponType(fist());
        e.fast = ex.mask != null && ex.mask.fastExecution();
        if (t.isGun()) {
            if (ex.mask == Mask.DETECTIVE && ex.weapon.hasAmmo()) {
                e.style = ExecutionStyle.GUN_SHOT;
            } else {
                // 총기: 무기를 바닥에 버리고 맨손으로 교체
                plugin.ground().drop(arena(), ex.weapon, ex.feet(), ex.look());
                ex.weapon = null;
                ex.offhand = null;
                t = fist();
                e.style = ExecutionStyle.HITS;
            }
        } else if (t.isThrowable()) {
            plugin.ground().drop(arena(), ex.weapon, ex.feet(), ex.look());
            ex.weapon = null;
            t = fist();
            e.style = ExecutionStyle.HITS;
        } else {
            e.style = t.execution();
        }
        if (t.isFist() && ex.mask == Mask.TONY) e.style = ExecutionStyle.AUTO;
        // 벽에 기대 기절한 적: 무기와 상관없이 머리를 발로 차서 처형
        boolean wallKick = plugin.falls().wallStunned(victim);
        if (wallKick) e.style = ExecutionStyle.WALL_KICK;
        e.bikerStyle = ex.mask == Mask.BIKER && t.id().equals("cleaver");
        e.hitsLeft = t.isFist() ? fist().executionHits() : t.executionHits();
        if (e.fast) e.hitsLeft = Math.max(1, e.hitsLeft / 2);
        e.startTick = now;
        int autoTicks = e.bikerStyle ? 22 : 16;
        e.finishTick = now + (e.fast ? autoTicks / 2 : autoTicks);
        if (e.style == ExecutionStyle.GUN_SHOT) e.finishTick = now + (e.fast ? 6 : 12);
        int contact = plugin.falls().pose(dev.violence.fx.FallPose.Kind.KICK) == null ? 3
                : Math.max(1, plugin.falls().pose(dev.violence.fx.FallPose.Kind.KICK).contact());
        if (e.style == ExecutionStyle.WALL_KICK) e.finishTick = now + contact + 1;
        e.nextHitReady = now + 3;
        e.victimDownedRemaining = Math.max(20, victim.downedUntil - now);
        ex.execution = e;
        victim.execution = e;
        ex.setState(CombatState.EXECUTING, now);
        victim.setState(CombatState.BEING_EXECUTED, now);
        Vec3 vf = victim.feet();
        Vec3 face = vf.sub(ex.feet()).horizontal().normalize();
        if (face.lengthSq() < 0.01) face = ex.look().horizontal().normalize();
        Vec3 camPos;
        Vec3 camLook;
        if (wallKick) {
            // 처형자를 기절한 적 앞(벽 반대쪽)에 세우고 발차기 인형
            Vec3 out = plugin.falls().wallFacing(victim);
            if (out == null) out = face.mul(-1);
            face = out.mul(-1);
            Location front = Fx.loc(arena().world, vf.add(out.mul(0.6 * victim.scale())));   // 뻗은 다리 위에 서서
            front.setYaw((float) face.yaw());
            front.setPitch(25);
            ex.teleport(front);
            ex.actionLockUntil = now + 12;
            ex.moveLockUntil = now + 12;
            // 카메라: 옆에서 (발차기와 벽이 함께 보이게)
            Vec3 side = out.cross(Vec3.UP).normalize();
            Vec3 mid = vf.add(out.mul(0.5));
            camPos = mid.add(side.mul(2.4)).add(out.mul(0.9)).add(0, 1.3, 0);
            camLook = mid.add(0, 0.8, 0);
        } else {
            // 처형자를 피처형자 위로 이동
            Location onTop = Fx.loc(arena().world, vf.add(face.mul(-0.25)).add(0, 0.05, 0));
            onTop.setYaw((float) face.yaw());
            onTop.setPitch(55);
            ex.teleport(onTop);
            // 카메라: 처형자의 살짝 뒤, 위
            camPos = vf.sub(face.mul(1.9)).add(0, 2.5, 0);
            camLook = vf.add(0, 0.4, 0);
        }
        ex.history.clear();   // 순간 이동한 앞쪽 위치로 판정되지 않게
        ex.refreshEquipment();
        // 발차기 인형은 장비를 다시 보낸 뒤에 시작 (실제 몸과 손 아이템을 숨김)
        if (wallKick) plugin.falls().kick(ex, (float) face.yaw());
        ItemDisplay cam = null;
        if (ex.isPlayer() || victim.isPlayer()) {
            Vec3 lookDir = camLook.sub(camPos).normalize();
            Location cl = Fx.loc(arena().world, camPos);
            cl.setYaw((float) lookDir.yaw());
            cl.setPitch((float) lookDir.pitch());
            cam = plugin.camera().spawnCamera(cl, 3);
        }
        ex.onExecutionStart(e, cam);
        victim.onExecutionStart(e, cam);
        plugin.fx().sound(ex.world(), vf, "violence:melee.mount", 1f, 1f);
        executions.add(e);
        if (wallKick) {
            plugin.laterIn(arena(), contact, () -> {
                if (ex.execution == e) wallKickStrike(e);
            });
        }
        if (e.style == ExecutionStyle.AUTO) {
            // 자동 처형 중간 타격 연출
            int strikes = e.bikerStyle ? 3 : 1;
            long span = e.finishTick - now;
            for (int i = 1; i <= strikes; i++) {
                long at = (span * i) / (strikes + 1);
                plugin.laterIn(arena(), (int) Math.max(1, at), () -> {
                    if (ex.execution == e) executionStrike(e, false);
                });
            }
        }
    }

    /** 처형 중 왼클릭 */
    public void executionClick(Combatant ex, long now) {
        Execution e = ex.execution;
        if (e == null || e.executor != ex) return;
        if (e.style != ExecutionStyle.HITS || now < e.nextHitReady) return;
        e.nextHitReady = now + (e.fast ? 3 : 6);
        e.hitsLeft--;
        executionStrike(e, e.hitsLeft <= 0);
        if (e.hitsLeft <= 0) finishExecution(e);
    }

    private void executionStrike(Execution e, boolean finalBlow) {
        Combatant ex = e.executor;
        Combatant v = e.victim;
        ex.entity().swingMainHand();
        if (ex instanceof PlayerCombatant pce) pce.playAnim(WeaponItems.animGroup(ex.weaponType(fist())), 7);
        Vec3 p = v.feet().add(0, 0.35, 0);
        WeaponType t = ex.weaponType(fist());
        String snd = t.isFist() ? "violence:melee.punch_hit" : (sharp(t) ? "violence:melee.slash_hit" : "violence:melee.blunt_hit");
        plugin.fx().sound(ex.world(), p, snd, 1.3f, finalBlow ? 0.8f : 1f);
        plugin.fx().blood(arena(), p, new Vec3(0, -1, 0).add(ex.look().mul(0.3)), finalBlow ? 4 : 2);
        ex.feelImpact(finalBlow ? 0.7 : 0.4);
        v.feelImpact(finalBlow ? 0.8 : 0.5);
    }

    /** 발이 머리에 닿음: 머리가 벽에 부딪히고 벽과 바닥에 피 */
    private void wallKickStrike(Execution e) {
        Combatant ex = e.executor;
        Combatant v = e.victim;
        Vec3 head = plugin.falls().wallHead(v);
        Vec3 out = plugin.falls().wallFacing(v);
        if (head == null || out == null) return;
        plugin.falls().snapHead(v);
        plugin.fx().sound(ex.world(), head, "violence:melee.kick", 1.4f, 0.8f);
        plugin.fx().sound(ex.world(), head, "violence:melee.blunt_hit", 1.4f, 0.7f);
        plugin.fx().blood(arena(), head, out.mul(-1).add(0, 0.15, 0), 4);
        ex.feelImpact(0.6);
        v.feelImpact(0.9);
    }

    private void finishExecution(Execution e) {
        long now = plugin.now();
        executions.remove(e);
        Combatant ex = e.executor;
        Combatant v = e.victim;
        if (e.style == ExecutionStyle.GUN_SHOT && ex.weapon != null) {
            ex.weapon.consume(now);
            plugin.fx().sound(ex.world(), v.eye(), ex.weapon.type().sound(), 2.5f, 0.9f);
            plugin.fx().muzzle(arena(), ex.eye(), v.feet().sub(ex.eye()).normalize(), false);
        }
        if (e.style != ExecutionStyle.HITS && e.style != ExecutionStyle.WALL_KICK) executionStrike(e, true);
        ex.execution = null;
        v.execution = null;
        ex.actionLockUntil = now + 4;
        ex.setState(CombatState.ALIVE, now);
        ex.onExecutionEnd(e);
        kill(v, ex, KillType.EXECUTION, new Vec3(0, -1, 0), false);
        ex.refreshEquipment();
    }

    /** 처형 취소 (우클릭으로 내림 / 처형자가 공격받음) */
    public void cancelExecution(Execution e) {
        if (e == null) return;
        long now = plugin.now();
        executions.remove(e);
        Combatant ex = e.executor;
        Combatant v = e.victim;
        ex.execution = null;
        v.execution = null;
        if (ex.state == CombatState.EXECUTING) {
            ex.actionLockUntil = now + 3;
            ex.setState(CombatState.ALIVE, now);
        }
        ex.onExecutionEnd(e);
        if (v.state == CombatState.BEING_EXECUTED) {
            v.downedUntil = now + e.victimDownedRemaining;
            v.setState(CombatState.DOWNED, now);
        }
        v.onExecutionEnd(e);
    }

    // ───────────────────────────── 사망 / 리스폰 ─────────────────────────────

    public void kill(Combatant v, Combatant killer, KillType type, Vec3 dir, boolean headshot) {
        long now = plugin.now();
        if (v.state == CombatState.DEAD) return;
        Arena a = arena();
        if (a == null) return;
        // 이미 나간 플레이어/교체된 NPC 에게는 킬을 주지 않음
        if (killer != null && !a.combatants.containsKey(killer.id)) killer = null;
        if (v.execution != null) {
            Execution e = v.execution;
            if (e.executor == v) cancelExecution(e);
            else {
                executions.remove(e);
                e.executor.execution = null;
                v.execution = null;
                if (e.executor.state == CombatState.EXECUTING) {
                    e.executor.setState(CombatState.ALIVE, now);
                    e.executor.onExecutionEnd(e);
                }
                v.onExecutionEnd(e);
            }
        }
        dropWeapons(v, dir);
        v.hp = 0;
        v.deaths++;
        v.streak.reset();
        v.mask = null;
        v.bulletShield = 0;
        v.respawnAt = now + RESPAWN_TICKS;
        Vec3 deathPos = v.feet();
        v.setState(CombatState.DEAD, now);
        plugin.fx().bloodPool(a, deathPos, type == KillType.EXECUTION || headshot ? 1.6f : 1.1f);
        plugin.fx().sound(v.world(), deathPos, "violence:hit.death", 1.2f, 0.9f + plugin.random().nextFloat() * 0.2f);
        plugin.corpses().spawn(a, v, dir, type == KillType.EXECUTION);
        v.onDeath(killer, dir, now);
        v.refreshEquipment();
        if (killer != null && killer != v) plugin.game().onKill(killer, v, type, headshot, deathPos);
        else plugin.game().onSuicide(v);
    }

    private void respawn(Combatant v, long now) {
        Vec3 spot = plugin.spawns().choose(arena(), v);
        Location l = Fx.loc(arena().world, spot);
        l.setYaw(plugin.random().nextFloat() * 360);
        v.teleport(l);
        v.hp = Combatant.MAX_HP;
        v.weapon = null;
        v.offhand = null;
        v.respawnAt = -1;
        v.lastAttacker = null;
        v.history.clear();
        v.actionLockUntil = now + 4;
        v.setState(CombatState.ALIVE, now);
        v.refreshEquipment();
        v.onRespawn(now);
    }

    // ───────────────────────────── 틱 ─────────────────────────────

    public void tick(long now) {
        Arena a = arena();
        if (a == null) return;
        for (Combatant c : new ArrayList<>(a.combatants.values())) {
            if (c.state != CombatState.DEAD) c.history.record(c.feet(), c.state.isDownedLike());
            switch (c.state) {
                case DOWNED -> {
                    if (now >= c.downedUntil) standUp(c, now);
                }
                case DEAD -> {
                    if (c.respawnAt >= 0 && now >= c.respawnAt) respawn(c, now);
                }
                default -> {
                }
            }
            // 임시 무기가 처형/빼앗기 등으로 사라졌으면 숨겨 둔 원래 무기를 돌려줌
            if (c.weapon == null && c.stashedWeapon != null && c.state == CombatState.ALIVE) {
                c.weapon = c.stashedWeapon;
                c.stashedWeapon = null;
                c.refreshEquipment();
            }
            // 가면 임시 무기 만료
            if (c.weapon != null && c.weapon.expireTick() > 0 && now >= c.weapon.expireTick()) {
                c.weapon = c.stashedWeapon;
                c.stashedWeapon = null;
                c.offhand = null;
                c.refreshEquipment();
            }
        }
        for (Execution e : new ArrayList<>(executions)) {
            if (!e.executor.isAlive() || !e.victim.isAlive()) {
                executions.remove(e);
                continue;
            }
            if ((e.style == ExecutionStyle.AUTO || e.style == ExecutionStyle.GUN_SHOT || e.style == ExecutionStyle.WALL_KICK)
                    && now >= e.finishTick) finishExecution(e);
            else if (e.style == ExecutionStyle.HITS && now - e.startTick > EXECUTION_TIMEOUT) cancelExecution(e);
        }
        tickProjectiles(a, now);
    }

    public void cancelAllExecutions() {
        for (Execution e : new ArrayList<>(executions)) {
            try {
                cancelExecution(e);
            } catch (RuntimeException ex) {
                executions.remove(e);
            }
        }
    }

    public void clear() {
        for (Projectile p : projectiles) if (p.display != null) p.display.remove();
        projectiles.clear();
        executions.clear();
    }

    public List<Execution> executions() { return executions; }
}
