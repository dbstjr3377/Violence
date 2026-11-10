package dev.violence.player;

import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.entity.Player;

/**
 * 플레이어 이동 속도. 클라이언트는 "이동 속도 속성 ÷ 걷기 속도(능력치)" 로 시야(FOV)를 넓히거나 좁히므로
 * 속성만 바꾸면 처형·컷씬(속도 0)이나 가면 속도 보정 때 화면이 확대·축소된다.
 * 걷기 속도 능력치를 같은 값으로 맞춰서 속도가 바뀌어도 시야는 그대로 둔다 (달리기 시야 변화만 남음).
 */
public final class PlayerSpeed {
    private PlayerSpeed() {}

    public static void set(Player p, double speed) {
        AttributeInstance inst = p.getAttribute(Attribute.MOVEMENT_SPEED);
        float walk = (float) Math.max(0, Math.min(1, speed * 2));   // Bukkit 걷기 속도 = 능력치 × 2
        if (inst != null && inst.getBaseValue() == speed && p.getWalkSpeed() == walk) return;
        p.setWalkSpeed(walk);                                        // 능력치와 속성 기본값을 함께 바꿈
        if (inst != null) inst.setBaseValue(speed);
    }
}
