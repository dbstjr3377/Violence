package dev.violence.npc;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Door;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.math.Vec3;
import dev.violence.weapon.WeaponItems;
import dev.violence.weapon.WeaponType;
import io.papermc.paper.datacomponent.item.ResolvableProfile;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mannequin;
import org.bukkit.entity.Pose;
import org.bukkit.inventory.EntityEquipment;
import org.bukkit.inventory.ItemStack;

/**
 * NPC 개체. 몸체는 플레이어 모델을 가진 마네킹 엔티티이며,
 * 서버가 보행 그리드 위에서 직접 위치를 계산해 움직인다(운동학적 이동).
 */
public final class NpcCombatant extends Combatant {
    final Mannequin body;
    private final ResolvableProfile profile;
    private final int outfitColor;
    final String name;

    // 이동 / AI 상태
    Vec3 pos;
    float yaw;
    float pitch;
    List<Vec3> path = new ArrayList<>();
    int pathIndex;
    long nextRepath;
    Vec3 pathGoal;
    Vec3 moveDir = Vec3.ZERO;
    Vec3 slide = Vec3.ZERO;
    Combatant target;
    long targetSeenAt = -1000;
    Vec3 targetLastPos;
    long reactionUntil;
    Vec3 noisePos;
    long noiseUntil;
    long nextThink;
    long burstUntil;
    long nextShotAt;
    long stuckSince;
    Vec3 lastProgressPos;
    final double skill;

    NpcCombatant(Mannequin body, ResolvableProfile profile, String name, int outfitColor, boolean heavy, double skill) {
        super(UUID.randomUUID());
        this.body = body;
        this.profile = profile;
        this.name = name;
        this.outfitColor = outfitColor;
        this.heavy = heavy;
        this.skill = skill;
        Location l = body.getLocation();
        this.pos = new Vec3(l.getX(), l.getY(), l.getZ());
        this.yaw = l.getYaw();
    }

    public ResolvableProfile profile() { return profile; }

    @Override public LivingEntity entity() { return body; }
    @Override public String name() { return name; }
    @Override public boolean isPlayer() { return false; }

    @Override
    public Vec3 feet() { return pos; }

    @Override
    public Vec3 look() { return Vec3.fromYawPitch(yaw, pitch); }

    @Override
    public float yaw() { return yaw; }

    @Override
    public double spreadPenalty() {
        return 1.6 + (1.0 - skill) * 1.6;
    }

    public void copyOutfitTo(EntityEquipment eq) {
        eq.setChestplate(WeaponItems.outfit(Material.LEATHER_CHESTPLATE, outfitColor));
        eq.setLeggings(WeaponItems.outfit(Material.LEATHER_LEGGINGS, darker(outfitColor)));
        eq.setBoots(WeaponItems.outfit(Material.LEATHER_BOOTS, 0x222222));
    }

    private static int darker(int rgb) {
        int r = (rgb >> 16 & 0xFF) * 6 / 10, g = (rgb >> 8 & 0xFF) * 6 / 10, b = (rgb & 0xFF) * 6 / 10;
        return (r << 16) | (g << 8) | b;
    }

    @Override
    public void refreshEquipment() {
        EntityEquipment eq = body.getEquipment();
        WeaponType fist = ViolencePlugin.get().weapons().fist();
        if (state == CombatState.DEAD) {
            eq.setItemInMainHand(null);
            eq.setItemInOffHand(null);
            return;
        }
        eq.setItemInMainHand(weapon != null ? WeaponItems.world(weapon.type()) : null);
        eq.setItemInOffHand(offhand != null ? WeaponItems.world(offhand.type()) : null);
        if (eq.getChestplate() == null || eq.getChestplate().getType() == Material.AIR) copyOutfitTo(eq);
    }

    @Override
    public void applyStateVisuals() {
        switch (state) {
            case DOWNED, BEING_EXECUTED -> {
                body.setInvisible(false);
                dev.violence.fx.Poses.lying(body);
            }
            case DEAD -> {
                dev.violence.fx.Poses.standing(body);
                body.setInvisible(true);
            }
            default -> {
                body.setInvisible(false);
                dev.violence.fx.Poses.standing(body);
            }
        }
    }

    @Override
    public void teleport(Location loc) {
        pos = new Vec3(loc.getX(), loc.getY(), loc.getZ());
        yaw = loc.getYaw();
        pitch = loc.getPitch();
        path.clear();
        slide = Vec3.ZERO;
        body.teleport(loc);
    }

    /** 현재 pos/yaw 를 몸체에 반영 */
    void sync() {
        Location l = new Location(body.getWorld(), pos.x(), pos.y(), pos.z(), yaw, pitch);
        body.teleport(l);
        body.setBodyYaw(yaw);
    }

    @Override
    public void knockback(Vec3 dir, double strength) {
        slide = dir.mul(strength * 0.55);
        path.clear();
    }

    @Override
    public boolean wantsToWalkThrough(Door door, long now) {
        if (moveDir.lengthSq() < 0.01) return false;
        Vec3 to = door.center().sub(pos).horizontal().normalize();
        return moveDir.dot(to) > 0.3;
    }

    @Override
    public void onRespawn(long now) {
        target = null;
        path.clear();
        noisePos = null;
        reactionUntil = now + 10;
    }

    @Override
    public void onDeath(Combatant killer, Vec3 dir, long now) {
        target = null;
        path.clear();
        burstUntil = 0;
    }
}
