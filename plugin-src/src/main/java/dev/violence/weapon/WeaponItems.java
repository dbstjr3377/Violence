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
    /** 연속 공격 때 번갈아 나오는 왼→오 휘두르기 ("<id>_b" 아이템 전용) */
    public static final Key MELEE_B = Key.key("violence", "melee_b");

    /** 좌우로 휘두르는 근접 무기 (부러진 큐대만 찌르기) */
    public static boolean swings(WeaponType t) {
        return t.isMelee() && !t.id().equals("pool_cue_short");
    }

    /**
     * 1인칭 손 아이템. backhand 이면 왼→오 휘두르기 프레임을 가진 "<id>_b" 모델과 별도 쿨다운 그룹을 쓴다.
     * (같은 무기라도 두 아이템을 번갈아 끼워 오→왼→오→왼 연속 동작을 만든다)
     */
    public static ItemStack create(WeaponType type, int ammo, boolean backhand) {
        ItemStack it = create(type, ammo);
        if (backhand && swings(type)) {
            it.setData(DataComponentTypes.ITEM_MODEL, Key.key(type.model() + "_b"));
            it.setData(DataComponentTypes.USE_COOLDOWN, io.papermc.paper.datacomponent.item.UseCooldown.useCooldown(0.05f).cooldownGroup(MELEE_B).build());
        }
        return it;
    }

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

    /** 아무것도 보이지 않는 손 아이템 (처형·컷씬 카메라 중 1인칭 손과 무기를 숨김: 빈손이면 팔이 그려지므로 투명 아이템을 쥐게 함) */
    public static ItemStack hiddenHand() {
        ItemStack it = new ItemStack(Material.STICK);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence:misc/blank"));
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.NONE).duration(1).build());
        it.setData(DataComponentTypes.INTERACT_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.NONE).duration(1).build());
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
     * - 근접: 두 손 대기 자세 (meleeStance). 부러진 큐대만 한 손 찌르기
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
        if (swings(type)) return meleeStance(type, false);   // 오른쪽 대기 (NPC 실제 장비)
        if (type.isFist()) it.setData(DataComponentTypes.ITEM_MODEL, Key.key("violence:misc/blank"));
        if (type.isMelee() || type.isFist()) {
            SwingAnimation.Animation a = type.id().equals("pool_cue_short") ? SwingAnimation.Animation.STAB : SwingAnimation.Animation.WHACK;
            it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(a).duration(Math.max(5, Math.min(10, type.meleeCooldown()))).build());
        }
        return it;
    }

    /**
     * 3인칭 휘두르기 길이 (틱). 리소스팩 "<id>_world_swing" 의 프레임 수와 같아야 한다 (tools/melee_tp.py SWING_TICKS).
     */
    public static final int TP_SWING_TICKS = 6;

    /** 휘두르는 근접 무기의 3인칭 대기 아이템 (left: 왼쪽 대기 = 다음 공격이 왼→오) */
    public static ItemStack worldStance(WeaponType type, boolean left) {
        return meleeItem(type, left ? "_world_l" : "_world");
    }

    /**
     * 휘두르는 근접 무기의 3인칭 휘두르기 아이템: 사용 시간(틱)에 따라 무기가 옆으로 크게 휘둘러지는 프레임.
     * backhand 이면 왼→오. 끝 자세는 반대쪽 대기와 같다.
     */
    public static ItemStack worldSwing(WeaponType type, boolean backhand) {
        return meleeItem(type, backhand ? "_world_swing_b" : "_world_swing");
    }

    /**
     * 휘두르는 근접 무기의 3인칭 아이템 (두 손 대기 자세).
     * "석궁 장전" 동작의 소모품으로 만들어, 보는 사람에게 "사용 중" 상태를 보내면 양손을 몸 앞에 모은 자세가 된다.
     * 보는 사람에게는 주 손을 왼손으로 보내므로 왼손이 손잡이 아래, 오른손(보조 팔)이 위를 잡는다 (tools/melee_tp.py).
     * 빠른 장전 IV 로 보조 팔이 0.25초 만에 자세를 잡는다 (반짝임은 끔). 공격하면 바닐라 휘두르기가 팔과 몸통을 비튼다.
     */
    private static ItemStack meleeStance(WeaponType type, boolean left) {
        return worldStance(type, left);
    }

    private static ItemStack meleeItem(WeaponType type, String suffix) {
        ItemStack it = new ItemStack(Material.STICK);
        it.setData(DataComponentTypes.ITEM_MODEL, Key.key(type.model() + suffix));
        it.setData(DataComponentTypes.MAX_STACK_SIZE, 1);
        it.setData(DataComponentTypes.TOOLTIP_DISPLAY, TooltipDisplay.tooltipDisplay().hideTooltip(true).build());
        it.setData(DataComponentTypes.CONSUMABLE, io.papermc.paper.datacomponent.item.Consumable.consumable()
                .consumeSeconds(3600f)
                .animation(io.papermc.paper.datacomponent.item.consumable.ItemUseAnimation.CROSSBOW)
                .sound(Key.key("minecraft:intentionally_empty"))
                .hasConsumeParticles(false)
                .build());
        try {
            it.setData(DataComponentTypes.ENCHANTMENTS, io.papermc.paper.datacomponent.item.ItemEnchantments.itemEnchantments()
                    .add(org.bukkit.enchantments.Enchantment.QUICK_CHARGE, 4).build());
            it.setData(DataComponentTypes.ENCHANTMENT_GLINT_OVERRIDE, false);
        } catch (RuntimeException ignored) {
            // 마법 부여 등록이 없으면 보조 팔이 천천히(1.25초) 자세를 잡을 뿐
        }
        it.setData(DataComponentTypes.ATTACK_ANIMATION, SwingAnimation.swingAnimation().type(SwingAnimation.Animation.WHACK).duration(TP_SWING_TICKS).build());
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
