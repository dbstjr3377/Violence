package dev.violence.npc;

import dev.violence.weapon.WeaponRegistry;
import dev.violence.weapon.WeaponType;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * NPC 시작 무기 (순수 계산이라 서버 없이 테스트 가능).
 * 기본: 5명 중 3명은 무기를 들고(armed 0.6), 무기를 든 NPC 중 5분의 2는 총기, 5분의 3은 근접 무기(gunShare 0.4).
 * 게임 시작처럼 한 번에 여러 명을 만들면 비율을 정확히 맞추고(남는 자리는 반올림), 리스폰처럼 한 명씩이면 확률로 고름.
 */
public final class NpcLoadout {
    private NpcLoadout() {}

    public enum Kind { UNARMED, GUN, MELEE }

    /** count 명의 무기 종류 (비율대로, 순서는 섞음) */
    public static List<Kind> batch(int count, double armed, double gunShare, Random rnd) {
        int armedN = (int) Math.round(count * armed);
        int gunN = (int) Math.round(armedN * gunShare);
        List<Kind> out = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            out.add(i < gunN ? Kind.GUN : i < armedN ? Kind.MELEE : Kind.UNARMED);
        }
        Collections.shuffle(out, rnd);
        return out;
    }

    /** 한 명 (리스폰 등) */
    public static Kind roll(double armed, double gunShare, Random rnd) {
        if (rnd.nextDouble() >= armed) return Kind.UNARMED;
        return rnd.nextDouble() < gunShare ? Kind.GUN : Kind.MELEE;
    }

    /** 종류에 맞는 무기 (맵 배치 가중치대로), 맨손이면 null */
    public static WeaponType pick(Kind kind, WeaponRegistry reg, Random rnd) {
        return switch (kind) {
            case UNARMED -> null;
            case GUN -> reg.randomSpawnable(rnd, WeaponType::isGun);
            case MELEE -> reg.randomSpawnable(rnd, WeaponType::isMelee);
        };
    }
}
