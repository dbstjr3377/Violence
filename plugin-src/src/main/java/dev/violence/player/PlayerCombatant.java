package dev.violence.player;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Door;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.combat.Execution;
import dev.violence.fx.Fx;
import dev.violence.math.Vec3;
import dev.violence.weapon.WeaponItems;
import dev.violence.weapon.WeaponType;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.block.Block;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Pose;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.util.Vector;

/** 플레이어 개체. */
public final class PlayerCombatant extends Combatant {
    /** 연사 무기로 적을 겨눈 채 누르기 (HoldFireBlock) */
    public final HoldFireBlock holdFire = new HoldFireBlock();

    public static final double BASE_SPEED = 0.135;

    private final Player player;
    public final InputState input = new InputState();
    private Block crawlBlock;
    public java.util.List<dev.violence.mask.Mask> maskOffer;

    public PlayerCombatant(Player player) {
        super(player.getUniqueId());
        this.player = player;
    }

    public Player player() { return player; }

    @Override public LivingEntity entity() { return player; }
    @Override public String name() { return player.getName(); }
    @Override public boolean isPlayer() { return true; }

    private static ViolencePlugin plugin() { return ViolencePlugin.get(); }

    /** 게임 참가 시 이동/공격 규칙 적용 */
    public void applyRules() {
        player.setGameMode(GameMode.SURVIVAL);
        setAttr(Attribute.JUMP_STRENGTH, 0.0);
        setAttr(Attribute.BLOCK_INTERACTION_RANGE, 64.0);
        setAttr(Attribute.ENTITY_INTERACTION_RANGE, 0.0);
        setAttr(Attribute.BLOCK_BREAK_SPEED, 0.0);
        setAttr(Attribute.STEP_HEIGHT, 0.6);
        setAttr(Attribute.ATTACK_SPEED, 1024.0);
        setAttr(Attribute.FALL_DAMAGE_MULTIPLIER, 0.0);
        player.setFoodLevel(6); // 6 이하 = 달리기 불가
        player.setSaturation(0);
        player.setHealth(player.getAttribute(Attribute.MAX_HEALTH).getValue());
        player.setInvulnerable(false);
        player.getInventory().clear();
        player.getInventory().setHeldItemSlot(0);
        player.setExp(0);
        player.setLevel(0);
        player.setFireTicks(0);
        player.setInvisible(false);
        applyStateVisuals();
        refreshEquipment();
    }

    /** 게임 종료 시 원래대로 */
    public void restoreDefaults() {
        setAttr(Attribute.JUMP_STRENGTH, 0.42);
        setAttr(Attribute.BLOCK_INTERACTION_RANGE, 4.5);
        setAttr(Attribute.ENTITY_INTERACTION_RANGE, 3.0);
        setAttr(Attribute.BLOCK_BREAK_SPEED, 1.0);
        PlayerSpeed.set(player, 0.1);
        setAttr(Attribute.ATTACK_SPEED, 4.0);
        setAttr(Attribute.FALL_DAMAGE_MULTIPLIER, 1.0);
        setAttr(Attribute.CAMERA_DISTANCE, 4.0);
        clearCrawl();
        dev.violence.fx.Poses.standing(player);
        player.setFoodLevel(20);
        player.getInventory().clear();
        player.setInvisible(false);
        player.setGameMode(GameMode.ADVENTURE);
    }

    private void setAttr(Attribute a, double v) {
        AttributeInstance inst = player.getAttribute(a);
        if (inst != null) inst.setBaseValue(v);
    }

    @Override
    public void refreshEquipment() {
        PlayerInventory inv = player.getInventory();
        inv.setItem(0, handItem());
        rehideHands();
        inv.setItemInOffHand(offhand != null ? WeaponItems.create(offhand.type(), offhand.ammo()) : null);
        if (inv.getHeldItemSlot() != 0) inv.setHeldItemSlot(0);
        plugin().game().syncHeld(this);
        inv.setHelmet(mask != null ? WeaponItems.mask(mask, false) : null);
        // 갑옷은 입히지 않음. 연속킬 붉은 화면만 보이지 않는 장비(모델 없음, 카메라 오버레이)로
        int overlay = streak.value() >= 5 ? 2 : (streak.value() >= 3 ? 1 : 0);
        inv.setChestplate(overlay > 0 && state != dev.violence.combat.CombatState.DEAD ? WeaponItems.overlayOnly(EquipmentSlot.CHEST, overlay) : null);
        inv.setLeggings(null);
        inv.setBoots(null);
    }

    public double speedValue(long now) {
        if (!canMove(now)) return 0;
        double s = BASE_SPEED;
        if (mask != null) s *= mask.speedMultiplier();
        if (streak.value() >= 5) s *= 1.05;
        return s;
    }

    @Override
    public void applyStateVisuals() {
        long now = plugin().now();
        PlayerSpeed.set(player, speedValue(now));
        switch (state) {
            case DOWNED, BEING_EXECUTED -> {
                dev.violence.fx.Poses.lying(player);
                applyCrawl();
                // 넘어지는 동작(인형) 중에는 실제 몸을 숨김
                player.setInvisible(plugin().falls() != null && plugin().falls().hiding(this));
            }
            case DEAD -> {
                clearCrawl();
                dev.violence.fx.Poses.standing(player);
                player.setInvisible(true);
            }
            default -> {
                clearCrawl();
                dev.violence.fx.Poses.standing(player);
                // 처형 발차기 인형 중에는 실제 몸을 숨김
                player.setInvisible(plugin().falls() != null && plugin().falls().hiding(this));
            }
        }
    }

