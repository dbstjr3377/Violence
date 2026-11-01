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

    public static ItemStack create(WeaponType type, int ammo) {
        ItemStack it = new ItemStack(Material.STICK);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key(type.model()));
        it.setData(DataComponentTypes.ITEM_NAME, Component.text(type.displayName()));
        it.setData(DataComponentTypes.MAX_STACK_SIZE, 1);
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        SwingAnimation.Animation anim = switch (type.category()) {
            case GUN, THROWABLE -> SwingAnimation.Animation.NONE;
            case FIST -> SwingAnimation.Animation.WHACK;
            case MELEE -> type.execution() == ExecutionStyle.AUTO && type.meleeCooldown() <= 6
                    ? SwingAnimation.Animation.STAB : SwingAnimation.Animation.WHACK;
        };
        it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(anim).duration(Math.max(4, Math.min(10, type.meleeCooldown()))).build());
        it.setData(DataComponentTypes.INTERACT_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.NONE).duration(1).build());
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
