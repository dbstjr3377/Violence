package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.math.Vec3;
import dev.violence.npc.NpcCombatant;
import dev.violence.player.PlayerCombatant;
import io.papermc.paper.datacomponent.DataComponentTypes;
import io.papermc.paper.datacomponent.item.CustomModelData;
import io.papermc.paper.datacomponent.item.ResolvableProfile;
import java.awt.image.BufferedImage;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import net.kyori.adventure.key.Key;
import org.bukkit.Color;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mannequin;
import org.bukkit.entity.Player;
import org.bukkit.entity.Pose;
import org.bukkit.inventory.EntityEquipment;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.FluidCollisionMode;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3d;
import org.joml.Vector3f;

/**
 * 쓰러지거나 죽을 때 넘어지는 동작 (fall.json, FallPose).
 *
 * 맞은 방향으로 밀려나되 언제나 뒤로 넘어진다. 등 뒤나 옆에서 맞으면 처음 3프레임에 걸쳐 맞은 쪽으로 돌아서며 넘어진다.
 * 샷건처럼 강한 공격이면 두 팔을 벌리고 뒤로 날아간다. 넘어지는 쪽(뒤)에 벽이 있으면 벽에 부딪혀 미끄러져 내려와
 * 벽에 등을 기댄 채 앉아 기절한다(벽 기절: 움직이지 못함, 처형하면 머리 발차기, 총·근접 무기로도 죽일 수 있음).
 *
 * 1) 넘어지는 동안: 실제 몸과 장비를 숨기고, 같은 크기·색의 6부위 인형(아이템 디스플레이)이 20fps 키프레임으로 넘어진다.
 * 2) 넘어진 뒤: 인형 대신 같은 스킨·장비의 마네킹(대역)이 같은 자세를 잡는다.
 *    등으로 누움 = 침대 없는 SLEEPING, 벽에 기대 앉음 = 보이지 않는 디스플레이에 탄 자세(머리를 숙임).
 *    쓰러져 있는 동안 실제 몸은 숨긴 채 위치만 따라가고(기어가면 대역도 따라감), 일어서면 대역을 치우고 실제 몸을 보인다.
 * 3) 죽으면: 누운 대역은 그대로 시체가 되고, 벽에 기대 있던 대역은 벽 아래로 미끄러져 눕는 동작(전용 사망 모션) 뒤 시체가 된다.
 *    쓰러지지 않고 바로 죽어도 같은 순서로 넘어져 시체가 된다(벽 앞이면 벽에 기대 앉은 시체). 처형당한 시체는 머리에서 피가 흐른다.
 * 4) 처형자 발차기: 벽 기절 처형 때 처형자의 실제 몸을 잠깐 숨기고 인형이 발차기를 한다.
 *
 * 색: 플레이어는 스킨 그림에서 얼굴·머리카락·옷·바지·신발 색을 뽑아 쓰고(처음 한 번 내려받음), NPC 는 옷 색을 쓴다.
 * 가면을 쓰고 있으면 인형 머리 대신 가면 모델을 씌운다.
 */
public final class FallService {
    private static final EquipmentSlot[] SLOTS = {EquipmentSlot.HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.HEAD,
            EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};
    /** 기본 색: 피부, 머리카락, 윗옷, 바지, 신발 */
    /** 쓰고 있는 가면을 머리에 씌울 때 크기 (머리 칸 아이템 = 0.625 블록) */
    private static final float MASK_SCALE = 0.625f;
    /** 뒤쪽 벽을 찾는 거리 (넘어지며 밀려나는 거리) */
    private static final double WALL_REACH = 1.7;

    private final ViolencePlugin plugin;
    private final Map<FallPose.Kind, FallPose> poses;
    /** 쓰러져 있는 (살아 있는) 대상 */
    private final Map<UUID, Lying> downed = new HashMap<>();
    /** 발차기 중인 처형자 */
    private final Map<UUID, Lying> acting = new HashMap<>();
    /** 처형 중 (처형자 id) */
    private final Map<UUID, ExecAct> execs = new HashMap<>();
    private final ExecutionAnims execAnims;

    /** 처형 동작: 처형자 인형(+무기)과 피처형자 인형 */
    private static final class ExecAct {
        final Combatant ex;
        final Combatant victim;
        final Arena arena;
        final ExecutionAnims.Anim anim;
        final Lying exPuppet;
        final Lying vPuppet;
        final Lying vLying;
        ItemDisplay weapon;
        double[] grip;
        ItemStack[] victimEquip;
        boolean victimReleased;
        /** 0 = 대기(ready), 1 = 한 번 치기(strike), 2 = 전체(full) */
        int mode;
        int tick;
        boolean ending;

        ExecAct(Combatant ex, Combatant victim, Arena arena, ExecutionAnims.Anim anim, Lying exPuppet, Lying vPuppet, Lying vLying) {
            this.ex = ex;
            this.victim = victim;
            this.arena = arena;
            this.anim = anim;
            this.exPuppet = exPuppet;
            this.vPuppet = vPuppet;
            this.vLying = vLying;
        }

        ExecutionAnims.Track exTrack() {
            return mode == 0 ? anim.readyExec() : mode == 1 ? anim.strikeExec() : anim.fullExec();
        }

