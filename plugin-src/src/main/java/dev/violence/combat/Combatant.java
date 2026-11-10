package dev.violence.combat;

import dev.violence.logic.ComboTracker;
import dev.violence.logic.FireAccumulator;
import dev.violence.logic.KillStreak;
import dev.violence.mask.Mask;
import dev.violence.math.Vec3;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponType;
import java.util.UUID;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.LivingEntity;

/**
 * 전투에 참여하는 개체(플레이어 또는 NPC)의 공통 상태.
 */
public abstract class Combatant {
    public static final double MAX_HP = 100;

    public final UUID id;
    public CombatState state = CombatState.ALIVE;
    public long stateSince;
    public double hp = MAX_HP;
    /** 마지막으로 총에 맞은 틱 (HP 회복 기준) */
    public long lastHurtTick = -1000;

    /** 들고 있는 무기 (null = 맨손) */
    public WeaponInstance weapon;
    /** 보조무기 칸 (마크 가면 MP5 왼손) */
    public WeaponInstance offhand;
    public Mask mask;

    public final KillStreak streak = new KillStreak();
    public final ComboTracker combo = new ComboTracker();
    public int kills;
    public int deaths;
    public int score;

    public long downedUntil;
    /** 이 틱 전까지 이동 외 행동 불가 (일어선 직후 3틱, 발차기 등) */
    public long actionLockUntil;
    /** 이 틱 전까지 이동 불가 (발차기, 경직) */
    public long moveLockUntil;
    public long meleeReadyAt;
    public long rollUntil;
    /** 남은 총알 버티기 횟수 (루퍼스/얼 가면) */
    public int bulletShield;
    public Execution execution;
    public Combatant lastAttacker;
    /** 맨손으로 쓰러뜨릴 수 없는 거구 */
    public boolean heavy;

    public final PositionHistory history = new PositionHistory(24);
    private FireAccumulator fireAcc;
    private String fireAccWeapon;
    public long lastFireTick = -100;
    public long lastSwingTick = -100;
    /** 끊기지 않고 이어진 휘두르기 횟수 (홀수 번째는 왼→오) */
    public int swingChain;
    public long dualToggle;
    /** 3인칭 근접 대기 방향: true = 왼쪽 대기 (다음 휘두르기가 왼→오, 보는 사람에게 주 손을 왼손으로 보냄) */
    public boolean tpStanceLeft;
    /** 3인칭 휘두르기 아이템을 보여주는 중 (이 틱 전까지) */
    public long tpSwingUntil = -100;
    public WeaponType tpSwingType;
    public int tpSwingSeq;
    /** 샷건 등 강한 공격에 맞은 틱 (넘어지는 동작 선택) */
    public long strongHitTick = -100;

    protected Combatant(UUID id) {
        this.id = id;
    }

    public abstract LivingEntity entity();

    public abstract String name();

    public abstract boolean isPlayer();

    /** 들고 있는 아이템 / 장비 표시 갱신 */
    public abstract void refreshEquipment();

    /** 상태 변화 시 (이동 잠금, 자세 등) 갱신 */
    public abstract void applyStateVisuals();

    /** 위치를 즉시 옮김 */
    public abstract void teleport(Location loc);

    /** 공격 방향으로 밀려남 (쓰러질 때) */
    public abstract void knockback(Vec3 dir, double strength);

    /** 닫힌 문을 향해 걸어가며 밀고 있는가 */
    public abstract boolean wantsToWalkThrough(dev.violence.arena.Door door, long now);

    /** 사망 직후 (시점 연출 등) */
    public void onDeath(Combatant killer, Vec3 dir, long now) {}

    /** 리스폰 직후 */
    public void onRespawn(long now) {}

    /** 처형 시작/종료 (카메라 전환) */
    public void onExecutionStart(Execution e, org.bukkit.entity.ItemDisplay cam) {}

    public void onExecutionEnd(Execution e) {}

    /** 처형 시 화면 흔들림 등 타격감 */
    public void feelImpact(double amount) {}

    /** 연사 중 잔떨림 (흔들림을 최소 이 정도로 유지, 누적되지 않음) */
    public void feelSustained(double level) {}

    /** 총 반동: 화면이 위로 튀었다가 제자리로 돌아옴 (도, 플레이어만) */
    public void feelRecoil(double degrees) {}

    /** 다음 리스폰 틱 (사망 상태일 때) */
    public long respawnAt = -1;
    /** 가면 F키 능력으로 임시로 바꾸기 전 들고 있던 무기 */
    public WeaponInstance stashedWeapon;
    public long abilityReadyAt;
    public long spaceReadyAt;

    public World world() { return entity().getWorld(); }

    public double scale() { return heavy ? 1.2 : 1.0; }

    /** 탄퍼짐 추가 배율 (NPC 는 부정확) */
    public double spreadPenalty() { return 1.0; }

    public Vec3 feet() {
        Location l = entity().getLocation();
        return new Vec3(l.getX(), l.getY(), l.getZ());
    }

    public Vec3 eye() {
        if (state.isDownedLike()) return feet().add(0, 0.4, 0);
        return feet().add(0, 1.62 * scale(), 0);
    }

    public Vec3 look() {
        Location l = entity().getLocation();
        return Vec3.fromYawPitch(l.getYaw(), l.getPitch());
    }

    public float yaw() { return entity().getLocation().getYaw(); }

    public boolean isAlive() { return state != CombatState.DEAD; }

    public boolean canAct(long now) {
        return state == CombatState.ALIVE && now >= actionLockUntil;
    }

    public boolean canMove(long now) {
        return state == CombatState.ALIVE && now >= moveLockUntil;
    }

    public WeaponType weaponType(WeaponType fist) {
        return weapon == null ? fist : weapon.type();
    }

    public boolean hasWeapon() { return weapon != null; }

    public FireAccumulator fireAccumulator(WeaponType type, double rpmMultiplier) {
        String key = type.id() + "@" + rpmMultiplier;
        if (fireAcc == null || !key.equals(fireAccWeapon)) {
            fireAcc = new FireAccumulator(type.rpm() * rpmMultiplier);
            fireAccWeapon = key;
        }
        return fireAcc;
    }

    public void setState(CombatState s, long now) {
        this.state = s;
        this.stateSince = now;
        applyStateVisuals();
    }

    public String displayName() { return name(); }
}
