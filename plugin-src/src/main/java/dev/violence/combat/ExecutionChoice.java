package dev.violence.combat;

import dev.violence.fx.ExecutionAnims;
import dev.violence.mask.Mask;
import dev.violence.weapon.ExecutionStyle;
import dev.violence.weapon.WeaponType;

/**
 * 처형 방식 고르기 (순수 계산이라 서버 없이 테스트 가능).
 *  - 벽에 기대 기절한 적: 무기·가면과 상관없이 언제나 머리 발차기
 *  - 총: 형사 가면 + 탄이 있으면 총으로 처형, 아니면 버리고 맨손 / 투척 무기: 버리고 맨손
 *  - 그 밖에는 무기 묶음별 처형 동작 (맨손 머리 박기 / 밟기 / 둔기 / 무거운 무기 / 가벼운 무기 / 날붙이)
 *
 * @param weapon   처형에 쓰는 무기 (총·투척 무기를 버리면 맨손)
 * @param drop     들고 있던 무기를 바닥에 버림
 * @param anim     처형 동작 이름 (없으면 null: 발차기·총 처형)
 * @param autoHits 왼클릭 처형도 자동으로 연달아 침 (토니 맨주먹, 바이커 중식도)
 */
public record ExecutionChoice(ExecutionStyle style, WeaponType weapon, boolean drop, String anim, boolean autoHits) {

    public static ExecutionChoice choose(boolean wallStunned, WeaponType held, WeaponType fist, Mask mask, boolean hasAmmo,
                                         ExecutionAnims anims) {
        if (wallStunned) return new ExecutionChoice(ExecutionStyle.WALL_KICK, held, false, null, false);
        WeaponType t = held;
        boolean drop = false;
        ExecutionStyle style;
        if (t.isGun()) {
            if (mask == Mask.DETECTIVE && hasAmmo) return new ExecutionChoice(ExecutionStyle.GUN_SHOT, t, false, null, false);
            t = fist;
            drop = true;
            style = ExecutionStyle.HITS;
        } else if (t.isThrowable()) {
            t = fist;
            drop = true;
            style = ExecutionStyle.HITS;
        } else {
            style = t.execution();
        }
        String anim = null;
        boolean auto = false;
        ExecutionAnims.Anim a = anims == null ? null : anims.get(anims.animFor(t, mask));
        if (a != null) {
            anim = a.name();
            style = a.hits() ? ExecutionStyle.HITS : ExecutionStyle.AUTO;
            auto = a.hits() && ((t.isFist() && mask == Mask.TONY) || (mask == Mask.BIKER && t.id().equals("cleaver")));
        }
        return new ExecutionChoice(style, t, drop, anim, auto);
    }
}
