package dev.violence.weapon;

import dev.violence.mask.Mask;
import io.papermc.paper.datacomponent.DataComponentTypes;
import io.papermc.paper.datacomponent.item.Equippable;
import io.papermc.paper.datacomponent.item.SwingAnimation;
import io.papermc.paper.datacomponent.item.TooltipDisplay;
import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextDecoration;
import org.bukkit.Material;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;

/** 무기/가면/장비 아이템 생성 (리소스팩 item_model 사용). */
public final class WeaponItems {
    private WeaponItems() {}

    /**
     * 1인칭 애니메이션용 쿨다운 그룹. 공격할 때 이 그룹에 짧은 쿨다운을 걸면
     * 리소스팩이 쿨다운 진행률에 따라 키프레임 모델(발사·반동 잡기 / 휘두르기 / 잽)을 보여준다.
     */
    public static final Key GUNFIRE = Key.key("violence", "gunfire");
    public static final Key MELEE = Key.key("violence", "melee");
    public static final Key FIST = Key.key("violence", "fist");

    public static Key animGroup(WeaponType t) {
        return switch (t.category()) {
            case GUN -> GUNFIRE;
            case MELEE -> MELEE;
            case FIST -> FIST;
            case THROWABLE -> null;
        };
    }

    public static ItemStack create(WeaponType type, int ammo) {
        ItemStack it = new ItemStack(Material.STICK);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key(type.model()));
        it.setData(DataComponentTypes.ITEM_NAME, Component.text(type.displayName()));
        it.setData(DataComponentTypes.MAX_STACK_SIZE, 1);
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        // 바닐라 휘두르기 동작은 끄고 리소스팩 키프레임 애니메이션만 사용
        it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.NONE).duration(1).build());
        it.setData(DataComponentTypes.INTERACT_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.NONE).duration(1).build());
        Key group = animGroup(type);
        if (group != null) {
            it.setData(DataComponentTypes.USE_COOLDOWN, io.papermc.paper.datacomponent.item.UseCooldown.useCooldown(0.05f).cooldownGroup(group).build());
        }
        return it;
    }

    /** 한 손으로 드는 총 (나머지 총은 양손 조준 자세) */
    public static boolean oneHanded(WeaponType t) {
        return t.id().equals("magnum") || t.id().equals("silenced_pistol");
    }

    /**
     * 다른 플레이어와 NPC 에게 보이는 손 아이템 (3인칭 상체 애니메이션용).
     * - 양손 총: 장전된 석궁 → 바닐라의 양팔 조준 자세 (다리는 이동하며 따로 움직임)
     * - 권총: 한 손으로 들기
     * - 근접: 공격 시 휘두르기 동작이 보이도록 (부러진 큐대만 찌르기)
     * - 맨손: 손에 보이는 것 없이 주먹 휘두르기
     */
    public static ItemStack world(WeaponType type) {
        if (type.isGun() && !oneHanded(type)) {
            ItemStack it = new ItemStack(Material.CROSSBOW);
            it.setData(DataComponentTypes.ITEM_MODEL, Key.key(type.model() + "_world"));
            it.setData(DataComponentTypes.CHARGED_PROJECTILES,
                    io.papermc.paper.datacomponent.item.ChargedProjectiles.chargedProjectiles(java.util.List.of(new ItemStack(Material.ARROW))));
            it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
            it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.NONE).duration(1).build());
            return it;
        }
        ItemStack it = create(type, 0);
        if (type.isGun()) {
            // 권총: 한 팔 조준 자세용 (보는 사람에게 "사용 중" 상태를 함께 보냄, 소리/입자 없음)
            it.setData(DataComponentTypes.ITEM_MODEL, Key.key(type.model() + "_world"));
            it.setData(DataComponentTypes.CONSUMABLE, io.papermc.paper.datacomponent.item.Consumable.consumable()
                    .consumeSeconds(3600f)
                    .animation(io.papermc.paper.datacomponent.item.consumable.ItemUseAnimation.TOOT_HORN)
                    .sound(Key.key("minecraft:intentionally_empty"))
                    .hasConsumeParticles(false)
                    .build());
            return it;
        }
        if (type.isFist()) it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence:misc/blank"));
        if (type.isMelee() || type.isFist()) {
            SwingAnimation.Animation a = type.id().equals("pool_cue_short") ? SwingAnimation.Animation.STAB : SwingAnimation.Animation.WHACK;
            it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(a).duration(Math.max(5, Math.min(10, type.meleeCooldown()))).build());
        }
        return it;
    }

    /** 가면 아이템 (머리 칸 착용, 착용 시 머리 위 모델 표시) */
    public static ItemStack mask(Mask mask, boolean selectable) {
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key(mask.model()));
        it.setData(DataComponentTypes.ITEM_NAME, Component.text(mask.displayName() + " (" + mask.animal() + ")", NamedTextColor.YELLOW));
        it.setData(DataComponentTypes.MAX_STACK_SIZE, 1);
        if (selectable) {
            it.setData(DataComponentTypes.LORE, io.papermc.paper.datacomponent.item.ItemLore.lore()
                    .addLine(Component.text(mask.description(), NamedTextColor.WHITE).decoration(TextDecoration.ITALIC, false))
                    .addLine(Component.text("클릭해서 착용", NamedTextColor.GRAY).decoration(TextDecoration.ITALIC, false))
                    .build());
        } else {
            it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        }
        it.setData(DataComponentTypes.EQUIPPABLE, Equippable.equippable(EquipmentSlot.HEAD).swappable(false).dispensable(false).build());
        return it;
    }

    /**
     * 피 뒤집어쓰기 장비 (갑옷 칸, 리소스팩 장비 텍스처).
     * 3킬 이상일 때는 화면을 붉게 물들이는 카메라 오버레이도 포함.
     */
    public static ItemStack bloodArmor(EquipmentSlot slot, int level, int streakOverlay) {
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence:misc/blank"));
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        Equippable.Builder eq = Equippable.equippable(slot).swappable(false).dispensable(false)
                .assetId(Key.key("violence", "blood" + Math.max(1, Math.min(3, level))));
        if (streakOverlay > 0) eq.cameraOverlay(Key.key("violence", "misc/streak" + streakOverlay));
        it.setData(DataComponentTypes.EQUIPPABLE, eq.build());
        return it;
    }

    /** 카메라 오버레이만 있는 투명 장비 (피 없음 + 붉은 화면) */
    public static ItemStack overlayOnly(EquipmentSlot slot, int streakOverlay) {
        ItemStack it = new ItemStack(Material.PAPER);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence:misc/blank"));
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        it.setData(DataComponentTypes.EQUIPPABLE, Equippable.equippable(slot).swappable(false).dispensable(false)
                .cameraOverlay(Key.key("violence", "misc/streak" + streakOverlay)).build());
        return it;
    }

    /** NPC 옷 색 (가죽 갑옷) */
    public static ItemStack outfit(Material leather, int rgb) {
        ItemStack it = new ItemStack(leather);
        it.setData(DataComponentTypes.DYED_COLOR, io.papermc.paper.datacomponent.item.DyedItemColor.dyedItemColor(org.bukkit.Color.fromRGB(rgb)));
        return it;
    }
}
