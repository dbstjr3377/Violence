package dev.violence.fx;

import org.bukkit.entity.Entity;
import org.bukkit.entity.Pose;

/** 자세 변경 (엔티티 종류에 따라 허용되지 않는 자세는 대체). */
public final class Poses {
    private Poses() {}

    /** 엎드린(쓰러진) 자세 */
    public static void lying(Entity e) {
        try {
            e.setPose(Pose.SWIMMING, true);
        } catch (IllegalArgumentException ex) {
            try {
                e.setPose(Pose.SLEEPING, true);
            } catch (IllegalArgumentException ignored) {
                // 지원하지 않으면 그대로 둠
            }
        }
    }

    public static void standing(Entity e) {
        try {
            e.setPose(Pose.STANDING, false);
        } catch (IllegalArgumentException ignored) {
            // 무시
        }
    }
}