    /** 내 화면에서도 엎드린 자세가 되도록 머리 위에 가짜 블록을 보낸다 */
    private void applyCrawl() {
        Block head = player.getLocation().getBlock().getRelative(0, 1, 0);
        if (head.equals(crawlBlock)) return;
        clearCrawl();
        if (head.getType().isAir()) {
            player.sendBlockChange(head.getLocation(), Material.BARRIER.createBlockData());
            crawlBlock = head;
        }
    }

    private void clearCrawl() {
        if (crawlBlock != null) {
            player.sendBlockChange(crawlBlock.getLocation(), crawlBlock.getBlockData());
            crawlBlock = null;
        }
    }

    /** 쓰러진 채 밀려서 위치가 바뀌었을 때 가짜 블록 따라가기 */
    public void tickCrawl() {
        if (state.isDownedLike()) applyCrawl();
    }

    @Override
    public void teleport(Location loc) {
        clearCrawl();
        player.teleport(loc);
    }

    @Override
    public void knockback(Vec3 dir, double strength) {
        player.setVelocity(new Vector(dir.x() * strength, 0.18, dir.z() * strength));
    }

    @Override
    public boolean wantsToWalkThrough(Door door, long now) {
        if (!input.forward && !input.left && !input.right && !input.backward) return false;
        Vec3 to = door.center().sub(feet()).horizontal().normalize();
        Vec3 move = input.moveDirection(look());
        return move.dot(to) > 0.4;
    }

    /** 지금 손에 든 아이템이 왼→오 휘두르기용("_b")인가 */
    private boolean backhand;

    /** 다음 휘두르기 방향에 맞는 1인칭 아이템으로 바꿔 낀다 (3인칭 표시는 그대로) */
    public void setBackhand(boolean b) {
        if (b == backhand) return;
        backhand = b;
        player.getInventory().setItem(0, handItem());
        rehideHands();
    }

    /** 처형·사망 카메라 중에 손 아이템이 바뀌면 동기화 뒤에 다시 숨김 */
    private void rehideHands() {
        if (!plugin().camera().isViewing(player)) return;
        plugin().later(1, () -> { if (player.isOnline()) plugin().camera().hideHands(player); });
    }

    /** 주 손 아이템. 맨손이면 비워 둬서 1인칭에 플레이어 스킨의 팔이 그대로 보이게 함 */
    private org.bukkit.inventory.ItemStack handItem() {
        return weapon == null ? null : WeaponItems.create(weapon.type(), weapon.ammo(), backhand);
    }

    /** 1인칭 키프레임 애니메이션 재생 (해당 쿨다운 그룹에 짧은 쿨다운) */
    public void playAnim(net.kyori.adventure.key.Key group, int ticks) {
        if (group != null) player.setCooldown(group, ticks);
    }

    @Override
    public void feelImpact(double amount) {
        plugin().shake().add(player, amount);
    }

    @Override
    public void feelRecoil(double degrees) {
        plugin().shake().recoil(player, degrees);
    }

    @Override
    public void feelSustained(double level) {
        plugin().shake().atLeast(player, level);
    }

    @Override
    public void onDeath(Combatant killer, Vec3 dir, long now) {
        ViolencePlugin pl = plugin();
        // 살짝 앞, 위에서 자신을 내려다보는 시점
        Vec3 f = feet();
        Vec3 fwd = look().horizontal().normalize();
        if (fwd.lengthSq() < 0.01) fwd = new Vec3(0, 0, 1);
        Vec3 camPos = f.add(fwd.mul(1.3)).add(0, 2.6, 0);
        Vec3 lookDir = f.add(0, 0.3, 0).sub(camPos).normalize();
        Location cl = Fx.loc(player.getWorld(), camPos);
        cl.setYaw((float) lookDir.yaw());
        cl.setPitch((float) lookDir.pitch());
        ItemDisplay cam = pl.camera().spawnCamera(cl, 20);
        pl.camera().view(player, cam);
        // 천천히 위로 빠지는 카메라
        Vec3 up = camPos.add(0, 1.2, 0).add(fwd.mul(0.4));
        Location ul = Fx.loc(player.getWorld(), up);
        Vec3 lookDir2 = f.add(0, 0.2, 0).sub(up).normalize();
        ul.setYaw((float) lookDir2.yaw());
        ul.setPitch((float) lookDir2.pitch());
        var arena = pl.arena();
        pl.laterIn(arena, 2, () -> {
            if (cam.isValid()) cam.teleport(ul);
        });
        // 2초 리스폰 타임라인: 24틱에 페이드아웃 시작 → 30~40틱 검은 화면 → 40틱 리스폰 → 페이드인
        pl.laterIn(arena, 24, () -> {
            if (state == CombatState.DEAD && arena.combatants.containsKey(id)) pl.hud().fadeBlack(player, 6, 12, 8);
        });
        pl.shake().reset(player);
        pl.shake().add(player, 0.6);
        player.getInventory().clear();
    }

    @Override
    public void onRespawn(long now) {
        plugin().camera().reset(player);
        plugin().shake().reset(player);
        input.reset();
    }

    @Override
    public void onExecutionStart(Execution e, ItemDisplay cam) {
        if (cam != null) plugin().camera().view(player, cam);
    }

    @Override
    public void onExecutionEnd(Execution e) {
        // 처형자는 사용자 설정 시점으로 복귀. 피처형자는 죽으면 사망 시점으로 넘어감
        if (state != CombatState.DEAD) plugin().camera().reset(player);
    }
}
