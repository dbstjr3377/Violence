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

    /** 무기 종류 이름. 근접 무기는 세분하지 않고 모두 "근접 무기" (meleeGroup 은 예전 호출 호환용) */
    public static String kind(WeaponType t, String meleeGroup) {
        return switch (t.category()) {
            case GUN -> GUN_KIND.getOrDefault(t.id(), t.pelletsMax() > 1 ? "샷건" : "총기");
            case MELEE -> "근접 무기";
            case THROWABLE -> "투척 무기";
            case FIST -> "맨손";
        };
    }

    /** "현재 / 최대" (총만, 아니면 null) */
    public static String ammo(WeaponInstance w) {
        if (!w.type().isGun()) return null;
        return w.ammo() + " / " + w.type().ammo();
    }

    private static Map<Character, Double> cardWidths;

    /** 카드 글꼴(violence:card, Neo둥근모 8)로 그린 글자 폭 (px). 폭표는 tools/build_pack.py 가 만든 card_widths.json */
    public static int cardFontWidth(String s) {
        if (cardWidths == null) {
            Map<Character, Double> m = new java.util.HashMap<>();
            try (var in = WeaponLabels.class.getResourceAsStream("/card_widths.json")) {
                if (in != null) {
                    var o = com.google.gson.JsonParser.parseReader(new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
                    for (var e : o.entrySet()) m.put(e.getKey().charAt(0), e.getValue().getAsDouble());
                }
            } catch (java.io.IOException ignored) {
                // 폭표가 없으면 아래 기본값
            }
            cardWidths = m;
        }
        double w = 0;
        for (int i = 0; i < s.length(); i++) w += cardWidths.getOrDefault(s.charAt(i), 5.0);
        return (int) Math.round(w);
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
