package dev.violence.fx;

import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.TextColor;

/** 리소스팩 커스텀 폰트 키와 특수 글리프. */
public final class Glyphs {
    private Glyphs() {}

    public static final Key HUD = Key.key("violence", "hud");
    public static final Key HUD_BIG = Key.key("violence", "hud_big");
    public static final Key COMBO = Key.key("violence", "combo");
    public static final Key POPUP = Key.key("violence", "popup");
    public static final Key PROMPT = Key.key("violence", "prompt");
    public static final Key OVERLAY = Key.key("violence", "overlay");
    public static final Key SPACE = Key.key("violence", "space");

    /** 화면 전체를 덮는 검은 글리프 (페이드용) */
    public static final String BLACK_SCREEN = "";
    /** 총알 아이콘 */
    public static final String BULLET = "";
    /** 해골 아이콘 */
    public static final String SKULL = "";

    private static final char[] POS = {'', '', '', '', '', '', '', '', ''};
    private static final char[] NEG = {'', '', '', '', '', '', '', '', ''};

    /** px 만큼 가로로 띄우는 문자열 (음수면 왼쪽으로). violence:space 폰트로 출력해야 함. */
    public static String spaceString(int px) {
        char[] set = px >= 0 ? POS : NEG;
        int v = Math.abs(px);
        StringBuilder sb = new StringBuilder();
        for (int bit = 8; bit >= 0; bit--) {
            int amount = 1 << bit;
            while (v >= amount) {
                sb.append(set[bit]);
                v -= amount;
            }
        }
        return sb.toString();
    }

    public static Component space(int px) {
        return Component.text(spaceString(px)).font(SPACE);
    }

    public static Component text(String s, Key font, int rgb) {
        return Component.text(s).font(font).color(TextColor.color(rgb));
    }

    public static final int WHITE = 0xFFFFFF;
    public static final int YELLOW = 0xFFE14D;
    public static final int PINK = 0xFF3C8E;
    public static final int RED = 0xFF2E3B;
    public static final int CYAN = 0x4DF0FF;
    public static final int GRAY = 0xB8B8C8;
}