        ExecutionAnims.Track vTrack() {
            return mode == 0 ? anim.readyVictim() : mode == 1 ? anim.strikeVictim() : anim.fullVictim();
        }
    }
    /** 넘어지는 중인 시체 */
    private final List<Lying> falling = new ArrayList<>();

    private static final class Lying {
        final Combatant victim;
        final Arena arena;
        final FallPose.Kind kind;
        FallPose pose;
        /** 넘어지기 전 몸 방향 → 넘어지는 방향(맞은 쪽을 봄) */
        final float startYaw;
        final float yaw;
        final double scale;
        final Map<FallPose.Part, ItemDisplay> parts = new EnumMap<>(FallPose.Part.class);
        ItemDisplay mask;
        Mannequin body;
        /** 앉은 대역이 타는 보이지 않는 디스플레이 */
        ItemDisplay seat;
        /** 시작 위치(발) → 끝 위치(발). 살아서 뒤로 넘어지면 실제 몸을 따라감 */
        Location start;
        Location end;
        boolean follow;
        boolean corpse;
        boolean execution;
        boolean revealed;
        /** 시체 피 웅덩이 크기 (0 = 없음)와 나오는 부위 (맞은 곳) */
        float poolSize;
        /** 대역을 마지막으로 옮긴 틱 (밀려나며 미끄러짐), 없으면 -1 */
        int lastMove = -1;
        FallPose.Part poolPart = FallPose.Part.BODY;
        int tick;

        Lying(Combatant victim, Arena arena, FallPose.Kind kind, FallPose pose, float startYaw, float yaw) {
            this.victim = victim;
            this.arena = arena;
            this.kind = kind;
            this.pose = pose;
            this.startYaw = startYaw;
            this.yaw = yaw;
            this.scale = victim.scale();
        }

        Location anchor(int frame) {
            double t = follow ? 1.0 : pose.frame(frame).travel();
            Location l = start.clone();
            l.add(end.clone().subtract(start).toVector().multiply(t));
            return l;
        }

        float yawAt(int frame) {
            return kind == FallPose.Kind.WALL_DEATH || kind == FallPose.Kind.KICK ? yaw : FallPose.spinYaw(startYaw, yaw, frame);
        }
    }

