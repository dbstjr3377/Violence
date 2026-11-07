package dev.violence.weapon;

import java.util.Map;

/** 바닥 무기 정보 카드에 쓰는 글자: 무기 종류 이름, 탄수 글자 폭. 순수 계산이라 서버 없이 테스트 가능. */
public final class WeaponLabels {
    private WeaponLabels() {}

    private static final Map<String, String> GUN_KIND = Map.of(
            "shotgun", "샷건", "double_barrel", "샷건",
            "m16", "소총",
            "uzi", "기관단총", "silenced_uzi", "기관단총", "mp5", "기관단총", "mp5_dual", "기관단총",
            "silenced_pistol", "권총", "magnum", "권총");

    private static final Map<String, String> MELEE_KIND = Map.of(
            "blunt", "둔기", "heavy", "무거운 무기", "light", "가벼운 무기", "blade", "날붙이");

    /** 무기 종류 이름. meleeGroup = 처형 묶음 (blunt / heavy / light / blade, 없으면 null) */
    public static String kind(WeaponType t, String meleeGroup) {
        return switch (t.category()) {
            case GUN -> GUN_KIND.getOrDefault(t.id(), t.pelletsMax() > 1 ? "샷건" : "총기");
            case MELEE -> meleeGroup != null ? MELEE_KIND.getOrDefault(meleeGroup, "근접 무기") : "근접 무기";
            case THROWABLE -> "투척 무기";
            case FIST -> "맨손";
        };
    }

    /** "현재 / 최대" (총만, 아니면 null) */
    public static String ammo(WeaponInstance w) {
        if (!w.type().isGun()) return null;
        return w.ammo() + " / " + w.type().ammo();
    }

    /**
     * 마인크래프트 기본 글꼴로 그린 글자 폭 (px, 글자 사이 1px 포함).
     * 숫자·'/' 는 6, 띄어쓰기 4 — 탄수 글자를 카드 오른쪽 끝에 맞출 때 씀.
     */
    public static int defaultFontWidth(String s) {
        int w = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            w += switch (c) {
                case ' ' -> 4;
                case 'i', '!', '.', ',', ':', ';', '|', '\'' -> 2;
                case 'l' -> 3;
                case 't', 'I', '[', ']' -> 4;
                case 'f', 'k', '<', '>', '(', ')', '{', '}', '*' -> 5;
                default -> 6;
            };
        }
        return w;
    }
}
