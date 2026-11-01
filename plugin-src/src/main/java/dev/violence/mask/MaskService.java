package dev.violence.mask;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.combat.CombatState;
import dev.violence.combat.Combatant;
import dev.violence.fx.Fx;
import dev.violence.fx.Glyphs;
import dev.violence.math.Vec3;
import dev.violence.player.PlayerCombatant;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponItems;
import dev.violence.weapon.WeaponType;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.kyori.adventure.text.Component;
import org.bukkit.Color;
import org.bukkit.entity.Display;
import org.bukkit.entity.Player;
import org.bukkit.entity.TextDisplay;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryType;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 가면: 연속 3/5킬 시 E 키(인벤토리)를 열어 무작위 3개 중 하나를 선택.
 * 인벤토리 화면은 리소스팩에서 "가면 선택" 화면으로 꾸며진다.
 */
public final class MaskService {
    /** 인벤토리에서 가면 후보가 놓이는 칸 (가운데 줄) */
    public static final int[] OFFER_SLOTS = {20, 22, 24};

    private final ViolencePlugin plugin;
    private final Map<UUID, List<TextDisplay>> georgeMarkers = new HashMap<>();

    public MaskService(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    /** 가면 선택권 지급 */
    public void offer(PlayerCombatant pc) {
        List<Mask> all = new ArrayList<>(List.of(Mask.values()));
        if (pc.mask != null) all.remove(pc.mask);
        Collections.shuffle(all, plugin.random());
        pc.maskOffer = new ArrayList<>(all.subList(0, 3));
        PlayerInventory inv = pc.player().getInventory();
        for (int i = 0; i < 3; i++) inv.setItem(OFFER_SLOTS[i], WeaponItems.mask(pc.maskOffer.get(i), true));
        plugin.hud().prompt(pc.player(), "E키를 눌러 가면을 착용하세요");
        plugin.fx().sound(pc.world(), pc.eye(), "violence:ui.mask_offer", 1f, 1f);
    }

    public void onInventoryClick(PlayerCombatant pc, InventoryClickEvent e) {
        if (pc.maskOffer == null) return;
        if (e.getClickedInventory() == null || e.getClickedInventory().getType() != InventoryType.PLAYER) return;
        int slot = e.getSlot();
        for (int i = 0; i < 3; i++) {
            if (OFFER_SLOTS[i] == slot) {
                Mask m = pc.maskOffer.get(i);
                clearOffer(pc);
                equip(pc, m);
                pc.player().closeInventory();
                return;
            }
        }
    }

    public void clearOffer(PlayerCombatant pc) {
        pc.maskOffer = null;
        PlayerInventory inv = pc.player().getInventory();
        for (int s : OFFER_SLOTS) inv.setItem(s, null);
    }

    public void equip(Combatant c, Mask m) {
        long now = plugin.now();
        c.mask = m;
        c.bulletShield = m.bulletShield();
        WeaponType t;
        switch (m) {
            case DENNIS -> {
                if (c.weapon == null) c.weapon = new WeaponInstance(plugin.weapons().get("dagger"));
            }
            case BIKER -> {
                if (c.weapon == null) c.weapon = new WeaponInstance(plugin.weapons().get("cleaver"));
            }
            case RICHTER -> {
                if (c.weapon != null) plugin.combat().dropWeapons(c, c.look());
                c.weapon = new WeaponInstance(plugin.weapons().get("silenced_uzi"));
            }
            case MARK -> {
                // 기존 소지 무기 제거 후 64발 MP5 양손
                c.weapon = null;
                c.stashedWeapon = null;
                t = plugin.weapons().get("mp5_dual");
                WeaponInstance right = new WeaponInstance(t);
                WeaponInstance left = new WeaponInstance(t);
                right.setVanishOnDrop(true);
                left.setVanishOnDrop(true);
                c.weapon = right;
                c.offhand = left;
            }
            default -> {
            }
        }
        c.refreshEquipment();
        c.applyStateVisuals();
        plugin.fx().sound(c.world(), c.eye(), "violence:ui.mask_equip", 1f, 1f);
        if (c instanceof PlayerCombatant pc) {
            plugin.hud().prompt(pc.player(), m.displayName() + " - " + m.description());
        }
    }

    /** F 키: 가면별 임시 무기 */
    public void onFKey(Combatant c, long now) {
        if (c.mask == null || !c.canAct(now) || now < c.abilityReadyAt) return;
        String weaponId;
        int seconds;
        switch (c.mask) {
            case DENNIS -> { weaponId = "dagger"; seconds = 5; }
            case RICHTER -> { weaponId = "silenced_uzi"; seconds = 12; }
            case DETECTIVE -> { weaponId = "shotgun"; seconds = 12; }
            case BIKER -> { weaponId = "cleaver"; seconds = 5; }
            default -> { return; }
        }
        WeaponInstance temp = new WeaponInstance(plugin.weapons().get(weaponId));
        temp.setExpireTick(now + seconds * 20L);
        temp.setVanishOnDrop(true);
        if (c.weapon != null && c.weapon.expireTick() < 0) c.stashedWeapon = c.weapon;
        c.weapon = temp;
        c.abilityReadyAt = now + seconds * 20L + 200;
        c.refreshEquipment();
        plugin.fx().sound(c.world(), c.eye(), "violence:weapon.pickup", 1f, 0.8f);
    }

    /** Space 가면 능력 (올라타기/발차기 대상이 없을 때) */
    public void onSpace(Combatant c, long now) {
        if (c.mask == null) return;
        Arena a = plugin.arena();
        switch (c.mask) {
            case WILLEM -> disarm(a, c, now);
            case CORY -> roll(c, now);
            default -> {
            }
        }
    }

    private void disarm(Arena a, Combatant c, long now) {
        Combatant best = null;
        double bd = 2.4;
        Vec3 look = c.look().horizontal().normalize();
        for (Combatant o : a.combatants.values()) {
            if (o == c || o.state != CombatState.ALIVE) continue;
            Vec3 to = o.feet().sub(c.feet()).horizontal();
            double d = to.length();
            if (d > bd || to.normalize().dot(look) < 0.6) continue;
            bd = d;
            best = o;
        }
        c.spaceReadyAt = now + 20;
        if (best == null) return;
        c.entity().swingMainHand();
        if (best.weapon != null) {
            if (c.weapon != null) plugin.combat().dropWeapons(c, look.mul(-1));
            c.weapon = best.weapon;
            best.weapon = null;
            best.offhand = null;
        }
        // 5틱 경직
        best.moveLockUntil = now + 5;
        best.actionLockUntil = now + 5;
        best.applyStateVisuals();
        plugin.later(6, best::applyStateVisuals);
        best.refreshEquipment();
        c.refreshEquipment();
        plugin.fx().sound(c.world(), best.eye(), "violence:melee.punch_hit", 1f, 1.3f);
    }

    private void roll(Combatant c, long now) {
        c.spaceReadyAt = now + 22;
        c.rollUntil = now + 8;
        c.actionLockUntil = now + 8;
        Vec3 dir;
        if (c instanceof PlayerCombatant pc) {
            dir = pc.input.moveDirection(c.look());
            if (dir.lengthSq() < 0.01) dir = c.look().horizontal().normalize();
        } else dir = c.look().horizontal().normalize();
        c.knockback(dir, 1.25);
        c.feelImpact(0.2);
        plugin.fx().sound(c.world(), c.feet(), "violence:melee.roll", 1f, 1f);
    }

    /** 조지: 주변 적 위치를 벽 너머로 표시 (착용자에게만 보임) */
    public void tick(Arena a, long now) {
        if (now % 2 != 0) return;
        for (PlayerCombatant pc : a.players.values()) {
            Player p = pc.player();
            List<TextDisplay> markers = georgeMarkers.get(p.getUniqueId());
            if (pc.mask != Mask.GEORGE || !pc.isAlive()) {
                if (markers != null) {
                    for (TextDisplay t : markers) {
                        a.tracked.remove(t);
                        t.remove();
                    }
                    georgeMarkers.remove(p.getUniqueId());
                }
                continue;
            }
            if (markers == null) {
                markers = new ArrayList<>();
                georgeMarkers.put(p.getUniqueId(), markers);
            }
            List<Combatant> enemies = new ArrayList<>();
            for (Combatant c : a.combatants.values()) {
                if (c != pc && c.isAlive() && c.feet().distance(pc.feet()) < 24) enemies.add(c);
            }
            while (markers.size() < enemies.size()) {
                TextDisplay td = a.track(a.world.spawn(p.getLocation(), TextDisplay.class, d -> {
                    d.text(Glyphs.text("▼", Glyphs.HUD, Glyphs.RED));
                    d.setBillboard(Display.Billboard.CENTER);
                    d.setSeeThrough(true);
                    d.setBackgroundColor(Color.fromARGB(0, 0, 0, 0));
                    d.setPersistent(false);
                    d.setVisibleByDefault(false);
                    d.setTeleportDuration(2);
                    d.setBrightness(new Display.Brightness(15, 15));
                    d.setTransformation(new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(1.6f, 1.6f, 1.6f), new Quaternionf()));
                }));
                p.showEntity(plugin, td);
                markers.add(td);
            }
            while (markers.size() > enemies.size()) {
                TextDisplay td = markers.removeLast();
                a.tracked.remove(td);
                td.remove();
            }
            for (int i = 0; i < enemies.size(); i++) {
                Combatant e = enemies.get(i);
                Vec3 at = e.feet().add(0, e.state.isDownedLike() ? 0.9 : 2.3, 0);
                markers.get(i).teleport(Fx.loc(a.world, at));
                markers.get(i).text(Component.text(e.state.isDownedLike() ? "▽" : "▼").font(Glyphs.HUD).color(net.kyori.adventure.text.format.TextColor.color(e.state.isDownedLike() ? Glyphs.YELLOW : Glyphs.RED)));
            }
        }
    }

    public void clear() {
        georgeMarkers.clear();
    }
}