    public FallService(ViolencePlugin plugin) {
        this.plugin = plugin;
        Map<FallPose.Kind, FallPose> p;
        try {
            p = FallPose.loadAll();
        } catch (RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "fall.json 읽기 실패 - 넘어지는 동작 없이 바로 눕습니다: " + e);
            p = null;
        }
        this.poses = p;
        ExecutionAnims ea;
        try {
            ea = ExecutionAnims.load();
        } catch (RuntimeException e) {
            plugin.getLogger().log(Level.WARNING, "execution.json 읽기 실패 - 처형 동작 없이 진행합니다: " + e);
            ea = null;
        }
        this.execAnims = ea;
    }

    public ExecutionAnims execAnims() { return execAnims; }

    /** 실제 몸을 숨기고 대역(인형/마네킹)을 보여주는 중인지 (쓰러짐, 처형 발차기) */
    public boolean hiding(Combatant c) {
        return downed.containsKey(c.id) || acting.containsKey(c.id) || execs.containsKey(c.id);
    }

    public FallPose pose(FallPose.Kind k) {
        return poses == null ? null : poses.get(k);
    }

    // ───────── 시작 ─────────

    /**
     * 쓰러진 직후 호출 (상태는 이미 DOWNED). push = 밀려나는 방향, strong = 샷건 등 강한 공격.
     * 뒤쪽에 벽이 있어 벽에 기대 앉게 되면 true (실제 몸은 앉을 자리로 옮기고 밀려나지 않게 함).
     */
    public boolean knockdown(Combatant c, Vec3 push, boolean strong) {
        Arena a = plugin.arena();
        LivingEntity e = c.entity();
        if (poses == null || a == null || e == null || !e.isValid() || c.state != CombatState.DOWNED || downed.containsKey(c.id)) return false;
        Lying l = create(a, c, push, strong, e.getLocation(), false);
        if (l == null) return false;
        downed.put(c.id, l);
        e.setInvisible(true);
        sendEquipment(a, c, true);
        if (l.kind == FallPose.Kind.WALL) {
            Location sit = l.end.clone();
            sit.setYaw(e.getLocation().getYaw());
            sit.setPitch(e.getLocation().getPitch());
            c.teleport(sit);
            e.setVelocity(new Vector());
            return true;
        }
        l.follow = true;
        return false;
    }

    /** 벽에 기대 기절해 있는지 */
    public boolean wallStunned(Combatant c) {
        Lying l = downed.get(c.id);
        return l != null && l.kind == FallPose.Kind.WALL;
    }

    /** 벽 기절한 대상의 머리 위치 (발차기 처형, 피) */
    public Vec3 wallHead(Combatant c) {
        Lying l = downed.get(c.id);
        if (l == null || l.kind != FallPose.Kind.WALL) return null;
        return headWorld(l, l.pose.frameCount() - 1, l.end);
    }

    /**
     * 쓰러져 있는(누운·벽에 기댄) 대상의 머리 위치 (지금 보이는 인형 프레임 또는 대역 자세 기준). 없으면 null.
     * 머리를 때리는 처형·공격의 피와 소리가 여기서 나온다.
     */
    public Vec3 head(Combatant c) {
        Lying l = downed.get(c.id);
        if (l == null) return null;
        int frame = Math.min(l.tick, l.pose.frameCount() - 1);
        return headWorld(l, frame, l.anchor(frame));
    }

    /** 벽 기절한 대상이 보는 방향 (벽 반대쪽, 수평 단위 벡터) */
    public Vec3 wallFacing(Combatant c) {
        Lying l = downed.get(c.id);
        if (l == null) return null;
        Vector f = forward(l.yaw);
        return new Vec3(f.getX(), 0, f.getZ());
    }

    /** 벽 기절 발차기 처형: 머리가 벽 쪽으로 젖혀짐 */
    public void snapHead(Combatant c) {
        Lying l = downed.get(c.id);
        if (l == null || l.body == null || !l.body.isValid()) return;
        l.body.setRotation(l.body.getLocation().getYaw(), -25f);
    }

    /**
     * 죽은 자리의 시체 (CorpseService 가 수명 관리). 쓰러져 누워 있던 대역은 그대로 시체가 되고,
     * 벽에 기대 있던 대역은 벽 아래로 미끄러져 눕는다. 대역이 없으면 넘어지는 동작부터 보여준다. 만들 수 없으면 null.
     * execution 이면 자리를 잡은 뒤 머리에서 피가 흐른다.
     */
    public Mannequin corpse(Arena a, Combatant v, Vec3 push, boolean strong, boolean execution) {
        return corpse(a, v, push, strong, execution, 0f, false);
    }

    /** poolSize > 0 이면 자리를 잡은 뒤 맞은 부위(head = 머리, 아니면 몸통) 밑에서 피 웅덩이가 퍼짐 (시체에 붙음) */
    public Mannequin corpse(Arena a, Combatant v, Vec3 push, boolean strong, boolean execution, float poolSize, boolean head) {
        // 처형 중에 죽으면 피처형자 인형을 치우고 누운 대역(=시체)을 다시 보임 (처형자 인형은 동작을 마저 함)
        for (ExecAct act : execs.values()) {
            if (act.victim == v) releaseVictim(act);
        }
        Lying l = downed.remove(v.id);
        if (l != null) {
            // 실제 몸은 죽어서 숨겨진 상태 → 다음 틱에 실제 장비(죽으며 비워짐)를 다시 보냄
            plugin.laterIn(a, 1, () -> {
                if (a.combatants.containsKey(v.id)) sendEquipment(a, v, false);
            });
            if (l.kind == FallPose.Kind.WALL && poses != null) {
                // 전용 사망 모션: 앉은 자세에서 벽 아래로 미끄러져 누움
                Lying d = new Lying(v, a, FallPose.Kind.WALL_DEATH, poses.get(FallPose.Kind.WALL_DEATH), l.yaw, l.yaw);
                d.start = l.end.clone();
                d.end = d.start.clone().add(forward(l.yaw).multiply(0));
                d.corpse = true;
                d.execution = execution;
                d.poolSize = poolSize;
                d.poolPart = head ? FallPose.Part.HEAD : FallPose.Part.BODY;
                if (spawnPuppet(a, v, d)) {
                    end(l, false);
                    d.body = spawnDouble(a, v, d);
                    place(d, 0, false);
                    falling.add(d);
                    return d.body;
                }
            }
            l.corpse = true;
            l.follow = false;
            l.execution = execution;
            l.poolSize = poolSize;
            l.poolPart = head ? FallPose.Part.HEAD : FallPose.Part.BODY;
            l.start = l.end = l.anchor(l.pose.frameCount() - 1);
            if (l.revealed) {
                bleed(l);
            } else {
                falling.add(l);
            }
            return l.body;
        }
        if (poses == null || v.entity() == null) return null;
        Location at = v.entity().getLocation();
        l = create(a, v, push, strong, at, true);
        if (l == null) return null;
        l.corpse = true;
        l.execution = execution;
        l.poolSize = poolSize;
        l.poolPart = head ? FallPose.Part.HEAD : FallPose.Part.BODY;
        falling.add(l);
        return l.body;
    }

    // ───────── 처형 동작 ─────────

    /**
     * 처형 동작 시작. 처형자는 at(발 위치)에서 yaw(누운 적의 머리 쪽)를 보고, 인형이 동작을 한다.
     * 피처형자는 누운 대역 대신 인형이 머리·팔을 움직인다. weapon 이 있으면 처형자 오른손에 들림.
     * 등으로 누운 대역이 없으면(벽 기절 등) false.
     */
    public boolean startExec(Combatant ex, Combatant victim, String animName, dev.violence.weapon.WeaponType weapon, Location at, float yaw) {
        Arena a = plugin.arena();
        LivingEntity e = ex.entity();
        Lying vl = downed.get(victim.id);
        ExecutionAnims.Anim anim = execAnims == null ? null : execAnims.get(animName);
        if (a == null || e == null || anim == null || vl == null || vl.pose.end() != FallPose.End.FACE_UP || execs.containsKey(ex.id)) return false;
        int mode = anim.hits() ? 0 : 2;
        ExecutionAnims.Track et = mode == 0 ? anim.readyExec() : anim.fullExec();
        ExecutionAnims.Track vt = mode == 0 ? anim.readyVictim() : anim.fullVictim();
        Lying exP = new Lying(ex, a, FallPose.Kind.KICK, et.pose(), yaw, yaw);
        exP.start = exP.end = feet(at);
        Location vAt = vl.anchor(vl.pose.frameCount() - 1);
        Lying vP = new Lying(victim, a, FallPose.Kind.KICK, vt.pose(), vl.yaw, vl.yaw);
        vP.start = vP.end = vAt;
        if (!spawnPuppet(a, ex, exP)) return false;
        if (!spawnPuppet(a, victim, vP)) {
            removePuppet(exP);
            return false;
        }
        ExecAct act = new ExecAct(ex, victim, a, anim, exP, vP, vl);
        act.mode = mode;
        if (!"none".equals(anim.weapon()) && weapon != null && !weapon.isFist()) {
            act.grip = execAnims.grip(weapon.id());
            try {
                act.weapon = a.track(a.world.spawn(exP.start, ItemDisplay.class, d -> setup(d, dev.violence.weapon.WeaponItems.create(weapon, 0))));
            } catch (RuntimeException ignored) {
                act.weapon = null;
            }
        }
        // 실제 몸 숨김: 처형자 (장비 포함), 피처형자 대역
        e.setInvisible(true);
        sendEquipment(a, ex, true);
        if (vl.body != null && vl.body.isValid()) {
            EntityEquipment eq = vl.body.getEquipment();
            act.victimEquip = new ItemStack[] {eq.getHelmet(), eq.getChestplate(), eq.getLeggings(), eq.getBoots()};
            eq.setHelmet(null);
            eq.setChestplate(null);
            eq.setLeggings(null);
            eq.setBoots(null);
            vl.body.setInvisible(true);
        }
        execs.put(ex.id, act);
        placeAct(act, 0, false);
        return true;
    }

    /** 왼클릭 처형: 한 번 치는 동작 재생. 머리에 닿는 틱(지금부터)을 돌려줌, 없으면 -1 */
    public int strike(Combatant ex) {
        ExecAct act = execs.get(ex.id);
        if (act == null || !act.anim.hits()) return -1;
        act.mode = 1;
        act.tick = 0;
        placeAct(act, 0, true);
        return act.anim.impact();
    }

    /** 처형이 끝남: 지금 동작(치기/전체)을 마저 하고 실제 몸으로 */
    public void finishExec(Combatant ex) {
        finishExec(ex, false);
    }

    /** keepCamera: 처형자가 처형 카메라로 남은 동작을 끝까지 봄 (자기 인형을 숨기지 않음) */
    public void finishExec(Combatant ex, boolean keepCamera) {
        ExecAct act = execs.get(ex.id);
        if (act == null) return;
        act.ending = true;
        if (act.mode == 0) {
            endExec(act);
            return;
        }
        // 처형 카메라가 끝나 1인칭으로 돌아온 처형자 눈에는 자기 인형이 바로 아래에 보이므로 숨김 (다른 사람은 마저 봄)
        if (!keepCamera && ex instanceof PlayerCombatant pc && pc.player().isOnline()) {
            Player p = pc.player();
            for (ItemDisplay d : act.exPuppet.parts.values()) if (d != null && d.isValid()) p.hideEntity(plugin, d);
            if (act.exPuppet.mask != null && act.exPuppet.mask.isValid()) p.hideEntity(plugin, act.exPuppet.mask);
            if (act.weapon != null && act.weapon.isValid()) p.hideEntity(plugin, act.weapon);
        }
    }

    /** 처형 취소: 바로 실제 몸으로, 피처형자 대역도 다시 보임 */
    public void cancelExec(Combatant ex) {
        ExecAct act = execs.get(ex.id);
        if (act != null) endExec(act);
    }

    /** 처형 인형이 남은 틱 수 (처형자 행동 잠금용) */
    public int execRemaining(Combatant ex) {
        ExecAct act = execs.get(ex.id);
        if (act == null) return 0;
        return Math.max(0, act.exTrack().length() - act.tick);
    }

    private void releaseVictim(ExecAct act) {
        if (act.victimReleased) return;
        act.victimReleased = true;
        removePuppet(act.vPuppet);
        Mannequin body = act.vLying.body;
        if (body != null && body.isValid()) {
            if (act.victimEquip != null) {
                EntityEquipment eq = body.getEquipment();
                eq.setHelmet(act.victimEquip[0]);
                eq.setChestplate(act.victimEquip[1]);
                eq.setLeggings(act.victimEquip[2]);
                eq.setBoots(act.victimEquip[3]);
            }
            body.setInvisible(false);
        }
    }

    private void endExec(ExecAct act) {
        execs.remove(act.ex.id);
        removePuppet(act.exPuppet);
        if (act.weapon != null && act.weapon.isValid()) act.weapon.remove();
        releaseVictim(act);
        LivingEntity e = act.ex.entity();
        if (e == null || !e.isValid() || plugin.arena() != act.arena || !act.arena.combatants.containsKey(act.ex.id)) return;
        act.ex.applyStateVisuals();
        sendEquipment(act.arena, act.ex, false);
    }

    private void tickExecs() {
        for (ExecAct act : new ArrayList<>(execs.values())) {
            LivingEntity e = act.ex.entity();
            if (e == null || !e.isValid() || plugin.arena() != act.arena || !act.arena.combatants.containsKey(act.ex.id)) {
                endExec(act);
                continue;
            }
            if (act.mode == 0) continue;
            act.tick++;
            if (act.tick >= act.exTrack().length()) {
                if (act.mode == 2 || act.ending) {
                    endExec(act);
                    continue;
                }
                act.mode = 0;
                act.tick = 0;
            }
            placeAct(act, act.tick, true);
        }
    }

    private void placeAct(ExecAct act, int frame, boolean animate) {
        ExecutionAnims.Track et = act.exTrack();
        act.exPuppet.pose = et.pose();
        int f = Math.min(frame, et.length() - 1);
        place(act.exPuppet, f, animate);
        FallPose.Placement w = act.weapon != null && act.weapon.isValid() && act.grip != null
                ? ExecutionAnims.weapon(et, f, act.exPuppet.scale, act.grip) : null;
        if (w != null) {
            Vector3d c = FallPose.toWorld(w.center(), act.exPuppet.yaw);
            // 디스플레이가 아이템을 Y180° 돌려 그리므로 미리 되돌림
            Quaternionf r = new Quaternionf(FallPose.toWorld(w.rotation(), act.exPuppet.yaw)).rotateY((float) Math.PI);
            float sc = (float) (ExecutionAnims.WEAPON_SCALE * act.exPuppet.scale);
            if (act.weapon.getLocation().distanceSquared(act.exPuppet.start) > 1e-4) act.weapon.teleport(act.exPuppet.start);
            act.weapon.setTransformation(new Transformation(new Vector3f((float) c.x, (float) c.y, (float) c.z), r,
                    new Vector3f(sc, sc, sc), new Quaternionf()));
            if (animate) act.weapon.setInterpolationDelay(0);
        }
        if (!act.victimReleased) {
            ExecutionAnims.Track vt = act.vTrack();
            act.vPuppet.pose = vt.pose();
            place(act.vPuppet, Math.min(frame, vt.length() - 1), animate);
        }
    }

    /** 처형자 발차기 인형 (yaw: 피처형자를 보는 방향). 끝나면 실제 몸으로 돌아감 */
    public void kick(Combatant ex, float yaw) {
        Arena a = plugin.arena();
        LivingEntity e = ex.entity();
        if (poses == null || a == null || e == null || acting.containsKey(ex.id)) return;
        Lying l = new Lying(ex, a, FallPose.Kind.KICK, poses.get(FallPose.Kind.KICK), yaw, yaw);
        l.start = l.end = feet(e.getLocation());
        if (!spawnPuppet(a, ex, l)) return;
        place(l, 0, false);
        acting.put(ex.id, l);
        e.setInvisible(true);
        sendEquipment(a, ex, true);
    }

    private static Vector forward(float yaw) {
        double r = Math.toRadians(yaw);
        return new Vector(-Math.sin(r), 0, Math.cos(r));
    }

    private Lying create(Arena a, Combatant c, Vec3 push, boolean strong, Location at, boolean corpse) {
        Vec3 face = c.look().horizontal();
        Vec3 p = push == null ? Vec3.ZERO : push.horizontal();
        float startYaw = (float) (face.lengthSq() < 1e-6 ? at.getYaw() : face.yaw());
        if (p.lengthSq() < 1e-6) p = face.lengthSq() < 1e-6 ? new Vec3(0, 0, -1) : face.mul(-1);
        p = p.normalize();
        // 몸은 맞은 쪽(밀려오는 쪽)을 보며 뒤로 넘어짐
        float yaw = (float) p.mul(-1).yaw();
        Location start = feet(at);
        FallPose.Config cfg = poses.get(FallPose.Kind.BACK).config();
        Location sit = wallSeat(a, start, p, cfg);
        FallPose.Kind kind = FallPose.kindFor(strong, sit != null);
        Lying l = new Lying(c, a, kind, poses.get(kind), startYaw, yaw);
        l.start = start;
        if (sit != null) l.end = sit;
        else {
            Vector slide = new Vector(p.x(), 0, p.z()).multiply(corpse ? l.pose.slide() : 0);
            l.end = clearSpot(a, start, slide);
        }
        if (!spawnPuppet(a, c, l)) return null;
        try {
            l.body = spawnDouble(a, c, l);
        } catch (RuntimeException ex) {
            plugin.getLogger().log(Level.WARNING, "대역 생성 실패: " + ex);
            removePuppet(l);
            return null;
        }
        place(l, 0, false);
        return l;
    }

    /** 밀려나는 쪽 벽: 몸통 두 높이에서 모두 막히면 벽. 앉을 자리(발 위치, 벽에서 wall_gap)를 돌려줌 */
    private static Location wallSeat(Arena a, Location start, Vec3 push, FallPose.Config cfg) {
        Vector dir = new Vector(push.x(), 0, push.z()).normalize();
        double dist = Double.MAX_VALUE;
        for (double h : new double[] {0.45, 1.0}) {
            Location from = start.clone().add(0, h, 0);
            RayTraceResult r = a.world.rayTraceBlocks(from, dir, WALL_REACH, FluidCollisionMode.NEVER, true);
            if (r == null || r.getHitBlock() == null || r.getHitBlockFace() == null) return null;
            if (dev.violence.arena.GlassService.isGlass(r.getHitBlock().getType())) return null;
            Vector n = r.getHitBlockFace().getDirection();
            if (n.dot(dir) > -0.7) return null;          // 벽면이 넘어지는 쪽을 마주해야 함
            dist = Math.min(dist, r.getHitPosition().distance(from.toVector()));
        }
        Location sit = start.clone().add(dir.clone().multiply(dist - cfg.wallGap()));
        // 앉을 자리 바닥
        RayTraceResult down = a.world.rayTraceBlocks(sit.clone().add(0, 0.6, 0), new Vector(0, -1, 0), 2.0, FluidCollisionMode.NEVER, true);
        if (down == null) return null;
        sit.setY(down.getHitPosition().getY());
        return sit;
    }

    /** 시체가 밀려날 자리 (벽에 막히면 그 앞까지) */
    private static Location clearSpot(Arena a, Location start, Vector slide) {
        double len = slide.length();
        if (len < 1e-3) return start.clone();
        Vector dir = slide.clone().normalize();
        RayTraceResult r = a.world.rayTraceBlocks(start.clone().add(0, 0.3, 0), dir, len + 0.4, FluidCollisionMode.NEVER, true);
        double d = r == null ? len : Math.max(0, Math.min(len, r.getHitPosition().distance(start.clone().add(0, 0.3, 0).toVector()) - 0.4));
        return start.clone().add(dir.multiply(d));
    }

    private boolean spawnPuppet(Arena a, Combatant c, Lying l) {
        try {
            ItemStack head = skinHead(c);
            for (FallPose.Part part : FallPose.Part.values()) {
                if (part == FallPose.Part.HEAD && c.mask != null) continue;
                l.parts.put(part, a.track(a.world.spawn(l.start, ItemDisplay.class, d -> setup(d, head.clone()))));
            }
            if (c.mask != null) {
                l.mask = a.track(a.world.spawn(l.start, ItemDisplay.class, d -> {
                    setup(d, dev.violence.weapon.WeaponItems.mask(c.mask, false));
                    d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.HEAD);
                }));
            }
            return true;
        } catch (RuntimeException ex) {
            plugin.getLogger().log(Level.WARNING, "넘어지는 인형 생성 실패: " + ex);
            removePuppet(l);
            return false;
        }
    }

    /** 넘어진 뒤 자세를 잡을 대역 (처음엔 숨김) */
    private Mannequin spawnDouble(Arena a, Combatant c, Lying l) {
        Location loc = doubleLocation(l);
        Mannequin body = a.track(a.world.spawn(loc, Mannequin.class, m -> {
            m.setPersistent(false);
            m.setImmovable(true);
            m.setDescription(null);
            m.setInvulnerable(true);
            m.setSilent(true);
            m.setGravity(false);
            m.setCollidable(false);
            m.setInvisible(true);
            if (c instanceof NpcCombatant n) m.setProfile(n.profile());
            else if (c.entity() instanceof Player p) m.setProfile(ResolvableProfile.resolvableProfile(p.getPlayerProfile()));
            if (c.heavy) {
                var s = m.getAttribute(org.bukkit.attribute.Attribute.SCALE);
                if (s != null) s.setBaseValue(c.scale());
            }
            // 머리 방향도 같이: 머리 방향이 0 으로 남으면 클라이언트가 몸을 머리 쪽으로 돌려 누운 몸이 비뚤어짐
            m.setRotation(loc.getYaw(), 0f);
            m.setBodyYaw(loc.getYaw());
            if (l.pose.end() == FallPose.End.FACE_UP) {
                try {
                    m.setPose(Pose.SLEEPING, true);
                } catch (IllegalArgumentException ex) {
                    Poses.lying(m);
                }
            }
        }));
        if (l.pose.end() == FallPose.End.SIT) {
            // 앉은 자세: 보이지 않는 디스플레이에 태움 (탄 개체의 발 = 자리 - seat_attach)
            FallPose.Config cfg = l.pose.config();
            Location seatLoc = l.end.clone().add(0, (cfg.seatY() + cfg.seatAttach()) * l.scale, 0);
            seatLoc.setYaw(l.yaw);
            seatLoc.setPitch(0);
            l.seat = a.track(a.world.spawn(seatLoc, ItemDisplay.class, d -> {
                d.setPersistent(false);
                d.setItemStack(null);
            }));
            l.seat.addPassenger(body);
            body.setRotation(l.yaw, (float) cfg.sitHeadPitch());
            body.setBodyYaw(l.yaw);
        }
        return body;
    }

    private static Location doubleLocation(Lying l) {
        Location loc = l.end.clone();
        if (l.pose.end() == FallPose.End.FACE_UP) {
            loc.add(forward(l.yaw).multiply(l.pose.endForward() * l.scale));
            loc.add(0, l.pose.lift() * l.scale, 0);
            loc.setYaw(FallPose.sleepingYaw(l.yaw));
        } else {
            loc.setYaw(l.yaw);
        }
        loc.setPitch(0);
        return loc;
    }

    // ───────── 매 틱 ─────────

    public void tick() {
        if (!execs.isEmpty()) tickExecs();
        if (!downed.isEmpty()) {
            for (Lying l : new ArrayList<>(downed.values())) {
                LivingEntity e = l.victim.entity();
                boolean gone = e == null || !e.isValid() || plugin.arena() != l.arena || !l.arena.combatants.containsKey(l.victim.id);
                if (gone || !l.victim.state.isDownedLike()) {
                    // 일어섬 (죽었으면 corpse() 가 먼저 데려감)
                    downed.remove(l.victim.id);
                    end(l, !gone);
                    continue;
                }
                if (l.follow) {
                    // 기어가면 따라감 (방향은 그대로)
                    Location now = feet(e.getLocation());
                    if (now.distanceSquared(l.end) > 1e-4) {
                        l.start = now;
                        l.end = now;
                        if (l.body != null && l.body.isValid()) {
                            Location dl = doubleLocation(l);
                            l.body.teleport(dl);
                            l.body.setRotation(dl.getYaw(), 0f);
                            l.body.setBodyYaw(dl.getYaw());
                            l.lastMove = l.tick;
                        }
                    }
                }
                advance(l);
                // 미끄러짐이 멈추면 대역을 새로 만듦: 움직이는 동안 클라이언트가 몸을 움직이는 방향으로 돌려
                // 누운 몸이 비뚤어진 채 남기 때문 (새 개체는 몸 방향이 처음부터 맞음)
                if (l.revealed && l.lastMove >= 0 && l.tick - l.lastMove >= 3 && l.victim.state == CombatState.DOWNED && l.seat == null) {
                    l.lastMove = -1;
                    respawnDouble(l);
                }
                if (l.revealed && l.tick % 10 == 0) sendEquipment(l.arena, l.victim, true);
            }
        }
        if (!acting.isEmpty()) {
            for (Lying l : new ArrayList<>(acting.values())) {
                LivingEntity e = l.victim.entity();
                l.tick++;
                boolean gone = e == null || !e.isValid() || plugin.arena() != l.arena || !l.arena.combatants.containsKey(l.victim.id);
                if (gone || l.tick >= l.pose.holdTicks() || l.victim.state == CombatState.DEAD || l.victim.state.isDownedLike()) {
                    acting.remove(l.victim.id);
                    end(l, !gone);
                    continue;
                }
                place(l, l.pose.frameAt(l.tick), true);
            }
        }
        if (!falling.isEmpty()) {
            for (Lying l : new ArrayList<>(falling)) {
                if (l.body == null || !l.body.isValid() || plugin.arena() != l.arena) {
                    removePuppet(l);
                    falling.remove(l);
                    continue;
                }
                advance(l);
                if (l.tick > l.pose.holdTicks()) falling.remove(l);
            }
        }
    }

    /** 다음 프레임 → 끝나기 한 틱 전에 대역을 보이고, 끝나면 인형을 치움 (한 틱 겹쳐서 빈 틱이 없게) */
    private void advance(Lying l) {
        l.tick++;
        int hold = l.pose.holdTicks();
        if (l.tick < hold) place(l, l.pose.frameAt(l.tick), true);
        if (!l.revealed && l.tick >= hold - 1) {
            reveal(l);
            if (l.corpse) bleed(l);
        }
        if (l.tick == hold) removePuppet(l);
    }

    /** 시체가 자리를 잡으면 맞은 부위 밑에서 피 웅덩이가 퍼짐 (시체에 붙어 함께 사라짐) */
    private void bleed(Lying l) {
        if (l.poolSize <= 0) return;
        float size = l.poolSize;
        l.poolSize = 0;
        int last = l.pose.frameCount() - 1;
        plugin.fx().bloodPool(l.arena, partWorld(l, l.poolPart, last, l.anchor(last)), size, l.body);
    }

    private Vec3 partWorld(Lying l, FallPose.Part part, int frame, Location anchor) {
        FallPose.Placement p = l.pose.place(frame, part, l.scale);
        Vector3d c = FallPose.toWorld(p.center(), l.yawAt(frame));
        return new Vec3(anchor.getX() + c.x, anchor.getY() + c.y, anchor.getZ() + c.z);
    }

    private Vec3 headWorld(Lying l, int frame, Location anchor) {
        FallPose.Placement p = l.pose.place(frame, FallPose.Part.HEAD, l.scale);
        Vector3d c = FallPose.toWorld(p.center(), l.yawAt(frame));
        return new Vec3(anchor.getX() + c.x, anchor.getY() + c.y, anchor.getZ() + c.z);
    }

    private void respawnDouble(Lying l) {
        Mannequin old = l.body;
        if (old == null || !old.isValid()) return;
        l.body = spawnDouble(l.arena, l.victim, l);
        l.revealed = false;
        reveal(l);
        l.arena.tracked.remove(old);
        old.remove();
    }

    private void reveal(Lying l) {
        l.revealed = true;
        Mannequin m = l.body;
        if (m == null || !m.isValid()) return;
        if (l.seat == null) {
            float y = doubleLocation(l).getYaw();
            m.setRotation(y, 0f);   // 머리·몸 방향을 다시 맞춤 (보이기 직전)
            m.setBodyYaw(y);
        }
        EntityEquipment eq = m.getEquipment();
        Combatant c = l.victim;
        if (c instanceof NpcCombatant n) n.copyOutfitTo(eq);
        else if (c.entity() instanceof Player p) {
            eq.setHelmet(p.getInventory().getHelmet());
            eq.setChestplate(p.getInventory().getChestplate());
            eq.setLeggings(p.getInventory().getLeggings());
        }
        m.setInvisible(false);
    }

    private void end(Lying l, boolean restore) {
        removePuppet(l);
        if (l.body != null && l.body.isValid()) {
            l.arena.tracked.remove(l.body);
            l.body.remove();
        }
        if (l.seat != null && l.seat.isValid()) {
            l.arena.tracked.remove(l.seat);
            l.seat.remove();
        }
        LivingEntity e = l.victim.entity();
        if (!restore || e == null || !e.isValid()) return;
        l.victim.applyStateVisuals();
        sendEquipment(l.arena, l.victim, false);
    }

    /** 아레나 정리 시: 모두 실제 몸으로 */
    public void clear() {
        for (ExecAct act : new ArrayList<>(execs.values())) endExec(act);
        execs.clear();
        for (Lying l : new ArrayList<>(downed.values())) end(l, true);
        for (Lying l : new ArrayList<>(acting.values())) end(l, true);
        for (Lying l : falling) removePuppet(l);
        downed.clear();
        acting.clear();
        falling.clear();
    }

    private static void removePuppet(Lying l) {
        for (ItemDisplay d : l.parts.values()) if (d.isValid()) d.remove();
        l.parts.clear();
        if (l.mask != null && l.mask.isValid()) l.mask.remove();
        l.mask = null;
    }

    private static Location feet(Location src) {
        Location l = src.clone();
        l.setYaw(0);
        l.setPitch(0);
        return l;
    }

    private static void setup(ItemDisplay d, ItemStack item) {
        d.setPersistent(false);
        d.setItemStack(item);
        d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
        d.setInterpolationDuration(1);
        d.setTeleportDuration(1);
        d.setShadowRadius(0);
        d.setViewRange(1.5f);
    }

    private void place(Lying l, int frame, boolean animate) {
        Location at = l.anchor(frame);
        float yaw = l.yawAt(frame);
        for (FallPose.Part part : FallPose.Part.values()) {
            ItemDisplay d = part == FallPose.Part.HEAD && l.mask != null ? l.mask : l.parts.get(part);
            if (d == null || !d.isValid()) continue;
            FallPose.Placement p = l.pose.place(frame, part, l.scale);
            Vector3d c = FallPose.toWorld(p.center(), yaw);
            Quaternionf r = new Quaternionf(FallPose.toWorld(p.rotation(), yaw));
            if (d.getLocation().distanceSquared(at) > 1e-4) d.teleport(at);
            if (d == l.mask) {
                float sc = (float) (FallPose.PX * 16 * l.scale) * MASK_SCALE;
                d.setTransformation(new Transformation(new Vector3f((float) c.x, (float) c.y, (float) c.z), r,
                        new Vector3f(sc, sc, sc), new Quaternionf()));
            } else {
                d.setTransformation(SkinPuppet.transform(part, c, r, l.scale));
                SkinPuppet.mark(d, part);
            }
            if (animate) d.setInterpolationDelay(0);
        }
    }

    /** 이 사람의 스킨을 쓰는 플레이어 머리 (NPC 는 마네킹 프로필, 플레이어는 자기 프로필) */
    private static ItemStack skinHead(Combatant c) {
        ItemStack it = new ItemStack(Material.PLAYER_HEAD);
        ResolvableProfile profile = null;
        if (c instanceof NpcCombatant n) profile = n.profile();
        else if (c.entity() instanceof Player p) profile = ResolvableProfile.resolvableProfile(p.getPlayerProfile());
        if (profile != null) it.setData(DataComponentTypes.PROFILE, profile);
        return it;
    }

    /** 보는 사람들에게 실제 몸의 장비를 숨김(hide) / 다시 보냄 */
    private void sendEquipment(Arena a, Combatant c, boolean hide) {
        LivingEntity e = c.entity();
        if (e == null) return;
        Map<EquipmentSlot, ItemStack> eq = new EnumMap<>(EquipmentSlot.class);
        EntityEquipment real = e.getEquipment();
        for (EquipmentSlot slot : SLOTS) {
            ItemStack it = hide || real == null ? null : real.getItem(slot);
            eq.put(slot, it == null ? new ItemStack(Material.AIR) : it);
        }
        for (PlayerCombatant viewer : a.players.values()) {
            if (viewer == c || !viewer.player().isOnline()) continue;
            viewer.player().sendEquipmentChange(e, eq);
        }
        // 손 아이템은 3인칭용으로 바꿔 보내는 것이 따로 있음
        if (!hide && c instanceof PlayerCombatant pc) plugin.game().syncHeld(pc);
        if (!hide && c instanceof NpcCombatant n) plugin.game().syncNpcPose(n);
    }
}
